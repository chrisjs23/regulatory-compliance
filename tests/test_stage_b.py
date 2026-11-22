"""Offline Stage B acceptance checks. No real source or deliverable is changed."""
from contextlib import redirect_stdout
import csv
from email.message import Message
import hashlib
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "regulatory-change-impact-brief"
sys.path.insert(0, str(SKILL / "scripts"))
import capture
import run


class Reply(io.BytesIO):
    def __init__(self, url, content, mime):
        super().__init__(content.encode())
        self.url = url
        self.headers = Message()
        self.headers["Content-Type"] = mime
        self.status = 200

    def geturl(self):
        return self.url


class CaptureTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.output = Path(temp.name)
        routes_file = SKILL / "references/routes.json"
        self.routes = json.loads(routes_file.read_bytes())
        self.calls = []
        self.page = {
            "OJ": ("Regulation - EU - 2024/1689", "Article 50 Article 113"),
            "AMEND": ("Regulation - EU - 2026/1744", "2024/1689 Article 1"),
            "CONSOLIDATED": ("02024R1689-20260727", "2024/1689 27.07.2026 Article 50"),
            "LAW": ("Article 50: transparency obligations", "providers; as at 27 July 2026"),
            "TIME": ("AI Act timeline", "Last update 24 July 2026"),
            "FAQ": ("Transparency obligations under article 50", "providers; Last update 24 July 2026"),
            "POLICY": ("Quillhaven internal policies", "Version v1 effective 2026-08-01"),
        }
        self.rows = {}
        for label, spec in capture.FIELDS.items():
            data = {"system_id": "AI-001", "record_id": "REC-001", "action_id": "ACT-001",
                    "reported_at": "2026-08-26", "due_date": "2026-09-03", "evidence_updated_at": "2026-08-26",
                    "record_version": "register-2026-08-26", "source_version": "calendar-2026-08-26"}
            self.rows[label] = {field: data[field] if field in data else capture.TERMS[field][0]
                                for field in reversed(spec.split())}
            self.rows[label]["unrelated"] = "never save extra columns"
        self.errors = {}
        with patch.object(run, "urlopen", side_effect=self.read), redirect_stdout(io.StringIO()):
            self.assertEqual(run.main(["--routes", str(routes_file), "--broad", "--output", str(self.output)]), 0)
        self.calls.clear()

    def read(self, url, timeout):
        label = next(k for k, v in self.routes.items() if url == v or url == v + "/export?format=csv")
        self.calls.append(label)
        if label in self.errors:
            raise self.errors[label]
        if label in self.rows:
            buf = io.StringIO()
            row = self.rows[label]
            writer = csv.DictWriter(buf, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
            return Reply(url, buf.getvalue(), "text/csv")
        title, text = self.page[label]
        return Reply(url, f"<title>{title}</title><p>{text}</p>", "text/html")

    def perform(self, expected_code):
        with patch.object(capture, "urlopen", side_effect=self.read), redirect_stdout(io.StringIO()), patch.dict(
                capture.TERMS, policy_paragraphs=["Version v1 effective 2026-08-01"]):
            self.assertEqual(capture.capture(self.output), expected_code)
        doc = json.loads((self.output / "snapshots/02-source-capture.json").read_bytes())
        self.assertCountEqual(self.calls, self.routes)
        return doc, {s["id"]: s for s in doc["state"]["sources"]}

    def test_complete_chain_and_retention(self):
        doc, sources = self.perform(0)
        prior = (self.output / "snapshots/01-scope.json").read_bytes()
        self.assertEqual(doc["run_id"], json.loads(prior)["run_id"])
        self.assertEqual(doc["predecessor"]["sha256"], "sha256:" + hashlib.sha256(prior).hexdigest())
        self.assertEqual(len(sources), 11)
        for rec in sources.values():
            data = (self.output / rec["local_reference"]).read_bytes()
            self.assertEqual(rec["content_hash"], capture.digest(data))
            self.assertNotIn(b"never save extra columns", data)
        systems = json.loads((self.output / sources["source-systems"]["local_reference"]).read_bytes())
        self.assertEqual((systems["rows"][0]["row"], systems["rows"][0]["values"]["system_id"]), (2, "AI-001"))
        faq = json.loads((self.output / sources["source-faq"]["local_reference"]).read_bytes())
        self.assertTrue(any(b["block"] and "Last update" in b["text"] for b in faq["blocks"]))

    def test_single_command_for_new_run(self):
        dest = self.output / "new-run"
        with patch.object(run, "urlopen", side_effect=self.read), patch.object(capture, "urlopen", side_effect=self.read), redirect_stdout(io.StringIO()):
            # POLICY has no permitted paragraphs in the default retention list.
            code = run.main(["--broad", "--through-capture", "--output", str(dest),
                             "--routes", str(SKILL / "references/routes.json")])
        self.assertEqual(code, 1)
        self.assertEqual(self.calls.count("SYSTEMS"), 2)
        first, second = [json.loads(p.read_bytes()) for p in sorted((dest / "snapshots").glob("*.json"))]
        self.assertEqual(first["run_id"], second["run_id"])
        self.assertEqual(second["status"], "partial")

    def test_failures_retained(self):
        self.errors["POLICY"] = HTTPError(self.routes["POLICY"], 403, "forbidden", {}, None)
        self.errors["OJ"] = URLError("offline")
        self.page["AMEND"] = ("Sign in", "Please log in")
        self.page["TIME"] = ("AI Act timeline", "Last update 27 August 2026")
        doc, sources = self.perform(1)
        self.assertEqual(doc["status"], "blocked")
        for label in ("oj", "policy"):
            self.assertEqual(sources["source-" + label]["retrieval_status"], "unavailable")
            self.assertIsNone(sources["source-" + label]["content_hash"])
        self.assertEqual(sources["source-amend"]["retrieval_status"], "invalid")
        self.assertEqual(sources["source-time"]["retrieval_status"], "unverified")
        self.assertIsNotNone(sources["source-time"]["local_reference"])

    def test_source_changes(self):
        self.rows["SYSTEMS"]["owner"] = "private changed value"
        self.rows["CALENDAR"].pop("action_id")
        self.rows["EVIDENCE"]["reported_at"] = "2026-08-27"
        doc, sources = self.perform(1)
        self.assertEqual(doc["status"], "partial")
        self.assertEqual(sources["source-calendar"]["retrieval_status"], "invalid")
        self.assertEqual(sources["source-evidence"]["version_metadata"]["row_revisions_or_dates"], ["2026-08-27"])
        data = (self.output / sources["source-systems"]["local_reference"]).read_text()
        self.assertNotIn("private changed value", data)
        self.assertIn("owner", sources["source-systems"]["issues"][0])

    def test_browser_selection_retains_403_and_requires_current_run(self):
        scope = json.loads((self.output / "snapshots/01-scope.json").read_bytes())
        item = dict(run_id=scope["run_id"], locator=self.routes["POLICY"], title="Current Internal Policies",
                    section="Review roles", passage="Operations reviews proposed dates.",
                    page_loaded_at=run.now(), captured_at=run.now())
        path = self.output / "selection.json"
        for override in ({"run_id": "other"}, {"locator": self.routes["LAW"]},
                         {"page_loaded_at": "2000-01-01T00:00:00+00:00"}, {"passage": ""},
                         {"captured_at": "2999-01-01T00:00:00Z"}):
            path.write_text(json.dumps(item | override))
            with self.assertRaises(ValueError):
                capture.read_selection(path, scope)
        path.write_text(json.dumps(item))
        self.errors["POLICY"] = HTTPError(self.routes["POLICY"], 403, "forbidden", {}, None)
        with patch.object(capture, "urlopen", side_effect=self.read), redirect_stdout(io.StringIO()):
            self.assertEqual(capture.capture(self.output, [path]), 1)
        snapshot = json.loads((self.output / "snapshots/02-source-capture.json").read_bytes())
        direct, browser = [s for s in snapshot["state"]["sources"] if s["label"] == "POLICY"]
        self.assertEqual(direct["http_status"], 403)
        self.assertEqual(browser["retrieval_status"], "unverified")
        data = (self.output / browser["local_reference"]).read_bytes()
        self.assertEqual(browser["content_hash"], capture.digest(data))
        self.assertEqual(json.loads(data), item)

    def test_predecessor_damage_and_overwrite(self):
        self.perform(0)
        with self.assertRaisesRegex(ValueError, "already exists"):
            capture.capture(self.output)
        (self.output / "sources/systems-scope.json").write_text("damaged")
        with self.assertRaisesRegex(ValueError, "Scope extract hash mismatch"):
            capture.capture(self.output)


if __name__ == "__main__":
    unittest.main()
