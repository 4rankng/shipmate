import importlib.util
import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parent / "doctor.py"
SPEC = importlib.util.spec_from_file_location("doctor_module", MODULE_PATH)
doctor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doctor)


class DoctorTests(TestCase):
    def test_check_groups_are_core_and_delivery(self):
        self.assertEqual(sorted(doctor.CHECKS), ["core", "delivery"])

    def test_core_group_passes_when_tools_present(self):
        with patch.object(doctor.shutil, "which", return_value="/usr/bin/git"):
            self.assertEqual(doctor.run(["core"]), 0)

    def test_delivery_accepts_authenticated_gh(self):
        with patch.object(doctor, "_gh_auth_ok", return_value=True), \
                patch.object(doctor.shutil, "which", return_value="/usr/bin/gh"), \
                patch.dict(doctor.os.environ, {"GH_TOKEN": "test-token"}):
            self.assertEqual(doctor.run(["delivery"]), 0)

    def test_all_groups_run_together(self):
        with patch.object(doctor, "_gh_auth_ok", return_value=True), \
                patch.object(doctor.shutil, "which", return_value="/usr/bin/gh"), \
                patch.dict(doctor.os.environ, {"GH_TOKEN": "test-token"}):
            self.assertEqual(doctor.run(["core", "delivery"]), 0)
