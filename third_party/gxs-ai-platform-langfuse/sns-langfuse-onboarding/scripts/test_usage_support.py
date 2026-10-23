"""Offline support checks: synthetic records, fake HTTP/API, temporary state only."""
import copy
import io
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import usage_runtime as runtime
from usage_sink import UsageSink, identity, payload


SETTINGS = {
    "LANGFUSE_PUBLIC_KEY": "pk-test-only", "LANGFUSE_SECRET_KEY": "sk-test-only",
    "LANGFUSE_TRACING_ENVIRONMENT": "test",
}
AUTH = "Basic TEST-PROJECT-AUTH"


def record(**changes):
    value = {
        "agent": "codex", "session_id": "session-one", "kind": "skill", "name": "langfuse",
        "observed_at_ns": 1791270600000000000, "source_trace_id": "a" * 32,
        "source_span_id": "b" * 16, "evidence": "codex_root_turn_explicit_skill_tag",
    }
    value.update(changes)
    return value


def root_observation(**changes):
    value = {
        "type": "AGENT", "name": "Codex Turn", "sessionId": "session-one",
        "traceId": "a" * 32, "id": "b" * 16, "parentObservationId": None,
        "startTime": "2026-10-06T01:50:00Z", "tags": ["skill:langfuse"],
        "metadata": {"run_id": "current-run"},
    }
    value.update(changes)
    return value


def first_span(body):
    return body["resourceSpans"][0]["scopeSpans"][0]["spans"][0]


class SinkTests(unittest.TestCase):
    def test_identity_counts_session_kind_name_and_agent_not_turns_or_retries(self):
        first = identity(record())
        self.assertEqual(first, identity(record(observed_at_ns=123, source_span_id="new-turn",
                                                evidence="another-valid-evidence", raw_prompt="ignored")))
        variants = [identity(record(**change)) for change in (
            {"session_id": "session-two"}, {"kind": "plugin"},
            {"agent": "copilot"}, {"name": "another-skill"},
        )]
        self.assertEqual(len(set([first, *variants])), 5)
        self.assertEqual((len(first[0]), len(first[1])), (32, 16))

    def test_duplicate_turns_and_restart_only_upload_one_session_record(self):
        with tempfile.TemporaryDirectory() as directory:
            sender = Mock()
            sink = UsageSink(SETTINGS, "developer", AUTH, directory=directory, sender=sender)
            first = record()
            result = sink.publish([record(observed_at_ns=first["observed_at_ns"] + 99), first, first])
            sink.close()
            self.assertEqual(result, {"uploaded": 1, "already_recorded": 2})
            self.assertEqual(first_span(sender.call_args.args[0])["startTimeUnixNano"], str(first["observed_at_ns"]))
            again = UsageSink(SETTINGS, "developer", AUTH, directory=directory, sender=sender)
            self.assertEqual(again.publish([first]), {"uploaded": 0, "already_recorded": 1})
            again.close()
            sender.assert_called_once()

    def test_uncertain_upload_retry_preserves_identity_and_first_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            failed = Mock(side_effect=ValueError("synthetic failure"))
            first = record()
            sink = UsageSink(SETTINGS, "developer", AUTH, directory=directory, sender=failed)
            with self.assertRaises(ValueError):
                sink.publish([first])
            sink.close()
            sent = Mock()
            retry = UsageSink(SETTINGS, "developer", AUTH, directory=directory, sender=sent)
            retry.publish([record(observed_at_ns=first["observed_at_ns"] + 999, source_span_id="later-turn")])
            retry.close()
            before, after = first_span(failed.call_args.args[0]), first_span(sent.call_args.args[0])
            for key in ("traceId", "spanId", "startTimeUnixNano", "endTimeUnixNano"):
                self.assertEqual(before[key], after[key])

    def test_payload_and_receipt_database_exclude_raw_content_and_keys(self):
        evidence = record(raw_prompt="DO-NOT-STORE-PROMPT", output="DO-NOT-STORE-OUTPUT",
                          command="DO-NOT-STORE-COMMAND", LANGFUSE_SECRET_KEY="DO-NOT-STORE-KEY")
        with tempfile.TemporaryDirectory() as directory:
            sender = Mock()
            sink = UsageSink(SETTINGS, "developer", AUTH, directory=directory, sender=sender)
            sink.publish([evidence])
            columns = [row[1] for row in sink.db.execute("PRAGMA table_info(receipts)")]
            self.assertEqual(columns, ["id", "first_ns", "sent"])
            sink.close()
            serialized = json.dumps(sender.call_args.args[0])
            for forbidden in ("DO-NOT-STORE", "LANGFUSE_SECRET_KEY", SETTINGS["LANGFUSE_SECRET_KEY"],
                              SETTINGS["LANGFUSE_PUBLIC_KEY"], AUTH, '"input"', '"output"'):
                self.assertNotIn(forbidden, serialized)
            path = next(Path(directory).glob("*.sqlite"))
            content = path.read_bytes()
            for forbidden in ("DO-NOT-STORE", "session-one", "langfuse", "developer", AUTH,
                              SETTINGS["LANGFUSE_SECRET_KEY"], SETTINGS["LANGFUSE_PUBLIC_KEY"]):
                self.assertNotIn(forbidden.encode(), content)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_invalid_identity_or_timestamp_cannot_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            sender = Mock()
            sink = UsageSink(SETTINGS, "developer", AUTH, directory=directory, sender=sender)
            self.addCleanup(sink.close)
            for change in ({"agent": "unverified"}, {"kind": "inventory"}, {"session_id": ""},
                           {"observed_at_ns": True}, {"observed_at_ns": 0}):
                with self.subTest(change=change), self.assertRaises(ValueError):
                    sink.publish([record(**change)])
            sender.assert_not_called()


class CollectionTests(unittest.TestCase):
    def test_every_page_remains_filtered_to_current_run_and_start_time(self):
        api = Mock(side_effect=[
            {"body": {"data": [root_observation()], "meta": {"cursor": "page-two"}}},
            {"body": {"data": [root_observation(sessionId="session-two")], "meta": {}}},
        ])
        started = "2026-10-06T01:49:00Z"
        records = runtime.collect_codex(SETTINGS, "current-run", started, api)
        self.assertEqual({r["session_id"] for r in records}, {"session-one", "session-two"})
        self.assertEqual(api.call_count, 2)
        for call in api.call_args_list:
            self.assertEqual(call.args, (SETTINGS, "observations", "list"))
            args = call.kwargs["extra"]
            filters = json.loads(args[args.index("--filter") + 1])
            self.assertIn({"column": "metadata", "type": "stringObject", "key": "run_id",
                           "operator": "=", "value": "current-run"}, filters)
            self.assertIn({"column": "startTime", "type": "datetime", "operator": ">=", "value": started}, filters)
            self.assertIn({"column": "type", "type": "stringOptions", "operator": "any of", "value": ["AGENT", "TOOL"]}, filters)
        self.assertNotIn("--cursor", api.call_args_list[0].kwargs["extra"])
        self.assertEqual(api.call_args_list[1].kwargs["extra"][-2:], ["--cursor", "page-two"])

    def test_repeated_cursor_fails_instead_of_counting_an_incomplete_batch(self):
        api = Mock(return_value={"data": [root_observation()], "meta": {"cursor": "same"}})
        with self.assertRaisesRegex(ValueError, "pagination"):
            runtime.collect_codex(SETTINGS, "current-run", "start", api)
        self.assertEqual(api.call_count, 2)

    def test_missing_current_run_root_retries_then_reports_unknown(self):
        api = Mock(return_value={"data": [], "meta": {}})
        with patch("usage_runtime.time.sleep") as pause:
            with self.assertRaisesRegex(ValueError, "coverage is unknown"):
                runtime.collect_codex(SETTINGS, "current-run", "start", api, attempts=3)
        self.assertEqual(api.call_count, 3)
        self.assertEqual(pause.call_count, 2)


class RuntimeTests(unittest.TestCase):
    def run_usage(self, **overrides):
        values = dict(command=["test-agent"], env={}, agent="codex", full_content=True,
                      run_id="current-run", settings=SETTINGS, developer="developer",
                      authorization=AUTH, api=Mock())
        values.update(overrides)
        return runtime.run_with_usage(**values)

    def test_loopback_headers_replace_project_authorization_without_mutating_parent(self):
        original = {"OTEL_EXPORTER_OTLP_HEADERS": "Authorization=" + AUTH,
                    "OTEL_EXPORTER_OTLP_TRACES_HEADERS": "Authorization=" + AUTH,
                    "COPILOT_OTEL_HEADERS": "Authorization=" + AUTH,
                    "COPILOT_OTEL_FILE_EXPORTER_PATH": "/not-created/session.jsonl", "OTHER": "preserve"}
        before = copy.deepcopy(original)
        proxy = Mock(local_headers={"X-SNS-Usage-Token": "LOCAL-ONLY"},
                     base_url="http://127.0.0.1:12345", trace_url="http://127.0.0.1:12345/v1/traces")
        actual = runtime.local_copilot_env(original, proxy)
        self.assertEqual(original, before)
        self.assertEqual(actual["OTHER"], "preserve")
        self.assertEqual(actual["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"], proxy.trace_url)
        for name in ("OTEL_EXPORTER_OTLP_HEADERS", "OTEL_EXPORTER_OTLP_TRACES_HEADERS"):
            self.assertEqual(actual[name], "X-SNS-Usage-Token=LOCAL-ONLY")
        self.assertNotIn(AUTH, json.dumps(actual))
        self.assertNotIn("COPILOT_OTEL_HEADERS", actual)
        self.assertNotIn("COPILOT_OTEL_FILE_EXPORTER_PATH", actual)

    def test_wait_process_preserves_exit_or_maps_signal_status(self):
        for child, expected in ((7, 7), (-15, 143)):
            with self.subTest(child=child), patch("usage_runtime.subprocess.Popen") as spawn:
                spawn.return_value.wait.return_value = child
                self.assertEqual(runtime.wait_process(["agent"], {}), expected)

    def test_interrupted_child_is_terminated_and_status_preserved(self):
        with patch("usage_runtime.subprocess.Popen") as spawn:
            spawn.return_value.wait.side_effect = [KeyboardInterrupt, subprocess.TimeoutExpired("agent", 5), -15]
            self.assertEqual(runtime.wait_process(["agent"], {}), 143)
            spawn.return_value.terminate.assert_called_once()

    def test_collection_and_each_receipt_failure_preserve_child_exit_status(self):
        for failure in ("collection", "open", "publish", "close"):
            with self.subTest(failure=failure), patch("usage_runtime.wait_process", return_value=9), \
                    patch("usage_runtime.collect_codex", return_value=[]) as collect, \
                    patch("usage_runtime.UsageSink") as sink_class, \
                    patch("sys.stdout", new_callable=io.StringIO), patch("sys.stderr", new_callable=io.StringIO):
                sink_class.return_value.publish.return_value = {"uploaded": 0, "already_recorded": 0}
                target = {"collection": collect, "open": sink_class,
                          "publish": sink_class.return_value.publish,
                          "close": sink_class.return_value.close}[failure]
                target.side_effect = ValueError("synthetic failure")
                self.assertEqual(self.run_usage(), 9)

    def test_copilot_warns_on_each_actual_coverage_failure_and_no_forwarded_batches(self):
        cases = [{}] + [{"forwarded_batches": 1, key: 1} for key in runtime.INCOMPLETE_COPILOT_COVERAGE]
        for coverage in cases:
            with self.subTest(coverage=coverage), patch("copilot_proxy.CopilotProxy") as proxy_class, \
                    patch("usage_runtime.wait_process", return_value=5), patch("usage_runtime.UsageSink") as sink, \
                    patch("sys.stdout", new_callable=io.StringIO), patch("sys.stderr", new_callable=io.StringIO) as errors:
                proxy = proxy_class.return_value.__enter__.return_value
                proxy.coverage = coverage
                proxy.local_headers = {"X-SNS-Usage-Token": "local"}
                proxy.base_url = "http://127.0.0.1:12345"
                proxy.trace_url = proxy.base_url + "/v1/traces"
                sink.return_value.publish.return_value = {"uploaded": 0, "already_recorded": 0}
                self.assertEqual(self.run_usage(agent="copilot"), 5)
                self.assertIn("coverage is incomplete", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
