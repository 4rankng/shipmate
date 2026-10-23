"""Offline fixtures and loopback-only checks; no real credentials or uploads."""

import copy
import gzip
import http.client
import json
import unittest
from unittest.mock import Mock, patch

from copilot_proxy import CopilotProxy, SkillUsageExtractor


TRACE = "1" * 32
SPAN = "2" * 16
ROOT = "3" * 16
TIME_NS = "1791270600000000123"


def attr(key, value):
    return {"key": key, "value": {"stringValue": value}}


def skill_event(skill="code-review", plugin="team-plugin"):
    values = [attr("github.copilot.skill.name", skill),
              attr("github.copilot.skill.content", "PRIVATE SKILL BODY"),
              attr("github.copilot.skill.path", "/private/user/skill/SKILL.md")]
    if plugin:
        values.extend([attr("github.copilot.skill.plugin_name", plugin),
                       attr("github.copilot.skill.plugin_version", "1.2.3")])
    return {"name": "github.copilot.skill.invoked", "timeUnixNano": TIME_NS,
            "attributes": values}


def span(*, session="session-one", events=None, span_id=SPAN, trace_id=TRACE, parent=None):
    result = {"traceId": trace_id, "spanId": span_id, "name": "invoke_agent",
              "attributes": [], "events": [] if events is None else events}
    if session:
        result["attributes"].append(attr("gen_ai.conversation.id", session))
    if parent:
        result["parentSpanId"] = parent
    return result


def batch(*spans):
    return {"resourceSpans": [{"scopeSpans": [{"spans": list(spans)}]}]}


class ExtractionTests(unittest.TestCase):
    def test_current_copilot_gen_ai_skill_name_matches_observed_native_schema(self):
        event = skill_event(plugin=None)
        event["attributes"][0]["key"] = "gen_ai.skill.name"
        event["attributes"].extend([
            attr("github.copilot.skill.source", "personal"),
            attr("github.copilot.skill.invocation_trigger", "agent"),
        ])
        result = SkillUsageExtractor().extract(batch(span(events=[event])))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "code-review")
        self.assertEqual(result[0]["session_id"], "session-one")

    def test_conflicting_current_and_legacy_skill_names_are_not_guessed(self):
        event = skill_event()
        event["attributes"].append(attr("gen_ai.skill.name", "different-skill"))
        extractor = SkillUsageExtractor()
        self.assertEqual(extractor.extract(batch(span(events=[event]))), [])
        self.assertEqual(extractor.coverage["conflicting_skill_identity"], 1)
        self.assertEqual(extractor.coverage["skill_events_missing_identity"], 1)

    def test_actual_skill_event_produces_only_whitelisted_session_evidence(self):
        source = batch(span(events=[skill_event()]))
        before = copy.deepcopy(source)
        result = SkillUsageExtractor().extract(source)
        self.assertEqual(source, before)
        self.assertEqual([(r["kind"], r["name"]) for r in result],
                         [("skill", "code-review"), ("plugin", "team-plugin")])
        for record in result:
            self.assertEqual(record["agent"], "copilot")
            self.assertEqual(record["session_id"], "session-one")
            self.assertEqual(record["observed_at_ns"], int(TIME_NS))
            self.assertEqual(record["source_trace_id"], TRACE)
            self.assertEqual(record["source_span_id"], SPAN)
            self.assertEqual(record["plugin_version"], "1.2.3")
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertNotIn("/private", json.dumps(result))

    def test_inventory_unrelated_events_and_no_event_are_not_usage(self):
        available = span(events=[{"name": "github.copilot.skills.available", "attributes":
                                 [attr("github.copilot.skill.name", "available-only")]}])
        available["attributes"].append(attr("github.copilot.skill.name", "listed-only"))
        self.assertEqual(SkillUsageExtractor().extract(batch(available, span())), [])

    def test_repeated_uses_deduplicate_per_session_kind_and_name(self):
        extractor = SkillUsageExtractor()
        first = extractor.extract(batch(span(events=[skill_event(), skill_event()])))
        second = extractor.extract(batch(span(events=[skill_event("other-skill")])))
        third = extractor.extract(batch(span(session="session-two", events=[skill_event()])))
        self.assertEqual(len(first), 2)
        self.assertEqual([(r["kind"], r["name"]) for r in second], [("skill", "other-skill")])
        self.assertEqual(len(third), 2)

    def test_root_identity_resolves_same_batch_regardless_of_order_and_cached_trace(self):
        extractor = SkillUsageExtractor()
        child = span(session=None, events=[skill_event()], parent=ROOT)
        result = extractor.extract(batch(child, span(span_id=ROOT)))
        self.assertEqual(len(result), 2)
        child["events"] = [skill_event("second-skill", plugin=None)]
        self.assertEqual(extractor.extract(batch(child))[0]["session_id"], "session-one")
        child["traceId"] = "4" * 32
        self.assertEqual(extractor.extract(batch(child)), [])

    def test_missing_identity_invalid_ids_and_missing_timestamp_stay_unknown(self):
        examples = [span(session=None, events=[skill_event()]),
                    span(trace_id="invalid", events=[skill_event()]),
                    span(span_id="0" * 16, events=[skill_event()])]
        no_time = span(events=[skill_event()])
        del no_time["events"][0]["timeUnixNano"]
        examples.append(no_time)
        for source in examples:
            with self.subTest(source=source):
                extractor = SkillUsageExtractor()
                self.assertEqual(extractor.extract(batch(source)), [])
                self.assertEqual(extractor.coverage["skill_events_missing_identity"], 1)

    def test_absent_plugin_does_not_invent_attribution(self):
        result = SkillUsageExtractor().extract(batch(span(events=[skill_event(plugin=None)])))
        self.assertEqual(len(result), 1)
        self.assertNotIn("plugin_name", result[0])

    def test_bound_retains_existing_deduplication_and_reports_missing_coverage(self):
        extractor = SkillUsageExtractor(max_records=1)
        result = extractor.extract(batch(span(events=[skill_event()])))
        self.assertEqual(len(result), 1)
        self.assertEqual(extractor.coverage["usage_capacity_exceeded"], 1)
        self.assertEqual(extractor.extract(batch(span(events=[skill_event()]))), [])


class ProxyTests(unittest.TestCase):
    def setUp(self):
        self.records = []
        self.proxy = CopilotProxy("Basic TEST-ONLY", self.records.append, timeout=1)
        self.proxy._forward = Mock(return_value=(200, b"{}", "application/json"))
        self.proxy.start()
        self.addCleanup(self.proxy.close)

    def post(self, body, *, path="/v1/traces", extra=None, authenticated=True):
        connection = http.client.HTTPConnection("127.0.0.1", self.proxy._server.server_port, timeout=3)
        headers = {"Content-Type": "application/json"}
        if authenticated:
            headers.update(self.proxy.local_headers)
        headers.update(extra or {})
        try:
            connection.request("POST", path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_gzip_is_forwarded_unchanged_and_records_are_deduplicated(self):
        payload = gzip.compress(json.dumps(batch(span(events=[skill_event()]))).encode())
        self.assertEqual(self.post(payload, extra={"Content-Encoding": "gzip"})[0], 200)
        self.assertEqual(self.post(payload, extra={"Content-Encoding": "gzip"})[0], 200)
        self.assertEqual(len(self.records), 2)
        self.proxy._forward.assert_called_with(payload, "application/json", "gzip")
        self.assertNotIn("TEST-ONLY", json.dumps(self.proxy.local_headers))

    def test_wrong_path_host_or_token_cannot_reach_upstream(self):
        for arguments in ({"path": "/v1/metrics"}, {"path": "https://example.com/v1/traces"},
                          {"path": "/v1/traces?redirect=https://example.com"},
                          {"extra": {"Host": "example.com"}}, {"authenticated": False},
                          {"extra": {"X-SNS-Usage-Token": "wrong"}}):
            with self.subTest(arguments=arguments):
                self.assertIn(self.post(b"{}", **arguments)[0], (401, 404))
        self.proxy._forward.assert_not_called()

    def test_oversized_request_is_rejected_before_forwarding(self):
        self.proxy._max_body_bytes = 4
        self.assertEqual(self.post(b"12345")[0], 413)
        self.proxy._forward.assert_not_called()

    def test_unexpected_format_is_forwarded_and_reports_coverage_failure(self):
        self.assertEqual(self.post(b"opaque protobuf", extra={"Content-Type": "application/x-protobuf"})[0], 200)
        self.assertEqual(self.proxy.coverage["unsupported_content_type"], 1)
        self.assertEqual(self.post(b"not json")[0], 200)
        self.assertEqual(self.proxy.coverage["invalid_json_or_gzip"], 1)
        self.assertEqual(self.records, [])

    def test_gzip_expansion_is_bounded_without_changing_raw_forward(self):
        self.proxy._max_decoded_bytes = 8
        payload = gzip.compress(b" " * 100)
        self.assertEqual(self.post(payload, extra={"Content-Encoding": "gzip"})[0], 200)
        self.assertEqual(self.proxy.coverage["decoded_body_too_large"], 1)
        self.assertEqual(self.records, [])

    def test_malformed_gzip_is_forwarded_without_unhandled_parser_failure(self):
        payload = b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03\x07"
        self.assertEqual(self.post(payload, extra={"Content-Encoding": "gzip"})[0], 200)
        self.assertEqual(self.proxy.coverage["invalid_json_or_gzip"], 1)
        self.assertEqual(self.records, [])

    def test_upstream_failure_does_not_emit_records(self):
        self.proxy._forward.side_effect = OSError("PRIVATE diagnostics")
        self.assertEqual(self.post(json.dumps(batch(span(events=[skill_event()]))).encode()), (502, b"{}"))
        self.assertEqual(self.records, [])
        self.assertEqual(self.proxy.coverage["upstream_failures"], 1)

    def test_callback_failures_are_reported_without_leaking_diagnostics(self):
        self.proxy._on_record = Mock(side_effect=ValueError("PRIVATE callback detail"))
        self.assertEqual(self.post(json.dumps(batch(span(events=[skill_event()]))).encode()), (200, b"{}"))
        self.assertEqual(self.proxy.coverage["usage_callback_failures"], 2)

    def test_close_waits_for_completed_callback_and_releases_socket(self):
        port = self.proxy._server.server_port
        self.post(json.dumps(batch(span(events=[skill_event()]))).encode())
        self.proxy.close()
        self.assertEqual(len(self.records), 2)
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
        with self.assertRaises(OSError):
            connection.request("POST", "/v1/traces", body=b"{}")
        connection.close()


class UpstreamBoundaryTests(unittest.TestCase):
    @patch("copilot_proxy.http.client.HTTPSConnection")
    def test_fixed_tls_destination_and_no_local_headers_leak(self, factory):
        connection = factory.return_value
        response = connection.getresponse.return_value
        response.status = 200
        response.read.return_value = b"{}"
        response.getheader.return_value = "application/json"
        proxy = CopilotProxy("Basic TEST-ONLY", lambda _: None)
        self.assertEqual(proxy._forward(b"RAW", "application/json", "gzip")[0], 200)
        self.assertEqual(factory.call_args.args[:2], ("langfuse.stg.dakota.com.sg", 443))
        self.assertTrue(factory.call_args.kwargs["context"].check_hostname)
        args, kwargs = connection.request.call_args
        self.assertEqual(args, ("POST", "/api/public/otel/v1/traces"))
        self.assertEqual(kwargs["body"], b"RAW")
        self.assertEqual(kwargs["headers"]["Authorization"], "Basic TEST-ONLY")
        self.assertNotIn("X-SNS-Usage-Token", kwargs["headers"])
        response.status = 307
        with self.assertRaisesRegex(ValueError, "redirects"):
            proxy._forward(b"RAW", "application/json", "")


if __name__ == "__main__":
    unittest.main()
