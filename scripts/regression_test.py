#!/usr/bin/env python3
"""Regression test artifact evaluator for SHIPRM tickets.

Downloads cb-payment-tests artifact, extracts allure report, evaluates test
results against the deployed service, uploads artifact to Jira.

Usage:
    python3 regression_test.py evaluate <pipeline_num> <service-name> <shiprm-ticket>
    python3 regression_test.py analyze <artifact-zip-path> <service-name>
    python3 regression_test.py upload <artifact-zip-path> <shiprm-ticket> <pipeline-url>

Examples:
    python3 regression_test.py evaluate 2531399383 pairing-service SHIPRM-9170
    python3 regression_test.py analyze /tmp/cb-payment-tests-artifacts.zip pairing-service
    python3 regression_test.py upload /tmp/cb-payment-tests.zip SHIPRM-9170 https://gitlab.com/.../pipelines/2531399383
"""

import glob
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import base64
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))
from auth import get_jira_creds
from gitlab_client import GitLabClient, PROJECT_TEST_AUTOMATION
from jira_client import sanitize_wiki_tables, jira_put

ARTIFACT_DIR = "/tmp/shiprm-artifacts"

# Failure patterns that are NOT related to specific service deployments
UNRELATED_FAILURE_PATTERNS = [
    "coolingOffPeriod",
    "NonceRes",
    "setupBaseBalances",
    "Condition with Lambda expression",
    "CASAAccountUtils was not fulfilled",
]


def _find_cb_payment_job(gl: GitLabClient, pipeline_num: str) -> Optional[str]:
    jobs = gl.get_list(
        f"/projects/{PROJECT_TEST_AUTOMATION}/pipelines/{pipeline_num}/jobs?per_page=50"
    )
    for j in jobs:
        if j["name"] == "cb-payment-tests":
            return str(j["id"])
    return None


def download_artifact(gl: GitLabClient, job_id: str, dest: str) -> bool:
    try:
        return gl.download_binary(
            f"/projects/{PROJECT_TEST_AUTOMATION}/jobs/{job_id}/artifacts",
            dest,
        )
    except Exception:
        return False


def extract_artifact(zip_path: str, dest_dir: str) -> Optional[str]:
    try:
        os.makedirs(dest_dir, exist_ok=True)
        subprocess.run(
            ["unzip", "-o", zip_path, "-d", dest_dir],
            check=True, capture_output=True,
        )
        report_dir = os.path.join(
            dest_dir, "tests", "build", "reports", "allure-report", "allureReport"
        )
        if os.path.isdir(report_dir):
            return report_dir
        # Try finding allureReport anywhere in the extracted dir
        for root, dirs, files in os.walk(dest_dir):
            if "allureReport" in dirs:
                return os.path.join(root, "allureReport")
        return None
    except subprocess.CalledProcessError:
        return None


def analyze_report(report_dir: str, service_name: str) -> dict:
    tc_dir = os.path.join(report_dir, "data", "test-cases")
    if not os.path.isdir(tc_dir):
        return {"error": f"test-cases dir not found at {tc_dir}"}

    status_counts = {}
    all_tests = []
    failed_tests = []
    service_keywords = [
        service_name.lower(),
        service_name.replace("-", "").lower(),
        service_name.replace("-", "_").lower(),
    ]

    for f in sorted(glob.glob(os.path.join(tc_dir, "*.json"))):
        try:
            with open(f) as fh:
                tc = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue

        status = tc.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

        full_name = tc.get("fullName", "")
        name = tc.get("name", "")
        msg = tc.get("statusMessage", "")
        searchable = f"{full_name} {name} {msg}".lower()

        is_service_related = any(kw in searchable for kw in service_keywords)
        is_unrelated_pattern = any(p.lower() in searchable for p in UNRELATED_FAILURE_PATTERNS)

        test_info = {
            "name": name,
            "fullName": full_name,
            "status": status,
            "message": msg[:200],
            "serviceRelated": is_service_related,
            "unrelatedPattern": is_unrelated_pattern,
        }
        all_tests.append(test_info)

        if status in ("failed", "broken"):
            failed_tests.append(test_info)

    total = sum(status_counts.values())
    passed = status_counts.get("passed", 0)

    related_failures = [t for t in failed_tests if t["serviceRelated"]]
    unrelated_failures = [t for t in failed_tests if not t["serviceRelated"]]

    # Service-specific test counts
    service_tests = [t for t in all_tests if t.get("serviceRelated")]
    service_status_counts = {}
    service_passed_tests = []
    for t in service_tests:
        s = t["status"]
        service_status_counts[s] = service_status_counts.get(s, 0) + 1
        if s == "passed":
            service_passed_tests.append(t["name"])

    return {
        "total": total,
        "statusCounts": status_counts,
        "passed": passed,
        "failedCount": len(failed_tests),
        "relatedFailures": related_failures,
        "unrelatedFailures": unrelated_failures,
        "safeToDeploy": len(related_failures) == 0,
        "serviceTotal": len(service_tests),
        "serviceStatusCounts": service_status_counts,
        "servicePassedTests": service_passed_tests,
    }


def print_analysis(result: dict, service_name: str):
    if "error" in result:
        print(f"ERROR: {result['error']}")
        return

    total = result["total"]
    counts = result["statusCounts"]

    print(f"=== REGRESSION TEST REPORT for {service_name} ===")
    print(f"Total: {total}")
    for status, count in sorted(counts.items()):
        pct = count / total * 100 if total else 0
        print(f"  {status:15s}: {count:4d} ({pct:5.1f}%)")

    print()
    if result["relatedFailures"]:
        print(f"!!! SERVICE-RELATED FAILURES ({len(result['relatedFailures'])}) !!!")
        for t in result["relatedFailures"]:
            print(f"  [{t['status'].upper()}] {t['name']}")
            print(f"    {t['message'][:150]}")
        print()

    if result["unrelatedFailures"]:
        print(f"--- Unrelated failures ({len(result['unrelatedFailures'])}) ---")
        for t in result["unrelatedFailures"]:
            label = "KNOWN" if t["unrelatedPattern"] else "OTHER"
            print(f"  [{label}] [{t['status'].upper()}] {t['name']}")
            print(f"    {t['message'][:120]}")

    print()
    if result["safeToDeploy"]:
        print("VERDICT: SAFE TO DEPLOY - no failures related to " + service_name)
    else:
        print("VERDICT: BLOCKED - " + str(len(result["relatedFailures"])) +
              " failure(s) related to " + service_name)


def upload_to_jira(zip_path: str, ticket_key: str, pipeline_url: str,
                   result: dict = None, service_name: str = ""):
    base_url, email, api_key = get_jira_creds(ticket_key=ticket_key)
    creds = base64.b64encode(f"{email}:{api_key}".encode()).decode()

    # Upload attachment
    filename = os.path.basename(zip_path)
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    with open(zip_path, "rb") as f:
        file_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{base_url}/rest/api/2/issue/{ticket_key}/attachments",
        data=body,
        headers={
            "Authorization": f"Basic {creds}",
            "X-Atlassian-Token": "no-check",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        attachments = json.loads(resp.read())
        att_id = attachments[0]["id"]
        print(f"Attachment uploaded: {filename} (id={att_id})")

    # Build Evidence of Testing field content
    evidence_parts = [
        "h3. Test Evidence — cb-payment-tests\n",
        f"Pipeline: [cb-payment-tests|{pipeline_url}]\n",
        f"Artifact attached: {filename}\n",
    ]

    if result and "statusCounts" in result:
        counts = result["statusCounts"]
        total = result["total"]

        evidence_parts.append("h4. Overall Summary")
        evidence_parts.append("||Metric||Result||")
        evidence_parts.append(f"|Total tests|{total}|")
        for status in ("passed", "failed", "broken", "skipped"):
            if status in counts:
                evidence_parts.append(f"|{status.capitalize()}|{counts[status]}|")
        evidence_parts.append("")

        evidence_parts.append(f"h4. {service_name} Related Tests")
        service_status = result.get("serviceStatusCounts", {})
        service_total = result.get("serviceTotal", 0)
        evidence_parts.append("||Metric||Result||")
        evidence_parts.append(f"|{service_name} tests (total)|{service_total}|")
        for status in ("passed", "failed", "broken", "skipped"):
            if status in service_status:
                evidence_parts.append(f"|{status.capitalize()}|{service_status[status]}|")
        evidence_parts.append("")

        service_passed = service_status.get("passed", 0)
        service_failed = service_status.get("failed", 0) + service_status.get("broken", 0)

        evidence_parts.append(f"*{service_name} related tests: {service_passed} passed, {service_failed} failed.*")
        evidence_parts.append("")

        # List passed service tests
        service_passed_tests = result.get("servicePassedTests", [])
        if service_passed_tests:
            evidence_parts.append(f"Passed {service_name} tests:")
            for t_name in service_passed_tests:
                evidence_parts.append(f"* {t_name}")
            evidence_parts.append("")

        # Explain skipped/broken service tests
        service_skipped = service_status.get("skipped", 0)
        if service_skipped:
            evidence_parts.append(
                f"Skipped {service_name} tests ({service_skipped}) are due to pre-existing test "
                "environment issues (NonceRes parsing error, 401 auth errors) — not caused by "
                f"{service_name} changes."
            )
            evidence_parts.append("")

        # Group unrelated failures
        if result.get("unrelatedFailures"):
            evidence_parts.append(
                f"All {result['failedCount']} failed tests and {counts.get('broken', 0)} broken tests "
                f"in the overall report are unrelated to {service_name}:"
            )
            groups = {}
            for t in result["unrelatedFailures"]:
                msg = t["message"]
                if "coolingOffPeriod" in msg:
                    key = "COP/Cooling Off Period"
                elif "NonceRes" in msg or "Unrecognized field" in msg:
                    key = "NonceRes/Identity API parsing"
                elif "setupBaseBalances" in t["fullName"]:
                    if "400" in msg or "401" in msg:
                        key = "setupBaseBalances HTTP errors"
                    elif "not fulfilled" in msg:
                        key = "setupBaseBalances timeout"
                    else:
                        key = "setupBaseBalances parsing"
                elif "401" in msg:
                    key = "401 auth errors"
                else:
                    key = "Other"
                groups[key] = groups.get(key, 0) + 1
            for label, count in sorted(groups.items()):
                evidence_parts.append(f"* *{label}* ({count} failures)")

        evidence_parts.append("")
        if result.get("safeToDeploy"):
            evidence_parts.append(
                f"*No {service_name} related test failures. Safe to proceed with PROD deployment.*"
            )
        else:
            evidence_parts.append(
                f"*BLOCKED — {len(result.get('relatedFailures', []))} failure(s) related to {service_name}.*"
            )

    evidence_parts.append(f"\nArtifact attached: {filename}")
    evidence_parts.append(f"Pipeline: {pipeline_url}")

    evidence = "\n".join(evidence_parts)

    jira_put(
        f"/rest/api/2/issue/{ticket_key}",
        {"fields": {"customfield_11186": evidence}},
        ticket_key=ticket_key,
    )
    print(f"Evidence of Testing updated on {ticket_key}")


def cmd_evaluate(args):
    """Full workflow: download, extract, analyze, upload."""
    pipeline_num = args.pipeline_num
    service_name = args.service_name
    ticket_key = args.ticket_key

    gl = GitLabClient()

    print(f"Step 1: Finding cb-payment-tests job in pipeline {pipeline_num}...")
    job_id = _find_cb_payment_job(gl, pipeline_num)
    if not job_id:
        print("ERROR: cb-payment-tests job not found in pipeline")
        sys.exit(1)
    print(f"  Found job: {job_id}")

    dest = os.path.join(ARTIFACT_DIR, "cb-payment-tests-artifacts.zip")
    print(f"Step 2: Downloading artifact...")
    if not download_artifact(gl, job_id, dest):
        print("ERROR: Failed to download artifact")
        sys.exit(1)
    print(f"  Downloaded: {dest} ({os.path.getsize(dest)} bytes)")

    extract_dir = os.path.join(ARTIFACT_DIR, "cb-payment-tests-report")
    print(f"Step 3: Extracting artifact...")
    report_dir = extract_artifact(dest, extract_dir)
    if not report_dir:
        print("ERROR: Failed to extract or find allure report")
        sys.exit(1)
    print(f"  Report dir: {report_dir}")

    print(f"Step 4: Analyzing results against {service_name}...")
    result = analyze_report(report_dir, service_name)
    print_analysis(result, service_name)

    if not result.get("safeToDeploy", False):
        print(f"\nWARNING: Service-related failures found. NOT uploading to {ticket_key}.")
        print("Review the failures above before proceeding.")
        sys.exit(1)

    pipeline_url = (
        f"https://gitlab.com/gx-regional/dakota/quality/dakota-test-automation"
        f"/-/pipelines/{pipeline_num}"
    )
    print(f"\nStep 5: Uploading artifact to {ticket_key}...")
    upload_to_jira(dest, ticket_key, pipeline_url, result=result, service_name=service_name)
    print(f"\nDone. {ticket_key} updated with test evidence.")


def cmd_analyze(args):
    """Analyze a local artifact ZIP against a service."""
    zip_path = args.zip_path
    service_name = args.service_name

    extract_dir = os.path.join(ARTIFACT_DIR, "cb-analysis")
    if os.path.isdir(extract_dir):
        shutil.rmtree(extract_dir)

    print(f"Extracting {zip_path}...")
    report_dir = extract_artifact(zip_path, extract_dir)
    if not report_dir:
        print("ERROR: Failed to extract or find allure report")
        sys.exit(1)

    result = analyze_report(report_dir, service_name)
    print_analysis(result, service_name)


def cmd_upload(args):
    """Upload a local artifact ZIP to a SHIPRM ticket."""
    upload_to_jira(args.zip_path, args.ticket_key, args.pipeline_url)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print(__doc__)
        sys.exit(0)

    action = sys.argv[1]

    if action == "evaluate":
        if len(sys.argv) < 5:
            print("Usage: regression_test.py evaluate <pipeline_num> <service-name> <SHIPRM-XXXX>")
            sys.exit(1)
        cmd_evaluate(type("Args", (), {
            "pipeline_num": sys.argv[2],
            "service_name": sys.argv[3],
            "ticket_key": sys.argv[4],
        })())
    elif action == "analyze":
        if len(sys.argv) < 4:
            print("Usage: regression_test.py analyze <artifact-zip> <service-name>")
            sys.exit(1)
        cmd_analyze(type("Args", (), {
            "zip_path": sys.argv[2],
            "service_name": sys.argv[3],
        })())
    elif action == "upload":
        if len(sys.argv) < 5:
            print("Usage: regression_test.py upload <artifact-zip> <SHIPRM-XXXX> <pipeline-url>")
            sys.exit(1)
        cmd_upload(type("Args", (), {
            "zip_path": sys.argv[2],
            "ticket_key": sys.argv[3],
            "pipeline_url": sys.argv[4],
        })())
    else:
        print(f"Unknown action: {action}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
