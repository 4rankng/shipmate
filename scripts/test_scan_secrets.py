import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scan_secrets import scan

# Positive fixtures are assembled at runtime so this source file never itself
# carries a pattern-shaped literal: CI runs the scanner over the whole tree,
# including this test.
JWT = "eyJ" + "hbGciOiJIUzI1NiIsInR5" + ".c2VjcmV0LXBheWxvYWQ" + ".Zm9vYmFyQ2FzZTEyMw"
AWS_KEY = "AKIA" + "IOSFODNN7EXAMPLE"
GITHUB_TOKEN = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
PRIVATE_KEY_HEADER = "-----BEGIN " + "RSA PRIVATE KEY" + "-----"


class ScanSecretsTests(unittest.TestCase):
    def scan_text(self, text: str) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sample.md").write_text(text, encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = scan([str(root)])
            return code, out.getvalue()

    def test_live_credential_shapes_are_flagged(self):
        code, out = self.scan_text(
            f"jwt: {JWT}\n"
            f"aws: {AWS_KEY}\n"
            f"github: {GITHUB_TOKEN}\n"
            f"{PRIVATE_KEY_HEADER}\n"
        )
        self.assertEqual(code, 1)
        self.assertIn("JWT", out)
        self.assertIn("AWS access key", out)
        self.assertIn("GitHub token", out)
        self.assertIn("private key", out)

    def test_templates_and_placeholder_values_pass(self):
        code, out = self.scan_text(
            'api_key: "{{API_KEY}}"\n'
            "password: changeme-is-not-a-real-secret\n"
            "token: $ENV_LOOKED_UP_AT_RUNTIME\n"
        )
        self.assertEqual(code, 0, out)
        self.assertIn("clean", out)

    def test_expression_assignment_is_not_a_literal(self):
        code, _ = self.scan_text(
            'api_key = os.environ.get("API_KEY")\n'
            'token = config["token"]\n'
        )
        self.assertEqual(code, 0)

    def test_undecodable_files_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # .bin would be skipped by suffix; .dat reaches the utf-8 decode
            # path and must be skipped there without failing the scan.
            (root / "blob.dat").write_bytes(b"\xff\xfe\x00garbage")
            (root / "note.md").write_text("nothing here", encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = scan([str(root)])
            self.assertEqual(code, 0)
            self.assertIn("clean", out.getvalue())


if __name__ == "__main__":
    unittest.main()
