import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from validate_spec import validate


DRAFT = """## Problem / Context
Refresh resets the selection.

## Objective
Engineers keep their selected environment after refresh.

## Acceptance Criteria
- AC-01: Given MY is permitted, When I refresh, Then MY remains selected.
"""


class SpecifyValidationTests(unittest.TestCase):
    def test_length_is_a_soft_target_counting_whitespace(self):
        exact = DRAFT + " " * (1200 - len(DRAFT))
        self.assertTrue(validate(exact)["within_target"])
        over = validate(exact + " ")
        self.assertTrue(over["valid"])
        self.assertFalse(over["within_target"])
        self.assertEqual(over["characters"], 1201)
        self.assertIn("strong reason", over["warnings"][0])

    def test_word_target_is_exclusive_and_only_warns(self):
        prefix, suffix = DRAFT.split("Refresh resets the selection.")
        remaining = 149 - len((prefix + suffix).split())
        exact = prefix + " ".join(["filler"] * remaining) + suffix
        self.assertEqual(validate(exact)["words"], 149)
        self.assertTrue(validate(exact)["within_target"])
        over = validate(exact.replace("filler", "filler filler", 1))
        self.assertTrue(over["valid"])
        self.assertFalse(over["within_target"])

    def test_unicode_and_urls_are_counted(self):
        text = DRAFT.replace("Refresh resets", "环境🙂 Refresh resets") + "\n## Technical Notes\n- See https://example.test/design\n"
        result = validate(text)
        self.assertTrue(result["valid"])
        self.assertEqual(result["characters"], len(text))
        self.assertGreater(len(text.encode("utf-8")), result["characters"])

    def test_optional_sections_are_nonempty_bounded_bullets(self):
        self.assertTrue(validate(DRAFT)["valid"])
        for name, limit in (("Out of Scope", 3), ("Technical Notes", 3)):
            for count in range(1, limit + 1):
                self.assertTrue(validate(DRAFT + f"\n## {name}\n" + "- Keep permissions.\n" * count)["valid"])
            self.assertFalse(validate(DRAFT + f"\n## {name}\n")["valid"])
            self.assertFalse(validate(DRAFT + f"\n## {name}\n" + "- Note.\n" * (limit + 1))["valid"])

    def test_definitions_are_optional_term_bullets_before_objective(self):
        def with_definitions(lines):
            return DRAFT.replace("## Objective", "## Definitions\n" + lines + "\n## Objective")
        self.assertTrue(validate(with_definitions("- **MY**: Malaysia environment.\n"))["valid"])
        self.assertTrue(validate(with_definitions("- **T**: term.\n" * 6))["valid"])
        self.assertFalse(validate(with_definitions("- **T**: term.\n" * 7))["valid"])
        self.assertFalse(validate(with_definitions("- MY means Malaysia.\n"))["valid"])
        misplaced = DRAFT + "\n## Definitions\n- **MY**: Malaysia.\n"
        self.assertFalse(validate(misplaced)["valid"])

    def test_section_order_and_required_sections(self):
        self.assertFalse(validate(DRAFT.replace("## Objective\nEngineers keep their selected environment after refresh.\n\n", ""))["valid"])
        swapped = DRAFT + "\n## Technical Notes\n- A.\n\n## Out of Scope\n- B.\n"
        self.assertFalse(validate(swapped)["valid"])
        self.assertTrue(validate(DRAFT + "\n## Out of Scope\n- B.\n\n## Technical Notes\n- A.\n")["valid"])

    def test_legacy_user_story_is_rejected_for_new_drafts(self):
        legacy = "## User Story\nAs an engineer, I want X, so that Y.\n\n" + DRAFT
        result = validate(legacy)
        self.assertFalse(result["valid"])
        self.assertIn("replaced by Objective", " ".join(result["errors"]))

    def test_titled_criteria_are_accepted(self):
        titled = DRAFT.replace("- AC-01:", "- AC-01 (Refresh):")
        self.assertTrue(validate(titled)["valid"])
        self.assertFalse(validate(DRAFT.replace("- AC-01:", "- AC-01 Refresh:"))["valid"])

    def test_incomplete_or_duplicate_criteria_fail(self):
        self.assertFalse(validate(DRAFT.replace(", Then MY remains selected.", "."))["valid"])
        self.assertFalse(validate(DRAFT + "- AC-01: Given access is revoked, When I load, Then default is used.\n")["valid"])
        self.assertFalse(validate(DRAFT.split("- AC-01")[0])["valid"])

    def test_worked_examples_validate(self):
        path = Path(__file__).resolve().parents[1] / "skills/specify/references/concise-spec.md"
        drafts = re.findall(r"```md\n(.*?)```", path.read_text(), re.DOTALL)
        self.assertEqual(len(drafts), 2)
        compact, recovery = (validate(d) for d in drafts)
        self.assertTrue(compact["valid"] and compact["within_target"], compact)
        self.assertTrue(recovery["valid"], recovery)
        self.assertEqual(compact["smells"], [])
        self.assertEqual(recovery["smells"], [])
        self.assertFalse(recovery["within_target"])
        self.assertIn("no longer permitted", drafts[0])
        self.assertIn("new tab", drafts[0])
        self.assertIn("do not change permissions", drafts[0])

    def test_unfilled_template_and_open_markers_fail(self):
        skill = Path(__file__).resolve().parents[1] / "skills/specify/SKILL.md"
        template = re.search(r"```md\n(.*?)```", skill.read_text(), re.DOTALL).group(1)
        result = validate(template)
        self.assertFalse(result["valid"])
        self.assertIn("placeholders", " ".join(result["errors"]))
        self.assertFalse(validate(DRAFT.replace("MY remains selected.", "TBD."))["valid"])
        self.assertTrue(validate(DRAFT + "\n## Technical Notes\n- See <https://example.test/design>\n")["valid"])

    def test_smells_are_advisory(self):
        vague = validate(DRAFT.replace("MY remains selected.", "MY is restored correctly."))
        self.assertTrue(vague["valid"] and vague["within_target"], vague)
        self.assertTrue(any(s.startswith("AC-01") and "'correctly'" in s for s in vague["smells"]))
        overlap = validate(DRAFT + "- AC-02: Given MY is permitted, When I refresh, Then the default is shown.\n")
        self.assertTrue(overlap["valid"])
        self.assertTrue(any("AC-01 and AC-02" in s for s in overlap["smells"]))
        guarantee = validate(DRAFT.replace("MY remains selected.", "MY is published Exactly-once."))
        self.assertTrue(guarantee["valid"])
        self.assertTrue(any("guarantee" in s for s in guarantee["smells"]))
        self.assertEqual(validate(DRAFT)["smells"], [])

    def test_literal_marker_words_in_requirements_are_valid(self):
        for status in ("TODO", "TBD", "`TODO`", '"TODO"'):
            for criterion in (
                f"Given a task in {status} status, When its owner completes it, "
                "Then its status becomes DONE.",
                f"Given an open task, When its owner resets it, Then its status becomes {status}.",
                f"Given {status} is a task status, When the owner lists tasks, Then tasks are shown.",
            ):
                with self.subTest(criterion=criterion):
                    draft = DRAFT.replace(
                        "Given MY is permitted, When I refresh, Then MY remains selected.", criterion)
                    result = validate(draft)
                    self.assertTrue(result["valid"], result)

    def test_explicit_open_markers_still_fail(self):
        for marker in ("TODO.", "TBD.", "TODO: decide the result.", "[TODO]",
                       "[TBD: agree the outcome]", "NEEDS CLARIFICATION"):
            with self.subTest(marker=marker):
                result = validate(DRAFT.replace("MY remains selected.", marker))
                self.assertFalse(result["valid"], result)
                self.assertIn("placeholders", " ".join(result["errors"]))
        for marker in ("TODO", "TBD", "- TODO: decide the retry policy."):
            with self.subTest(marker=marker):
                result = validate(DRAFT.replace("Refresh resets the selection.", marker))
                self.assertFalse(result["valid"], result)
                self.assertIn("placeholders", " ".join(result["errors"]))

    def test_cli_is_read_only_and_never_prints_content(self):
        script = Path(__file__).with_name("validate_spec.py")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "draft.md"
            literal = DRAFT.replace("Given MY is permitted, When I refresh, Then MY remains selected.",
                                    "Given a task in TODO status, When its owner completes it, "
                                    "Then its status becomes DONE.")
            cases = ((DRAFT, 0), (literal, 0), (DRAFT + " " * 1200, 0),
                     (DRAFT.replace("MY remains selected.", "TODO."), 1),
                     (DRAFT.replace("## Objective", "## Goal"), 1))
            for text, code in cases:
                content = text.replace("\n", "\r\n").encode()
                path.write_bytes(content)
                result = subprocess.run([sys.executable, str(script), str(path)], capture_output=True, text=True)
                self.assertEqual(result.returncode, code)
                self.assertEqual(path.read_bytes(), content)
                self.assertEqual(json.loads(result.stdout)["characters"], len(content.decode()))
                self.assertNotIn("MY remains selected", result.stdout)
            path.write_bytes(b"\xff")
            result = subprocess.run([sys.executable, str(script), str(path)], capture_output=True)
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
