"""Schema checks for the machine-local run state file."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from run_state import validate


SCRIPT = Path(__file__).parent / "run_state.py"


def state(**overrides):
    entry = {
        "version": 1,
        "work_item": {"key": "local-0123456789ab", "source": "local"},
        "stage": 5,
        "updated_at": "2026-10-23T12:00:00Z",
    }
    entry.update(overrides)
    return entry


class ValidateRunStateTests(unittest.TestCase):
    def test_accepts_a_minimal_valid_state(self):
        result = validate(state())
        self.assertEqual(result["errors"], [])
        self.assertTrue(result["valid"])

    def test_accepts_decisions_candidate_review_and_pending(self):
        result = validate(state(
            stage=9,
            decisions=[{"text": "reuse the existing job store", "source": "AC-02"}],
            candidate={"branch": "local-abc-exports", "sha": "abc1234", "base": "main"},
            review={"roster": ["requirements-code-quality"], "verdict":
                    "NO_BLOCKING_FINDINGS_IN_REVIEWED_SCOPE"},
            pending={"question": "retention period for exported files?"},
        ))
        self.assertTrue(result["valid"])

    def test_rejects_unknown_version_and_stage_range(self):
        result = validate(state(version=2, stage=12))
        self.assertFalse(result["valid"])
        self.assertIn("version must be 1", result["errors"])
        self.assertIn("stage must be an integer 0-11", result["errors"])

    def test_rejects_missing_work_item_and_timestamp(self):
        result = validate({"version": 1, "stage": 3})
        self.assertFalse(result["valid"])
        self.assertIn("work_item.key must be a nonempty string", result["errors"])
        self.assertIn("work_item.source must be jira or local", result["errors"])
        self.assertIn("updated_at must be a nonempty ISO-8601 string", result["errors"])

    def test_rejects_malformed_decision_and_pending_entries(self):
        result = validate(state(
            decisions=[{"text": "  "}],
            pending={"question": ""},
        ))
        self.assertFalse(result["valid"])
        self.assertIn("decisions[0].text must be a nonempty string", result["errors"])
        self.assertIn("decisions[0].source must be a nonempty string", result["errors"])
        self.assertIn("pending.question must be a nonempty string", result["errors"])

    def test_rejects_non_list_decisions(self):
        result = validate(state(decisions="settled"))
        self.assertFalse(result["valid"])
        self.assertIn("decisions must be a list", result["errors"])

    def test_cli_exits_nonzero_on_an_invalid_state(self):
        run = subprocess.run([sys.executable, str(SCRIPT), "--check", "-"],
                             input=json.dumps(state(stage=99)),
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn("stage must be an integer 0-11", run.stdout)

    def test_cli_exits_zero_on_a_valid_state(self):
        run = subprocess.run([sys.executable, str(SCRIPT), "--check", "-"],
                             input=json.dumps(state()),
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0)
        self.assertIn('"valid": true', run.stdout)


if __name__ == "__main__":
    unittest.main()
