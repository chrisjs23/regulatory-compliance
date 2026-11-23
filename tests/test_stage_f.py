"""Exercise fresh attempts, prior-run history and damaged-output recovery offline."""
import csv
from email.message import Message
import io
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "regulatory-change-impact-brief/scripts"))
import capture
import full_run as f
import publish
import run


class Reply(io.BytesIO):
    def __init__(self, url, content, content_type):
        super().__init__(content.encode())
        self.url = url
        self.status = 200
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def geturl(self):
        return self.url


class StageF(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.output = self.base / "deliverables"
        shutil.copytree(ROOT / "deliverables", self.output)
        self.routes_path = ROOT / "regulatory-change-impact-brief/references/routes.json"
        self.routes = json.loads(self.routes_path.read_bytes())
        self.calls = []
        self.offline = False

    def read(self, url, timeout):
        def matches(name, route):
            if url == route:
                return True
            if name in capture.FIELDS:
                workbook = route.split("/spreadsheets/d/", 1)[1].split("/", 1)[0]
                return url == f"https://docs.google.com/spreadsheets/d/{workbook}/export?format=csv"
            return False
        label = next(name for name, route in self.routes.items() if matches(name, route))
        self.calls.append(label)
        if self.offline:
            raise URLError("offline test")
        if label == "POLICY":
            raise HTTPError(url, 403, "forbidden", Message(), None)
        if label in capture.FIELDS:
            source = json.loads((ROOT / "deliverables/sources/capture" / (label.lower() + ".json")).read_bytes())
            rows = [row["values"] for row in source["rows"]]
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            return Reply(url, stream.getvalue(), "text/csv")
        title, body = {
            "OJ": ("Regulation - EU - 2024/1689", "Article 50 Article 113"),
            "AMEND": ("Regulation - EU - 2026/1744", "2024/1689 Article 1"),
            "CONSOLIDATED": ("02024R1689-20260727", "2024/1689 27.07.2026 Article 50"),
            "LAW": ("Article 50 transparency obligations", "providers; as at 27 July 2026"),
            "TIME": ("AI Act timeline", "2026 Last update 24 July 2026"),
            "FAQ": ("Transparency obligations Article 50", "providers; Last update 24 July 2026"),
        }[label]
        return Reply(url, f"<title>{title}</title><p>{body}</p>", "text/html")

    def invoke(self):
        with patch.object(run, "urlopen", side_effect=self.read), patch.object(capture, "urlopen", side_effect=self.read):
            return f.full_run(self.output, self.routes_path, broad=True, retry_reason="Stage F offline acceptance retry")

    def test_damaged_draft_is_archived_and_fresh_run_replaces_it(self):
        old = json.loads((self.output / "snapshots/01-scope.json").read_bytes())["run_id"]
        (self.output / "compliance-brief.md").write_text("damaged previous draft")
        self.assertEqual(self.invoke(), 1)
        current = json.loads((self.output / "snapshots/01-scope.json").read_bytes())
        self.assertNotEqual(current["run_id"], old)
        self.assertEqual(current["supersedes_run_id"], old)
        self.assertTrue(publish.verify_bundle(self.output))
        archived = self.output / "history" / old
        self.assertEqual((archived / "compliance-brief.md").read_text(), "damaged previous draft")
        manifest = json.loads((archived / "archive-manifest.json").read_bytes())
        self.assertFalse(manifest["prior_bundle_valid"])
        self.assertIn("compliance-brief.md", manifest["damaged"])
        sources = json.loads((self.output / "snapshots/02-source-capture.json").read_bytes())["state"]["sources"]
        self.assertEqual(len(sources), 11)
        self.assertCountEqual(self.calls, list(self.routes) + ["SYSTEMS"])

    def test_network_failure_retains_attempt_without_replacing_current(self):
        old = json.loads((self.output / "snapshots/01-scope.json").read_bytes())["run_id"]
        self.offline = True
        self.assertEqual(self.invoke(), 2)
        self.assertEqual(json.loads((self.output / "snapshots/01-scope.json").read_bytes())["run_id"], old)
        attempt, = list((self.base / "review-runs").glob("run-*"))
        failure = json.loads((attempt / "failure.json").read_bytes())
        self.assertEqual(failure["stage"], "source-capture")
        self.assertEqual(len(json.loads((attempt / "snapshots/02-source-capture.json").read_bytes())["state"]["sources"]), 11)
        self.assertFalse((self.output / "history" / old).exists())


if __name__ == "__main__":
    unittest.main()
