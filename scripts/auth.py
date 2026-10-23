#!/usr/bin/env python3
"""Region-aware credential loading from the process environment.

Loads {REGION}_{SERVICE}_{KEY} with fallback to unprefixed {SERVICE}_{KEY}.
os.environ is authoritative, so the module stays shell- and OS-agnostic and CI
variables always win. Shell rc files are a last-resort fallback for two cases a
long-lived agent process hits often:

  * the variable was never exported into this process (non-interactive shell
    never sourced the rc file), and
  * the variable is exported but *stale* — the user rotated the token in their
    rc file after the process started, so every call fails with 401. Callers
    handle that by catching the 401 and calling `refresh_credentials()`, which
    re-reads the rc files and lets the value there override the stale env.

Usage:
    from auth import get_jira_creds, get_datadog_creds, get_doorman_creds
"""

import os
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

# Not zsh-specific: a teammate on bash must work too. Same list and rationale as
# gitlab_client._SHELL_RC_FILES — the files are parsed, never sourced, because
# sourcing ~/.zshrc under bash emits `compdef` noise and can fail the command.
_SHELL_RC_FILES = (".zshrc", ".bashrc", ".bash_profile", ".profile")

_EXPORT_RE = re.compile(r"^\s*export\s+([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
_VAR_REF_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")

# Values parsed out of the rc files. Populated lazily; `refresh_credentials()`
# clears it so a rotated token is picked up without restarting the process.
_rc_cache: Optional[Dict[str, str]] = None

# Names whose rc value should override a stale process env value. Set by
# `refresh_credentials()` only, so normal lookups keep env-first precedence.
_rc_overrides_env = False


def _rc_files() -> Tuple[Path, ...]:
    home = Path(os.environ.get("HOME", str(Path.home())))
    override = os.environ.get("PAYMENT_ENV_FILE")
    if override:
        return (Path(override),)
    return tuple(home / name for name in _SHELL_RC_FILES)


def _expand(value: str, parsed: Dict[str, str]) -> str:
    """Resolve `$VAR` / `${VAR}` against values seen so far, then the env."""

    def replace(match: re.Match) -> str:
        name = match.group(1) or match.group(2)
        return parsed.get(name) or os.environ.get(name, "")

    return _VAR_REF_RE.sub(replace, value)


def _parse_rc_file(path: Path) -> Dict[str, str]:
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return {}
    parsed: Dict[str, str] = {}
    for line in lines:
        match = _EXPORT_RE.match(line)
        if not match:
            continue
        name, raw = match.group(1), match.group(2).strip()
        if raw[:1] in ("'", '"') and raw[:1] == raw[-1:] and len(raw) > 1:
            quote, raw = raw[0], raw[1:-1]
            # Single quotes are literal in the shell; double quotes interpolate.
            parsed[name] = raw if quote == "'" else _expand(raw, parsed)
            continue
        # Unquoted: the shell ends the value at the first space, so anything
        # after one (a trailing `# comment`) is not part of the value.
        raw = raw.split(" ")[0]
        parsed[name] = _expand(raw, parsed)
    return parsed


def _shell_rc_values() -> Dict[str, str]:
    """Parse exports out of the user's shell rc files. Earlier files win."""
    global _rc_cache
    if _rc_cache is None:
        merged: Dict[str, str] = {}
        for path in _rc_files():
            if not path.exists():
                continue
            for name, value in _parse_rc_file(path).items():
                merged.setdefault(name, value)
        _rc_cache = merged
    return _rc_cache


def refresh_credentials() -> None:
    """Re-read the shell rc files and prefer them over the process env.

    Call this after an authenticated request fails with 401: it is the only
    signal available that the value carried in os.environ is a rotated-away
    token. Subsequent lookups return the rc value, so a single retry succeeds
    without restarting the agent process.
    """
    global _rc_cache, _rc_overrides_env
    _rc_cache = None
    _rc_overrides_env = True
    _shell_rc_values()


def lookup(name: str) -> str:
    """Resolve one variable: process env first, shell rc files as a fallback."""
    if _rc_overrides_env:
        value = _shell_rc_values().get(name, "")
        if value:
            return value
    return os.environ.get(name, "") or _shell_rc_values().get(name, "")


def load_credentials(region: str, service_prefix: str, keys: list) -> Dict[str, str]:
    """Load region-prefixed credentials from environment.

    Args:
        region: "sg" or "my"
        service_prefix: e.g. "JIRA", "DD", "DOORMAN"
        keys: list of key suffixes, e.g. ["DOMAIN", "USERNAME", "API_KEY"]

    Returns dict of {key: value}. Missing keys get empty string.
    """
    prefix = region.upper()
    result = {}
    for key in keys:
        val = lookup(f"{prefix}_{service_prefix}_{key}")
        if not val:
            val = lookup(f"{service_prefix}_{key}")
        result[key] = val
    return result


def _detect_region(ticket_key: Optional[str]) -> str:
    """Detect region from Jira ticket prefix."""
    if ticket_key:
        if ticket_key.startswith("TS-") and not ticket_key.startswith("TSE-"):
            return "my"
        if ticket_key.startswith("CM-"):
            return "my"
    return "sg"


def get_jira_creds(
    region: Optional[str] = None,
    ticket_key: Optional[str] = None,
) -> Tuple[str, str, str]:
    """Returns (base_url, email, api_key). Auto-detects region from ticket prefix.

    Env vars: SG_JIRA_DOMAIN / MY_JIRA_DOMAIN, SG_JIRA_USERNAME / MY_JIRA_USERNAME,
              SG_JIRA_API_KEY / MY_JIRA_API_KEY
    Fallback: JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN
    """
    if not region:
        region = _detect_region(ticket_key)

    creds = load_credentials(region, "JIRA", ["DOMAIN", "USERNAME", "API_KEY"])

    base_url = creds["DOMAIN"]
    email = creds["USERNAME"]
    api_key = creds["API_KEY"]

    # Fallback to unprefixed legacy vars
    if not base_url:
        base_url = lookup("JIRA_BASE_URL")
    if not email:
        email = lookup("JIRA_EMAIL")
    if not api_key:
        api_key = lookup("JIRA_API_TOKEN")

    return base_url, email, api_key


def get_datadog_creds(region: str = "sg") -> Tuple[str, str, str]:
    """Returns (site, api_key, app_key).

    Env vars: SG_DD_API_KEY / MY_DD_API_KEY, SG_DD_APP_KEY / MY_DD_APP_KEY
    Fallback: DD_API_KEY, DD_APP_KEY
    """
    creds = load_credentials(region, "DD", ["API_KEY", "APP_KEY"])
    # Use `or` (not the get() default) so a DD_SITE that exists-but-empty
    # falls back to the EU site instead of building https://api./... which
    # fails DNS with "nodename nor servname provided". SG/MY keys are valid on EU.
    site = lookup("DD_SITE") or "datadoghq.eu"

    api_key = creds["API_KEY"]
    app_key = creds["APP_KEY"]

    return site, api_key, app_key


def get_doorman_creds(region: str = "sg") -> Tuple[str, str]:
    """Returns (username, password).

    Env vars: SG_DOORMAN_USERNAME / MY_DOORMAN_USERNAME / STG_DOORMAN_USERNAME,
              SG_DOORMAN_PASSWORD / MY_DOORMAN_PASSWORD / STG_DOORMAN_PASSWORD
    Fallback: SG_DOORMAN_* for STG (same LDAP)
    """
    creds = load_credentials(region, "DOORMAN", ["USERNAME", "PASSWORD"])
    # Staging reuses SG LDAP creds if STG-specific ones aren't set
    if region == "stg" and not creds["USERNAME"]:
        creds = load_credentials("sg", "DOORMAN", ["USERNAME", "PASSWORD"])
    return creds["USERNAME"], creds["PASSWORD"]
