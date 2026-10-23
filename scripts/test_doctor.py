import importlib.util
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parent / "doctor.py"
SPEC = importlib.util.spec_from_file_location("doctor_module", MODULE_PATH)
doctor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doctor)


class DoctorTests(TestCase):
    @patch.object(doctor, "_glab_auth_ok", return_value=True)
    @patch.object(doctor.shutil, "which", return_value="/usr/local/bin/glab")
    def test_gitlab_accepts_authenticated_glab_without_exported_pat(self, _which, _auth):
        with patch.object(doctor, "lookup", return_value=None):
            self.assertEqual(doctor.run(["gitlab"]), 0)

    @patch.object(doctor, "_live_jira_check", return_value=([], []))
    def test_live_check_uses_only_selected_region(self, live_check):
        with patch.object(doctor, "lookup", return_value="configured"):
            self.assertEqual(doctor.run(["jira"], live=True, region="sg"), 0)
        live_check.assert_called_once_with(("sg",))
