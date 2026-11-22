"""Run from the repository root with the skill's Python environment."""
from contextlib import redirect_stdout, redirect_stderr
from email.message import Message
import hashlib
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "regulatory-change-impact-brief"
sys.path.insert(0, str(SKILL / "scripts"))
import run


class ScopeTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name)
        self.output = self.folder / "attempt"
        self.routes = SKILL / "references/routes.json"
        self.body = b"extra,record_version,system_id\na,rev2,TEST-B\nb,rev1,TEST-A\n"

    def invoke(self, *args, failure=None):
        response = io.BytesIO(self.body)
        response.headers = Message()
        response.headers["Content-Type"] = "text/csv"
        with patch.object(run, "urlopen", return_value=response, side_effect=failure), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return run.main(["--routes", str(self.routes), "--output", str(self.output), *args])

    def snapshot(self):
        data = json.loads((self.output / "snapshots/01-scope.json").read_text())
        validator = run.Draft202012Validator(json.loads(run.SCHEMA.read_text()), format_checker=run.Draft202012Validator.FORMAT_CHECKER)
        validator.validate(data)
        return data

    def test_focused(self):
        self.assertEqual(self.invoke("--system-id", "TEST-B"), 0)
        s = self.snapshot()
        self.assertEqual(s["state"]["systems_in_scope"], ["TEST-B"])
        self.assertEqual(s["state"]["as_of"], "2026-08-26T00:00:00+01:00")
        self.assertEqual(set(s["state"]["routes"]), run.LABELS)
        self.assertIsNone(s["predecessor"])
        self.assertEqual(s["consumed_record_ids"], [])
        attempt = s["state"]["source_attempts"][0]
        data = (self.output / attempt["local_reference"]).read_bytes()
        self.assertEqual(attempt["content_hash"], "sha256:" + hashlib.sha256(data).hexdigest())
        self.assertEqual(set(json.loads(data)[0]), {"row", "record_version", "system_id"})

    def test_broad_retry(self):
        self.assertEqual(self.invoke("--broad"), 0)
        first = self.snapshot()
        self.assertEqual(first["state"]["systems_in_scope"], ["TEST-A", "TEST-B"])
        with self.assertRaises(SystemExit):
            self.invoke("--broad")
        self.output = self.folder / "retry"
        self.assertEqual(self.invoke("--broad", "--supersedes-run-id", first["run_id"], "--retry-reason", "repeat check"), 0)
        retry = self.snapshot()
        self.assertEqual(retry["supersedes_run_id"], first["run_id"])
        for key in ("run_id", "snapshot_id"):
            self.assertNotEqual(first[key], retry[key])

    def test_missing_id(self):
        self.assertEqual(self.invoke("--system-id", "UNKNOWN"), 1)
        self.assertIn("UNKNOWN", self.snapshot()["unresolved"][0]["summary"])

    def test_access_failure(self):
        self.assertEqual(self.invoke("--broad", failure=URLError("offline")), 1)
        snapshot = self.snapshot()
        self.assertEqual(snapshot["status"], "blocked")
        self.assertIsNone(snapshot["state"]["source_attempts"][0]["content_hash"])

    def test_ambiguous_register(self):
        self.body += b"duplicate,rev1,TEST-A\n"
        self.assertEqual(self.invoke("--broad"), 1)
        self.assertEqual(self.snapshot()["state"]["source_attempts"][0]["retrieval_status"], "invalid")

    def test_required_inputs(self):
        with self.assertRaises(SystemExit):
            self.invoke()
        self.routes = self.folder / "routes.json"
        self.routes.write_text("{}")
        with self.assertRaises(SystemExit):
            self.invoke("--broad")
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
