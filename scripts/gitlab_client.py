#!/usr/bin/env python3
"""GitLab API client for Dakota CI/CD operations.

Wraps all GitLab API calls used by deploy-service, gitlab-mr, and
regression_test skills. Replaces raw curl commands with typed Python.

Handles two pipeline architectures:
  - Child pipeline services (payment repo 71764944)
  - Standalone services (transaction-limit 71765328, etc.)

Usage:
    from gitlab_client import GitLabClient, find_image_tag, trigger_regression_pipeline
"""

import json
import os
import subprocess
import sys
import base64
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _token_from_glab() -> str:
    """Get the token glab itself uses (authenticated, kept fresh by `glab auth`).

    Preferred source: a hand-exported PAT frequently goes stale and returns
    HTTP 401, while the glab CLI keeps a working token.
    """
    try:
        out = subprocess.run(
            ["glab", "config", "get", "token", "--host", "gitlab.com"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    return ""


# Shell rc files are only a last-resort fallback, so the plugin still works for
# someone whose token is exported in an rc file that a non-interactive agent
# shell never sources. Not zsh-specific: a teammate on bash must work too.
_SHELL_RC_FILES = (".zshrc", ".bashrc", ".bash_profile", ".profile")


def _token_from_shell_rc() -> str:
    """Parse GITLAB_PRIVATE_TOKEN out of the user's shell rc files.

    Reads the files rather than sourcing them: sourcing ~/.zshrc under bash
    runs interactive completion init and emits `compdef:153: _comps:
    assignment to invalid subscript range` noise (and can fail the command).
    """
    for name in _SHELL_RC_FILES:
        rc = Path.home() / name
        if not rc.exists():
            continue
        try:
            lines = rc.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if line.startswith("export GITLAB_PRIVATE_TOKEN="):
                val = line.split("=", 1)[1].strip()
                return val.strip('"').strip("'")
    return ""


def _get_token() -> str:
    # Prefer glab's authenticated token; hand-exported PATs often go stale (401).
    token = (
        _token_from_glab()
        or os.environ.get("GITLAB_PRIVATE_TOKEN", "")
        or _token_from_shell_rc()
    )
    if not token:
        print("ERROR: No GitLab token found. Run `glab auth login`, or export "
              "GITLAB_PRIVATE_TOKEN in your environment.", file=sys.stderr)
        sys.exit(1)
    return token


# ---------------------------------------------------------------------------
# Project registry — maps service names to GitLab project IDs
# ---------------------------------------------------------------------------
SERVICE_PROJECTS = {
    "payment-experience":  {"id": 71764944, "type": "child"},
    "pairing-service":     {"id": 71764944, "type": "child"},
    "payment-engine":      {"id": 71764944, "type": "child"},
    "gd-proxy":            {"id": 71764944, "type": "child"},
    "transaction-limit":      {"id": 71765328, "type": "standalone"},
    "transaction-history":    {"id": 71765460, "type": "standalone"},
}

PROJECT_DEPLOY = 71764609
PROJECT_TEST_AUTOMATION = 71764778


def get_service_project(service_name: str) -> dict:
    info = SERVICE_PROJECTS.get(service_name)
    if not info:
        known = ", ".join(sorted(SERVICE_PROJECTS))
        print(f"WARNING: Service '{service_name}' not in registry. "
              f"Known services: {known}.")
        print("Falling back to payment child-pipeline search; if this is a "
              "typo or a non-payment service, the search will not find a tag.")
        return {"id": 71764944, "type": "child"}
    return info


# ---------------------------------------------------------------------------
# Low-level API helpers
# ---------------------------------------------------------------------------
class GitLabClient:
    def __init__(self, token: str = None):
        self.token = token or _get_token()

    def _auth_headers(self) -> dict:
        # glpat-/PAT tokens use PRIVATE-TOKEN; glab's OAuth tokens use Bearer.
        if self.token.startswith(("glpat-", "gldt-", "glsoat-")):
            return {"PRIVATE-TOKEN": self.token}
        return {"Authorization": f"Bearer {self.token}"}

    def _request(self, path: str, method: str = "GET",
                 data: dict = None) -> dict:
        url = f"https://gitlab.com/api/v4{path}"
        headers = self._auth_headers()
        body = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode()
        req = urllib.request.Request(url, data=body, headers=headers,
                                     method=method)
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            if not raw:
                return {}
            return json.loads(raw)

    def get(self, path: str) -> dict:
        return self._request(path)

    def get_list(self, path: str) -> list:
        result = self._request(path)
        return result if isinstance(result, list) else [result]

    def post(self, path: str, data: dict = None) -> dict:
        return self._request(path, method="POST", data=data)

    def put(self, path: str, data: dict = None) -> dict:
        return self._request(path, method="PUT", data=data)

    def get_raw(self, path: str) -> str:
        url = f"https://gitlab.com/api/v4{path}"
        req = urllib.request.Request(url, headers=self._auth_headers())
        with urllib.request.urlopen(req) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def download_binary(self, path: str, dest: str) -> bool:
        url = f"https://gitlab.com/api/v4{path}"
        req = urllib.request.Request(url, headers=self._auth_headers())
        with urllib.request.urlopen(req) as resp:
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
        return os.path.exists(dest) and os.path.getsize(dest) > 0


# ---------------------------------------------------------------------------
# Pipeline operations
# ---------------------------------------------------------------------------
def list_pipelines(gl: GitLabClient, project_id: int, ref: str = None,
                   sha: str = None, per_page: int = 10,
                   order_by: str = "id", sort: str = "desc") -> list:
    params = {"per_page": per_page, "order_by": order_by, "sort": sort}
    if ref:
        params["ref"] = ref
    if sha:
        params["sha"] = sha
    qs = urllib.parse.urlencode(params)
    return gl.get_list(f"/projects/{project_id}/pipelines?{qs}")


def list_jobs(gl: GitLabClient, project_id: int, pipeline_id: int) -> list:
    return gl.get_list(
        f"/projects/{project_id}/pipelines/{pipeline_id}/jobs?per_page=50"
    )


def get_job_log(gl: GitLabClient, project_id: int, job_id: int) -> str:
    return gl.get_raw(f"/projects/{project_id}/jobs/{job_id}/trace")


def find_job_by_name(gl: GitLabClient, project_id: int, pipeline_id: int,
                     job_name: str) -> Optional[dict]:
    for j in list_jobs(gl, project_id, pipeline_id):
        if j["name"] == job_name:
            return j
    return None


def find_child_pipeline(gl: GitLabClient, project_id: int,
                        pipeline_id: int) -> Optional[int]:
    bridges = gl.get_list(
        f"/projects/{project_id}/pipelines/{pipeline_id}/bridges"
    )
    for b in bridges:
        dp = b.get("downstream_pipeline")
        if dp:
            return dp["id"]
    return None


# ---------------------------------------------------------------------------
# Image tag extraction
# ---------------------------------------------------------------------------
def extract_image_tag_from_log(log: str) -> Optional[str]:
    for line in log.splitlines():
        low = line.lower()
        if "pushing image" in low or "pushed" in low:
            for part in line.split():
                if "amazonaws.com" in part:
                    tag = part.split(":")[-1].strip()
                    if tag and "-" in tag:
                        return tag
    return None


def find_image_tag(service_name: str, merge_sha: str = None) -> Optional[str]:
    """Find the rc- image tag for a service from its latest master pipeline.

    Handles both child pipeline (payment repo) and standalone projects.
    """
    gl = GitLabClient()
    info = get_service_project(service_name)
    project_id = info["id"]
    pipeline_type = info["type"]

    pipelines = list_pipelines(gl, project_id, ref="master", per_page=10)
    if not pipelines:
        print(f"No master pipelines found for project {project_id}")
        return None

    for p in pipelines:
        if merge_sha and not p["sha"].startswith(merge_sha[:7]):
            continue

        pid = p["id"]
        if pipeline_type == "child":
            child_id = find_child_pipeline(gl, project_id, pid)
            if not child_id:
                continue
            job = find_job_by_name(gl, project_id, child_id, "docker-svc-push")
        else:
            job = find_job_by_name(gl, project_id, pid, "docker-svc-push")

        if not job:
            continue

        log = get_job_log(gl, project_id, job["id"])
        tag = extract_image_tag_from_log(log)
        if tag:
            print(f"Found image tag: {tag} (pipeline #{pid}, job #{job['id']})")
            return tag

    print(f"No docker-svc-push job with image tag found for {service_name}")
    return None


# ---------------------------------------------------------------------------
# MR operations
# ---------------------------------------------------------------------------
def list_merge_requests(gl: GitLabClient, project_id: int,
                        state: str = "merged", per_page: int = 10) -> list:
    qs = urllib.parse.urlencode({
        "state": state, "order_by": "updated_at",
        "sort": "desc", "per_page": per_page,
    })
    return gl.get_list(f"/projects/{project_id}/merge_requests?{qs}")


def get_merge_request(gl: GitLabClient, project_id: int,
                      mr_iid: int) -> dict:
    return gl.get(f"/projects/{project_id}/merge_requests/{mr_iid}")


def create_merge_request(gl: GitLabClient, project_id: int,
                         source_branch: str, title: str,
                         target_branch: str = "master",
                         description: str = "") -> dict:
    return gl.post(f"/projects/{project_id}/merge_requests", {
        "source_branch": source_branch,
        "target_branch": target_branch,
        "title": title,
        "description": description,
    })


def approve_merge_request(gl: GitLabClient, project_id: int,
                          mr_iid: int) -> dict:
    return gl.post(
        f"/projects/{project_id}/merge_requests/{mr_iid}/approve"
    )


def merge_merge_request(gl: GitLabClient, project_id: int, mr_iid: int,
                        sha: str = None) -> dict:
    data = {
        "should_remove_source_branch": True,
        "squash": True,
        "skip_merge_train": False,
    }
    if sha:
        data["sha"] = sha
    return gl.put(
        f"/projects/{project_id}/merge_requests/{mr_iid}/merge", data
    )


# ---------------------------------------------------------------------------
# Regression test pipeline
# ---------------------------------------------------------------------------
def trigger_regression_pipeline(gl: GitLabClient) -> Optional[str]:
    """Trigger regression test pipeline via GraphQL API.

    Returns the pipeline path (e.g. '/gx-regional/dakota/quality/dakota-test-automation/-/pipelines/12345').
    """
    query = """
    mutation internalPipelineCreate($input: PipelineCreateInput!) {
      pipelineCreate(input: $input) {
        clientMutationId
        errors
        pipeline { id path }
      }
    }
    """
    variables = {
        "input": {
            "projectPath": "gx-regional/dakota/quality/dakota-test-automation",
            "ref": "master",
            "variables": [
                {"key": "ENVIRONMENT", "value": "stage",
                 "variableType": "ENV_VAR"},
                {"key": "BANK_NAME", "value": "gxs",
                 "variableType": "ENV_VAR"},
                {"key": "APP_TYPE", "value": "SDK",
                 "variableType": "ENV_VAR"},
            ],
            "inputs": [],
        }
    }
    body = json.dumps({
        "operationName": "internalPipelineCreate",
        "variables": variables,
        "query": query,
    }).encode()

    headers = gl._auth_headers()
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        "https://gitlab.com/api/graphql",
        data=body,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())

    data = result.get("data", {}).get("pipelineCreate", {})
    pipeline = data.get("pipeline")
    if not pipeline:
        errors = data.get("errors") or result.get("errors", [])
        print(f"ERROR triggering pipeline: {errors}")
        return None

    path = pipeline.get("path", "")
    gid = pipeline.get("id", "")
    print(f"Pipeline triggered: https://gitlab.com{path}")
    print(f"Pipeline GID: {gid}")
    return path


def play_manual_job(gl: GitLabClient, project_id: int, job_id: int) -> dict:
    return gl.post(f"/projects/{project_id}/jobs/{job_id}/play")


def play_all_manual_jobs(gl: GitLabClient, project_id: int,
                         pipeline_id: int) -> list:
    jobs = list_jobs(gl, project_id, pipeline_id)
    played = []
    for j in jobs:
        if j["status"] == "manual":
            play_manual_job(gl, project_id, j["id"])
            played.append(j)
            print(f"  Played: {j['name']} (id={j['id']})")
    if not played:
        print("  No manual jobs found to play.")
    return played


# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------
def search_code(service_name: str, term: str, limit: int = 20) -> list:
    """Blob search within a service's repo."""
    info = get_service_project(service_name)
    gl = GitLabClient()
    hits = gl.get_list(
        f"/projects/{info['id']}/search"
        f"?scope=blobs&search={urllib.parse.quote(term)}&per_page={limit}"
    )
    return hits


def fetch_file(service_name: str, file_path: str, ref: str = None) -> str:
    """Return the raw contents of a file from a service's repo."""
    info = get_service_project(service_name)
    gl = GitLabClient()
    ref = ref or info.get("default_branch") or "master"
    try:
        raw = gl._request(
            f"/projects/{info['id']}/repository/files/"
            f"{urllib.parse.quote(file_path, safe='')}?ref={urllib.parse.quote(ref)}"
        )
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise SystemExit(
                f"Not found: {file_path} at ref {ref}. Paths are relative to the "
                f"repository root, so a service file is usually "
                f"'{service_name}/<path>'. Use `search` to locate it."
            )
        raise
    return base64.b64decode(raw.get("content", "")).decode("utf-8", "replace")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print(__doc__)
        print("Actions: find-tag, search, file, list-mrs, trigger-regression, play-jobs")
        sys.exit(0)

    action = sys.argv[1]

    if action == "find-tag":
        if len(sys.argv) < 3:
            print("Usage: gitlab_client.py find-tag <service-name> [merge-sha]")
            sys.exit(1)
        service = sys.argv[2]
        sha = sys.argv[3] if len(sys.argv) > 3 else None
        tag = find_image_tag(service, merge_sha=sha)
        if tag:
            print(tag)
        else:
            sys.exit(1)

    elif action == "search":
        if len(sys.argv) < 4:
            print("Usage: gitlab_client.py search <service-name> <term> [limit]")
            sys.exit(1)
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else 20
        for h in search_code(sys.argv[2], sys.argv[3], limit):
            print(f"{h.get('path')}:{h.get('startline')}")
            for line in (h.get("data") or "").splitlines():
                print(f"    {line}")

    elif action == "file":
        if len(sys.argv) < 4:
            print("Usage: gitlab_client.py file <service-name> <path> [ref]")
            sys.exit(1)
        ref = sys.argv[4] if len(sys.argv) > 4 else None
        print(fetch_file(sys.argv[2], sys.argv[3], ref))

    elif action == "list-mrs":
        if len(sys.argv) < 3:
            print("Usage: gitlab_client.py list-mrs <service-name> [count]")
            sys.exit(1)
        service = sys.argv[2]
        count = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        info = get_service_project(service)
        gl = GitLabClient()
        mrs = list_merge_requests(gl, info["id"], per_page=count)
        for mr in mrs:
            sha = mr.get("merge_commit_sha", mr.get("sha", ""))[:12]
            print(f"  !{mr['iid']}: {mr['title']}")
            print(f"    SHA: {sha}  Merged: {mr.get('merged_at', 'N/A')[:16]}")

    elif action == "trigger-regression":
        gl = GitLabClient()
        trigger_regression_pipeline(gl)

    elif action == "play-jobs":
        if len(sys.argv) < 3:
            print("Usage: gitlab_client.py play-jobs <pipeline-num> "
                  "[project-id]")
            sys.exit(1)
        pipeline_num = sys.argv[2]
        project_id = int(sys.argv[3]) if len(sys.argv) > 3 else PROJECT_TEST_AUTOMATION
        gl = GitLabClient()
        play_all_manual_jobs(gl, project_id, int(pipeline_num))

    else:
        print(f"Unknown action: {action}")
        print("Actions: find-tag, search, file, list-mrs, trigger-regression, play-jobs")
        sys.exit(1)


if __name__ == "__main__":
    main()
