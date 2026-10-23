import importlib.util
import os
import tempfile
import urllib.error
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent

# The developer running these tests has real tokens exported. Clear the names
# under test so a passing/failing assertion can never echo a live credential.
_AMBIENT = (
    "SG_JIRA_DOMAIN", "SG_JIRA_USERNAME", "SG_JIRA_API_KEY",
    "MY_JIRA_DOMAIN", "MY_JIRA_USERNAME", "MY_JIRA_API_KEY",
    "JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_API_KEY",
)


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


auth = _load("auth_module", "auth.py")


def _reset():
    auth._rc_cache = None
    auth._rc_overrides_env = False


class ShellRcParsingTests(TestCase):
    def setUp(self):
        _reset()
        self.addCleanup(_reset)
        cleared = patch.dict("os.environ", {}, clear=False)
        cleared.start()
        self.addCleanup(cleared.stop)
        for name in _AMBIENT:
            os.environ.pop(name, None)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.rc = Path(self.tmp.name) / "rc"

    def _with_rc(self, text: str):
        self.rc.write_text(text, encoding="utf-8")
        return patch.dict("os.environ", {"PAYMENT_ENV_FILE": str(self.rc)}, clear=False)

    def test_parses_plain_quoted_and_interpolated_exports(self):
        with self._with_rc(
            'export SG_JIRA_DOMAIN=https://gxsbank.atlassian.net\n'
            'export SG_JIRA_USERNAME="user@example.com"\n'
            "export SG_JIRA_API_KEY='fake-single-quoted'\n"
            'export JIRA_BASE_URL="$SG_JIRA_DOMAIN"\n'
            'export JIRA_EMAIL="${SG_JIRA_USERNAME}"\n'
        ):
            values = auth._shell_rc_values()

        self.assertEqual(values["SG_JIRA_DOMAIN"], "https://gxsbank.atlassian.net")
        self.assertEqual(values["SG_JIRA_USERNAME"], "user@example.com")
        self.assertEqual(values["SG_JIRA_API_KEY"], "fake-single-quoted")
        self.assertEqual(values["JIRA_BASE_URL"], "https://gxsbank.atlassian.net")
        self.assertEqual(values["JIRA_EMAIL"], "user@example.com")

    def test_unquoted_value_stops_at_trailing_comment(self):
        with self._with_rc("export SG_JIRA_API_KEY=ATATT-token # rotated 2026-08-19\n"):
            self.assertEqual(auth.lookup("SG_JIRA_API_KEY"), "ATATT-token")

    def test_env_wins_over_rc_file_by_default(self):
        with self._with_rc("export SG_JIRA_API_KEY=from-rc\n"):
            with patch.dict("os.environ", {"SG_JIRA_API_KEY": "from-env"}, clear=False):
                self.assertEqual(auth.lookup("SG_JIRA_API_KEY"), "from-env")

    def test_rc_fills_in_variable_missing_from_env(self):
        with self._with_rc("export SG_JIRA_API_KEY=from-rc\n"):
            self.assertEqual(auth.lookup("SG_JIRA_API_KEY"), "from-rc")

    def test_refresh_lets_rc_override_a_stale_env_value(self):
        with self._with_rc("export SG_JIRA_API_KEY=rotated-token\n"):
            with patch.dict("os.environ", {"SG_JIRA_API_KEY": "stale-token"}, clear=False):
                self.assertEqual(auth.lookup("SG_JIRA_API_KEY"), "stale-token")
                auth.refresh_credentials()
                self.assertEqual(auth.lookup("SG_JIRA_API_KEY"), "rotated-token")

    def test_get_jira_creds_uses_rc_after_refresh(self):
        with self._with_rc(
            "export SG_JIRA_DOMAIN=https://gxsbank.atlassian.net\n"
            "export SG_JIRA_USERNAME=user@example.com\n"
            "export SG_JIRA_API_KEY=rotated-token\n"
        ):
            with patch.dict("os.environ", {"SG_JIRA_API_KEY": "stale-token"}, clear=False):
                auth.refresh_credentials()
                base_url, email, api_key = auth.get_jira_creds(region="sg")

        self.assertEqual(base_url, "https://gxsbank.atlassian.net")
        self.assertEqual(email, "user@example.com")
        self.assertEqual(api_key, "rotated-token")


class JiraClientRetryTests(TestCase):
    def setUp(self):
        _reset()
        self.addCleanup(_reset)
        self.jira_client = _load("jira_client_module", "jira_client.py")

    def _http_error(self, code: int):
        return urllib.error.HTTPError("https://example/x", code, "err", {}, None)

    def test_401_refreshes_credentials_and_retries_once(self):
        creds = iter([
            ("https://site", "user", "stale-token"),
            ("https://site", "user", "rotated-token"),
        ])
        calls = []

        def fake_request(path, base_url, email, api_key, data=None, method="GET"):
            calls.append(api_key)
            if api_key == "stale-token":
                raise self._http_error(401)
            return {"ok": True}

        with patch.object(self.jira_client, "get_jira_creds", side_effect=lambda **kw: next(creds)), \
                patch.object(self.jira_client, "refresh_credentials") as refresh, \
                patch.object(self.jira_client, "_make_request", side_effect=fake_request):
            result = self.jira_client.jira_get("/rest/api/3/myself", region="sg")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(calls, ["stale-token", "rotated-token"])
        refresh.assert_called_once()

    def test_401_with_no_fresher_credential_raises_actionable_error(self):
        with patch.object(self.jira_client, "get_jira_creds",
                          return_value=("https://site", "user", "same-token")), \
                patch.object(self.jira_client, "refresh_credentials"), \
                patch.object(self.jira_client, "_make_request",
                             side_effect=self._http_error(401)):
            with self.assertRaises(self.jira_client.JiraAuthError) as ctx:
                self.jira_client.jira_get("/rest/api/3/myself", region="sg")

        self.assertIn("401", str(ctx.exception))
        self.assertNotIn("same-token", str(ctx.exception))

    def test_non_401_error_propagates_without_retry(self):
        with patch.object(self.jira_client, "get_jira_creds",
                          return_value=("https://site", "user", "token")), \
                patch.object(self.jira_client, "refresh_credentials") as refresh, \
                patch.object(self.jira_client, "_make_request",
                             side_effect=self._http_error(404)) as request:
            with self.assertRaises(urllib.error.HTTPError):
                self.jira_client.jira_get("/rest/api/3/issue/X-1", region="sg")

        refresh.assert_not_called()
        self.assertEqual(request.call_count, 1)
