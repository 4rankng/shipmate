import importlib.util
import io
import json
import tempfile
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parent / "jira_cli.py"
SPEC = importlib.util.spec_from_file_location("jira_cli_module", MODULE_PATH)
jira_cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(jira_cli)

class JiraCommentInventoryTests(TestCase):
    def read_comments(self, pages):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(jira_cli, "jira_get", side_effect=pages) as get:
            with redirect_stdout(output), redirect_stderr(errors):
                result = jira_cli.main(["comments", "RGPAYM-1234", "--all", "--json"])
        return result, output.getvalue(), errors.getvalue(), get

    def test_timestamp_churn_does_not_gate_complete_inventory(self):
        # A metadata handshake would read these changing timestamps and fail.
        with patch.object(jira_cli, "_get_specification_issue", side_effect=[
            {"fields": {"updated": str(n)}} for n in range(9)
        ]) as issue:
            result, output, _, get = self.read_comments([
                {"startAt": 0, "total": 2, "comments": [{"id": "1"}]},
                {"startAt": 1, "total": 2, "comments": [{"id": "2"}]},
            ])
        self.assertEqual(result, 0)
        self.assertEqual([c["id"] for c in json.loads(output)["comments"]], ["1", "2"])
        self.assertEqual(get.call_count, 2)
        issue.assert_not_called()
        self.assertIn("startAt=1", get.call_args_list[1].args[0])

    def test_empty_inventory_is_complete(self):
        result, output, _, get = self.read_comments([{"startAt": 0, "total": 0, "comments": []}])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output)["comments"], [])
        self.assertEqual(get.call_count, 1)

    def test_incomplete_or_inconsistent_pagination_fails_without_partial_json(self):
        first = {"startAt": 0, "total": 2, "comments": [{"id": "1"}]}
        for second in (
            {"startAt": 1, "total": 2, "comments": []},
            {"startAt": 1, "total": 2, "comments": [{"id": "1"}]},
            {"startAt": 1, "total": 3, "comments": [{"id": "2"}]},
            {"startAt": 0, "total": 2, "comments": [{"id": "2"}]},
            {"comments": [{"id": "2"}]},
        ):
            with self.subTest(second=second):
                result, output, errors, _ = self.read_comments([first, second])
                self.assertEqual(result, 1)
                self.assertEqual(output, "")
                self.assertIn("complete comment inventory", errors)


class JiraCliSetSummaryTests(TestCase):
    def run_cli(self, argv, stored):
        output, errors = io.StringIO(), io.StringIO()
        reads = [{"fields": {"summary": "FPX exactly-once to PC"}}, {"fields": {"summary": stored}}]
        with patch.object(jira_cli, "jira_get", side_effect=reads) as get, \
                patch.object(jira_cli, "jira_put", return_value={}) as put:
            with redirect_stdout(output), redirect_stderr(errors):
                code = jira_cli.main(argv)
        return code, output.getvalue(), errors.getvalue(), get, put

    def test_set_summary_writes_reads_back_and_reports_previous(self):
        title = "[fpx-adapter] Recover unpublished FPX payment results"
        code, out, _, get, put = self.run_cli(["set-summary", "RGPAYM-1234", "--summary", title], title)
        self.assertEqual(code, 0)
        put.assert_called_once_with(
            "/rest/api/3/issue/RGPAYM-1234", {"fields": {"summary": title}}, ticket_key="RGPAYM-1234"
        )
        self.assertEqual(get.call_count, 2)
        result = json.loads(out)
        self.assertEqual(result["previous_summary"], "FPX exactly-once to PC")
        self.assertTrue(result["verified"])

    def test_set_summary_fails_when_readback_differs(self):
        code, out, err, _, _ = self.run_cli(["set-summary", "RGPAYM-1234", "--summary", "New"], "Other")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("did not retain", err)

    def test_set_summary_rejects_invalid_values_without_calls(self):
        for value in ("   ", "a\nb", "x" * 256):
            with patch.object(jira_cli, "jira_get") as get, patch.object(jira_cli, "jira_put") as put:
                with redirect_stderr(io.StringIO()):
                    self.assertEqual(jira_cli.main(["set-summary", "RGPAYM-1234", "--summary", value]), 1)
            get.assert_not_called()
            put.assert_not_called()


class JiraCliSetDescriptionTests(TestCase):
    @patch.object(jira_cli, "jira_put")
    def test_set_description_reads_file_and_puts_fields(self, mock_put):
        mock_put.return_value = {}
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir) / "description.md"
            tmp.write_text("## Goal\n- **Problem:** example\n", encoding="utf-8")

            exit_code = jira_cli.main(["set-description", "RGPAYM-1234", "--file", str(tmp)])

        self.assertEqual(exit_code, 0)
        mock_put.assert_called_once_with(
            "/rest/api/3/issue/RGPAYM-1234",
            {
                "fields": {
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "heading",
                                "attrs": {"level": 2},
                                "content": [{"type": "text", "text": "Goal"}],
                            },
                            {
                                "type": "bulletList",
                                "content": [
                                    {
                                        "type": "listItem",
                                        "content": [
                                            {
                                                "type": "paragraph",
                                                "content": [
                                                    {
                                                        "type": "text",
                                                        "text": "Problem:",
                                                        "marks": [{"type": "strong"}],
                                                    },
                                                    {"type": "text", "text": " example"},
                                                ],
                                            }
                                        ],
                                    }
                                ],
                            },
                        ],
                    }
                }
            },
            ticket_key="RGPAYM-1234",
        )

    @patch.object(jira_cli, "jira_put")
    def test_set_description_with_text_and_region(self, mock_put):
        mock_put.return_value = {}

        exit_code = jira_cli.main(
            ["set-description", "RGPAYM-1234", "--text", "inline text", "--region", "my"]
        )

        self.assertEqual(exit_code, 0)
        mock_put.assert_called_once_with(
            "/rest/api/3/issue/RGPAYM-1234",
            {
                "fields": {
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "inline text"}],
                            }
                        ],
                    }
                }
            },
            ticket_key="RGPAYM-1234",
            region="my",
        )

    def test_set_description_requires_text_or_file(self):
        with self.assertRaises(SystemExit):
            jira_cli.main(["set-description", "RGPAYM-1234"])


class TextToAdfTests(TestCase):
    def test_empty_text_is_a_valid_empty_document(self):
        self.assertEqual(
            jira_cli.text_to_adf("   \n\n"),
            {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": []}]},
        )

    def test_headings_use_their_markdown_level(self):
        doc = jira_cli.text_to_adf("### Edge & Error Cases")
        self.assertEqual(
            doc["content"],
            [
                {
                    "type": "heading",
                    "attrs": {"level": 3},
                    "content": [{"type": "text", "text": "Edge & Error Cases"}],
                }
            ],
        )

    def test_consecutive_bullets_share_one_list(self):
        doc = jira_cli.text_to_adf("- first\n* second\n\nplain line")
        self.assertEqual(doc["content"][0]["type"], "bulletList")
        self.assertEqual(len(doc["content"][0]["content"]), 2)
        self.assertEqual(
            doc["content"][1],
            {"type": "paragraph", "content": [{"type": "text", "text": "plain line"}]},
        )

    def test_fenced_code_block_keeps_language_and_raw_lines(self):
        doc = jira_cli.text_to_adf("```bash\nmake test\nmake lint\n```")
        self.assertEqual(
            doc["content"],
            [
                {
                    "type": "codeBlock",
                    "attrs": {"language": "bash"},
                    "content": [{"type": "text", "text": "make test\nmake lint"}],
                }
            ],
        )

    def test_no_empty_text_nodes_are_emitted(self):
        doc = jira_cli.text_to_adf("## Heading\n\n-\n\ntext\n")
        for block in doc["content"]:
            for node in block.get("content", []):
                if node.get("type") == "text":
                    self.assertTrue(node["text"])

    def test_spec_tables_and_inline_marks_render_as_adf(self):
        doc = jira_cli.text_to_adf(
            "## Required Behaviour\n"
            "| Area | Requirement |\n"
            "|---|---|\n"
            "| Configuration | Provide **one** `feature.flag`. |\n\n"
            "## Acceptance Criteria\n"
            "| AC | Scenario | Given | When | Then |\n"
            "|---|---|---|---|---|\n"
            "| AC-01 | Disabled path | The flag is `true`. | The service starts. | No work begins. |"
        )

        tables = [block for block in doc["content"] if block["type"] == "table"]
        self.assertEqual(len(tables), 2)
        required_behaviour = tables[0]
        self.assertEqual(
            [cell["type"] for cell in required_behaviour["content"][0]["content"]],
            ["tableHeader", "tableHeader"],
        )
        requirement_nodes = required_behaviour["content"][1]["content"][1]["content"][0][
            "content"
        ]
        self.assertIn(
            {"type": "text", "text": "one", "marks": [{"type": "strong"}]},
            requirement_nodes,
        )
        self.assertIn(
            {"type": "text", "text": "feature.flag", "marks": [{"type": "code"}]},
            requirement_nodes,
        )
        self.assertEqual(len(tables[1]["content"][0]["content"]), 5)

    def test_jira_cli_exposes_comment_reads_but_no_comment_mutations(self):
        parser = jira_cli.build_parser()
        subcommands = parser._subparsers._group_actions[0].choices

        self.assertIn("comments", subcommands)
        self.assertNotIn("comment", subcommands)
        self.assertNotIn("delete-comment", subcommands)

    def test_spec_can_embed_original_content_without_changing_its_adf_blocks(self):
        original = (
            "Refreshing resets MY to SG. Keep **my choice**.\n\n"
            "- Keep the `region` field.\n\n"
            "| Input | Value |\n|---|---|\n| region | MY |\n\n"
            "```json\n{\"region\": \"MY\"}\n```\n"
        )
        draft = (
            "## Original Intent and Goal\n"
            "- **Desired outcome:** Retain selection for this tab session.\n\n"
            "### Original ticket content\n" + original + "\n"
            "## Required Behaviour\nRestore the permitted selection.\n\n"
            "## Acceptance Criteria\n"
            "| AC | Scenario | Given | When | Then |\n|---|---|---|---|---|\n"
            "| AC-01 | Refresh | MY selected | Refresh | MY remains |\n\n"
            "## Out of Scope\n- Cross-tab persistence.\n"
        )
        blocks = jira_cli.text_to_adf(draft)["content"]
        headings = [
            (i, block["content"][0]["text"])
            for i, block in enumerate(blocks) if block["type"] == "heading"
        ]
        positions = dict((title, i) for i, title in headings)
        self.assertEqual(
            blocks[positions["Original ticket content"] + 1:positions["Required Behaviour"]],
            jira_cli.text_to_adf(original)["content"],
        )
        self.assertEqual(sum(title == "Original ticket content" for _, title in headings), 1)
