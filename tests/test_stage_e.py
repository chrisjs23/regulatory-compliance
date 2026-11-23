"""Check draft agreement, hash binding, undated actions and authority blockers."""
import csv
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest

from icalendar import Calendar

ROOT = Path(__file__).resolve().parents[1]
REVIEWED = ROOT / "deliverables/history/75cff7ce-c62c-405a-9014-65049ec2197c"
sys.path.insert(0, str(ROOT / "regulatory-change-impact-brief/scripts"))
import analyze as a
import publish as p
import reconcile as c


class StageE(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.snaps = self.root / "snapshots"
        self.snaps.mkdir()
        for name in a.NAMES:
            shutil.copy(REVIEWED / "snapshots" / (name + ".json"), self.snaps)
        shutil.copytree(REVIEWED / "sources", self.root / "sources")

    def calendar_events(self):
        cal = Calendar.from_ical((self.root / p.FILES["calendar"]).read_bytes())
        return list(cal.walk("VEVENT"))

    def test_agreement_and_tamper(self):
        self.assertEqual(p.publish(self.root), 1)
        self.assertTrue(p.verify_bundle(self.root))
        seven = json.loads((self.snaps / "07-publication-validation.json").read_bytes())
        self.assertEqual((seven["status"], seven["state"]["publication_status"]), ("partial", "validated"))
        self.assertEqual(len(seven["state"]["review_request_bindings"]), 16)
        with (self.root / p.FILES["register"]).open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 33)
        self.assertEqual(len(self.calendar_events()), 8)
        path = self.root / p.FILES["register"]
        path.write_bytes(path.read_bytes() + b"\n")
        self.assertFalse(p.verify_bundle(self.root))

    def test_undated_proposal_is_explained_and_omitted(self):
        path = self.snaps / "06-actions-and-approvals.json"
        six = json.loads(path.read_bytes())
        six["state"]["proposed_actions"][0]["proposed_due_date"] = None
        path.write_bytes(c.encoded(six))
        self.assertEqual(p.publish(self.root), 1)
        self.assertTrue(p.verify_bundle(self.root))
        self.assertEqual(len(self.calendar_events()), 7)
        brief = (self.root / p.FILES["brief"]).read_text()
        self.assertIn("omitted from calendar: no proposed date", brief)

    def test_binding_authority_blocker_limits_calendar(self):
        for name in a.NAMES[2:]:
            (self.snaps / (name + ".json")).unlink()
        path = self.snaps / "02-source-capture.json"
        two = json.loads(path.read_bytes())
        amend = next(x for x in two["state"]["sources"] if x["id"] == "source-amend")
        amend.update(retrieval_status="unavailable", local_reference=None, content_hash=None)
        path.write_bytes(c.encoded(two))
        self.assertEqual(c.reconcile(self.root), 1)
        self.assertEqual(a.analyze(self.root), 1)
        self.assertEqual(p.publish(self.root), 1)
        seven = json.loads((self.snaps / "07-publication-validation.json").read_bytes())
        self.assertEqual((seven["status"], seven["state"]["publication_status"]), ("blocked", "blocked"))
        self.assertEqual(len(self.calendar_events()), 0)
        self.assertIn("authority-gap-amend", (self.root / p.FILES["brief"]).read_text())
        self.assertTrue(p.verify_bundle(self.root))


if __name__ == "__main__":
    unittest.main()
