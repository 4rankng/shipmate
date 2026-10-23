import json
import unittest

from codex_usage import extract_codex_usage


def root(**overrides):
    row = {
        "type": "AGENT", "name": "Codex Turn", "sessionId": "session-one",
        "traceId": "trace-one", "id": "span-one", "parentObservationId": None,
        "startTime": "2026-10-06T01:02:03.123456789Z", "tags": ["skill:langfuse"],
    }
    row.update(overrides)
    return row


def tool(path, **overrides):
    row = root(
        type="TOOL", name="skill:langfuse", id="tool-one",
        parentObservationId="span-one", level="DEFAULT",
        metadata={"codex.tool_name": "exec_command"}, input={"cmd": "cat " + path},
    )
    row.update(overrides)
    return row


class CodexUsageTests(unittest.TestCase):
    def test_deduplicates_turns_by_session_and_keeps_earliest_precise_time(self):
        later = root(id="later", traceId="trace-two", startTime="2026-10-06T01:03:00Z")
        records = extract_codex_usage([later, root(), root()])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source_span_id"], "span-one")
        self.assertEqual(records[0]["observed_at_ns"] % 1_000_000_000, 123456789)
        self.assertEqual(records[0]["name"], "langfuse")

    def test_separate_sessions_remain_separate(self):
        records = extract_codex_usage([root(), root(sessionId="session-two")])
        self.assertEqual(len(records), 2)

    def test_children_and_generations_do_not_count_inherited_tags(self):
        child = root(id="child", parentObservationId="parent")
        subagent = root(name="Codex Subagent Turn", isRootObservation=True)
        generation = root(type="GENERATION", name="LLM")
        self.assertEqual(extract_codex_usage([child, subagent, generation]), [])

    def test_requires_root_evidence_and_respects_explicit_false(self):
        missing = root()
        del missing["parentObservationId"]
        self.assertEqual(extract_codex_usage([missing, root(isRootObservation=False)]), [])
        semantic_root = root(parentObservationId="external", isRootObservation=True)
        self.assertEqual(len(extract_codex_usage([semantic_root])), 1)

    def test_installed_inventory_and_model_text_are_not_usage(self):
        path = "/home/u/.codex/plugins/cache/market/unused/1.0/skills/x/SKILL.md"
        inventory = {"installedPlugins": ["unused"], "skills": ["langfuse"]}
        model = root(type="GENERATION", name="LLM", input=path, output=path)
        ordinary_tool = tool(path, name="exec_command")
        self.assertEqual(extract_codex_usage([inventory, model, ordinary_tool]), [])

    def test_codex_and_copilot_cache_owners_with_wrapped_and_json_arguments(self):
        paths = [
            "/Users/example/.codex/plugins/cache/gx-copilot-plugin/justinian/2.1.0/skills/l3-goal/SKILL.md",
            "~/.copilot/plugins/cache/team/telemetry/1.0.0/skills/trace/scripts/run.py",
        ]
        first = tool(paths[0], input={"args": {"cmd": "cat '" + paths[0] + "'"}})
        second = tool(paths[1], id="tool-two", input=json.dumps({"command": "python3 " + paths[1]}))
        records = extract_codex_usage([first, second])
        self.assertEqual({row["name"] for row in records}, {
            "justinian@gx-copilot-plugin", "telemetry@team",
        })
        self.assertTrue(all(row["kind"] == "plugin" for row in records))

    def test_unknown_owners_and_non_skill_cache_files_are_ignored(self):
        paths = [
            "/home/u/.agents/skills/langfuse/SKILL.md",
            "/home/u/.codex/plugins/cache/market/plugin/1.0/README.md",
            "/home/u/.codex/plugins/cache/market/plugin/1.0/skills/x/SKILL.md.bak",
        ]
        self.assertEqual(extract_codex_usage([tool(path) for path in paths]), [])

    def test_mcp_server_is_not_assumed_to_be_plugin_owner(self):
        row = tool("/home/u/.codex/plugins/cache/m/p/1/skills/x/SKILL.md",
                   name="some-server.some-tool", metadata={"codex.tool_name": "mcp_tool"})
        self.assertEqual(extract_codex_usage([row]), [])

    def test_error_tools_are_excluded_and_warning_access_is_identified(self):
        path = "/home/u/.codex/plugins/cache/m/p/1/skills/x/SKILL.md"
        records = extract_codex_usage([
            tool(path, level="ERROR"), tool(path, level="DEBUG"),
            tool(path, level="FATAL"), tool(path, level="WARNING"),
        ])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["evidence"], "codex_detected_skill_based_plugin_access")

    def test_plugin_access_deduplicates_across_skills_and_explicit_tag(self):
        path = "/home/u/.codex/plugins/cache/m/p/1/skills/x/SKILL.md"
        first = tool(path)
        later = tool(path.replace("/x/", "/y/"), id="tool-two", startTime="2026-10-06T02:00:00Z")
        tagged = root(tags=["plugin:p@m"], startTime="2026-10-06T03:00:00Z")
        records = extract_codex_usage([later, tagged, first])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source_span_id"], "tool-one")

    def test_evidence_return_never_contains_raw_tool_data(self):
        path = "/Users/private/.codex/plugins/cache/m/p/1/skills/x/SKILL.md"
        row = tool(path, input={"cmd": "cat '" + path + "'; FAKE_SECRET=never-return-me"})
        serialized = json.dumps(extract_codex_usage([row]))
        self.assertNotIn("never-return-me", serialized)
        self.assertNotIn("/Users/private", serialized)
        self.assertNotIn("cmd", serialized)

    def test_missing_identifiers_or_invalid_timestamp_are_not_guessed(self):
        examples = [root(sessionId=None), root(traceId=""), root(id=None),
                    root(startTime="2026-10-06T01:02:03"), root(startTime="n/a")]
        self.assertEqual(extract_codex_usage(examples), [])

    def test_snake_case_api_fields_and_timezone_offsets(self):
        row = root()
        for camel, snake in [("sessionId", "session_id"), ("traceId", "trace_id"),
                             ("parentObservationId", "parent_observation_id"),
                             ("startTime", "start_time")]:
            row[snake] = row.pop(camel)
        row["start_time"] = "2026-10-06T09:02:03.123456789+08:00"
        self.assertEqual(extract_codex_usage([row])[0]["observed_at_ns"],
                         extract_codex_usage([root()])[0]["observed_at_ns"])


if __name__ == "__main__":
    unittest.main()
