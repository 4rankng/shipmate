import contextlib
import io
import tempfile
from pathlib import Path
from unittest import TestCase, mock

import confluence_cli


class ConfluenceCliSafetyTests(TestCase):
    def test_get_body_output_file_writes_exact_body_without_printing_it(self):
        body = "<p>secret body</p>"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "body.html"
            args = confluence_cli.build_parser().parse_args(
                ["get", "123", "--body-output-file", str(output)]
            )
            with mock.patch.object(confluence_cli, "request", return_value={
                "id": "123", "body": {"storage": {"value": body}}
            }), contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(args.func(args), 0)
            self.assertEqual(output.read_text(), body)
            self.assertNotIn(body, stdout.getvalue())

    def test_update_aborts_when_expected_body_differs_beyond_trailing_whitespace(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.html"
            candidate = Path(directory) / "candidate.html"
            baseline.write_text("<p>old</p>\n")
            candidate.write_text("<p>new</p>")
            args = confluence_cli.build_parser().parse_args([
                "update", "123", "--expected-body-file", str(baseline),
                "--body-file", str(candidate), "--verify",
            ])
            current = {"title": "T", "version": {"number": 7},
                       "body": {"storage": {"value": "<p>changed</p>"}}}
            with mock.patch.object(confluence_cli, "request", return_value=current) as request:
                self.assertEqual(args.func(args), 1)
            request.assert_called_once()

    def test_update_allows_trailing_whitespace_and_verifies_normalized_readback(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.html"
            candidate = Path(directory) / "candidate.html"
            baseline.write_text("<p>old</p>\n")
            candidate.write_text(
                '<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">json</ac:parameter>'
                '<ac:parameter ac:name="breakoutMode">wide</ac:parameter><p>{"a":1}</p></ac:structured-macro>'
            )
            args = confluence_cli.build_parser().parse_args([
                "update", "123", "--expected-body-file", str(baseline),
                "--body-file", str(candidate), "--verify",
            ])
            current = {"title": "T", "version": {"number": 7},
                       "body": {"storage": {"value": "<p>old</p>   "}}}
            put = {"id": "123"}
            stored = {"body": {"storage": {"value":
                '<ac:structured-macro ac:name="code" ac:macro-id="x">'
                '<ac:parameter ac:name="breakoutMode">wide</ac:parameter>'
                '<ac:parameter ac:name="language">json</ac:parameter><p>{&quot;a&quot;:1}</p>'
                '</ac:structured-macro>'}}}
            with mock.patch.object(confluence_cli, "request", side_effect=[current, put, stored]):
                self.assertEqual(args.func(args), 0)

    def test_normalization_does_not_hide_semantic_change(self):
        self.assertNotEqual(
            confluence_cli._normalize_storage("<p>before</p>"),
            confluence_cli._normalize_storage("<p>after</p>"),
        )

    def test_update_requires_concurrency_guard_and_verification(self):
        with self.assertRaises(SystemExit):
            confluence_cli.build_parser().parse_args(["update", "123", "--body", "<p>x</p>"])
        with self.assertRaises(SystemExit):
            confluence_cli.build_parser().parse_args([
                "update", "123", "--body", "<p>x</p>",
                "--expected-body-file", "baseline.html",
            ])
        with self.assertRaises(SystemExit):
            confluence_cli.build_parser().parse_args([
                "update", "123", "--body", "<p>x</p>", "--body-file", "body.html",
                "--expected-body-file", "baseline.html", "--verify",
            ])

    def test_update_rejects_empty_explicit_body_before_any_request(self):
        for source in (["--body", ""], ["--body", "   "]):
            with self.subTest(source=source):
                args = confluence_cli.build_parser().parse_args([
                    "update", "123", *source,
                    "--expected-body-file", "baseline.html", "--verify",
                ])
                with mock.patch.object(confluence_cli, "request") as request:
                    self.assertEqual(args.func(args), 1)
                request.assert_not_called()
        with tempfile.TemporaryDirectory() as directory:
            empty = Path(directory) / "empty.html"
            empty.write_text("")
            args = confluence_cli.build_parser().parse_args([
                "update", "123", "--body-file", str(empty),
                "--expected-body-file", "baseline.html", "--verify",
            ])
            with mock.patch.object(confluence_cli, "request") as request:
                self.assertEqual(args.func(args), 1)
            request.assert_not_called()

    def test_parameter_text_inside_cdata_is_not_reordered(self):
        first = (
            '<ac:structured-macro ac:name="code"><ac:plain-text-body><![CDATA['
            '<ac:parameter ac:name="a">1</ac:parameter>'
            '<ac:parameter ac:name="b">2</ac:parameter>'
            ']]></ac:plain-text-body></ac:structured-macro>'
        )
        second = first.replace(
            '<ac:parameter ac:name="a">1</ac:parameter>'
            '<ac:parameter ac:name="b">2</ac:parameter>',
            '<ac:parameter ac:name="b">2</ac:parameter>'
            '<ac:parameter ac:name="a">1</ac:parameter>',
        )
        self.assertNotEqual(
            confluence_cli._normalize_storage(first),
            confluence_cli._normalize_storage(second),
        )

    def test_parameter_text_inside_pre_is_not_reordered(self):
        first = (
            '<ac:structured-macro ac:name="code"><pre>'
            '<ac:parameter ac:name="a">1</ac:parameter>'
            '<ac:parameter ac:name="b">2</ac:parameter>'
            '</pre></ac:structured-macro>'
        )
        second = first.replace(
            '<ac:parameter ac:name="a">1</ac:parameter>'
            '<ac:parameter ac:name="b">2</ac:parameter>',
            '<ac:parameter ac:name="b">2</ac:parameter>'
            '<ac:parameter ac:name="a">1</ac:parameter>',
        )
        self.assertNotEqual(
            confluence_cli._normalize_storage(first),
            confluence_cli._normalize_storage(second),
        )

    def test_code_payload_whitespace_remains_significant(self):
        first = '<ac:plain-text-body><![CDATA[a >   < b]]></ac:plain-text-body>'
        second = '<ac:plain-text-body><![CDATA[a > < b]]></ac:plain-text-body>'
        self.assertNotEqual(
            confluence_cli._normalize_storage(first),
            confluence_cli._normalize_storage(second),
        )

    def test_code_payload_entity_encoding_remains_significant(self):
        first = '<ac:plain-text-body><![CDATA[&amp;amp;]]></ac:plain-text-body>'
        second = '<ac:plain-text-body><![CDATA[&amp;]]></ac:plain-text-body>'
        self.assertNotEqual(
            confluence_cli._normalize_storage(first),
            confluence_cli._normalize_storage(second),
        )

    def test_generated_wrapper_id_normalizes_without_touching_payload(self):
        candidate = '<ac:plain-text-body><![CDATA[a >   < b]]></ac:plain-text-body>'
        stored = (
            '<ac:plain-text-body ac:local-id="generated"><![CDATA[a >   < b]]>'
            '</ac:plain-text-body>'
        )
        self.assertEqual(
            confluence_cli._normalize_storage(candidate),
            confluence_cli._normalize_storage(stored),
        )

    def test_generated_id_normalization_is_limited_to_opening_tag_attributes(self):
        candidate = '<p title="a > b">keep local-id="human text"</p>'
        stored = '<p title="a > b" local-id="generated">keep local-id="human text"</p>'
        self.assertEqual(
            confluence_cli._normalize_storage(candidate),
            confluence_cli._normalize_storage(stored),
        )
        self.assertNotEqual(
            confluence_cli._normalize_storage('<p>keep local-id="human text"</p>'),
            confluence_cli._normalize_storage("<p>keep</p>"),
        )
        self.assertNotEqual(
            confluence_cli._normalize_storage(
                '<p title=\'keep local-id="human text"\'>body</p>'
            ),
            confluence_cli._normalize_storage("<p title='keep'>body</p>"),
        )

    def test_nested_code_parameter_moved_outside_container_remains_different(self):
        nested = (
            '<ac:structured-macro ac:name="code"><div>'
            '<ac:parameter ac:name="language">json</ac:parameter></div>'
            '<ac:parameter ac:name="breakoutMode">wide</ac:parameter>'
            '<p>body</p></ac:structured-macro>'
        )
        moved = (
            '<ac:structured-macro ac:name="code">'
            '<ac:parameter ac:name="language">json</ac:parameter><div></div>'
            '<ac:parameter ac:name="breakoutMode">wide</ac:parameter>'
            '<p>body</p></ac:structured-macro>'
        )
        self.assertNotEqual(
            confluence_cli._normalize_storage(nested),
            confluence_cli._normalize_storage(moved),
        )

    def test_direct_expand_macro_parameters_are_unordered(self):
        first = (
            '<ac:structured-macro ac:name="expand">'
            '<ac:parameter ac:name="title">Details</ac:parameter>'
            '<ac:parameter ac:name="breakoutWidth">760</ac:parameter>'
            '<ac:rich-text-body><p>body</p></ac:rich-text-body>'
            '</ac:structured-macro>'
        )
        second = first.replace(
            '<ac:parameter ac:name="title">Details</ac:parameter>'
            '<ac:parameter ac:name="breakoutWidth">760</ac:parameter>',
            '<ac:parameter ac:name="breakoutWidth">760</ac:parameter>'
            '<ac:parameter ac:name="title">Details</ac:parameter>',
        )
        self.assertEqual(
            confluence_cli._normalize_storage(first),
            confluence_cli._normalize_storage(second),
        )

    def test_escaped_prose_is_not_reinterpreted_as_storage_markup(self):
        first = '<p>&lt;span local-id="human"&gt;x&lt;/span&gt;</p>'
        second = '<p>&lt;span local-id="changed"&gt;x&lt;/span&gt;</p>'
        self.assertNotEqual(
            confluence_cli._normalize_storage(first),
            confluence_cli._normalize_storage(second),
        )

    def test_entity_encoded_attribute_survives_generated_id_normalization(self):
        candidate = '<p title="&quot;quoted&quot;">body</p>'
        stored = '<p title="&quot;quoted&quot;" local-id="generated">body</p>'
        self.assertEqual(
            confluence_cli._normalize_storage(candidate),
            confluence_cli._normalize_storage(stored),
        )

    def test_literal_code_payload_entities_remain_significant(self):
        first = '<code>&amp;amp; &gt;   &lt;</code>'
        second = '<code>&amp; &gt; &lt;</code>'
        self.assertNotEqual(
            confluence_cli._normalize_storage(first),
            confluence_cli._normalize_storage(second),
        )
