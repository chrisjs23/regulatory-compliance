"""Exercise stage C against the approved, locally retained stage B run."""
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "regulatory-change-impact-brief/scripts"))
import reconcile as c

RETRY = ROOT / "review-runs/policy-retry"


class StageC(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.snaps = self.root / "snapshots"
        self.snaps.mkdir()
        for f in c.FILES[:2]:
            shutil.copy(RETRY / "snapshots" / (f+".json"), self.snaps)
        shutil.copytree(RETRY / "sources", self.root / "sources")

    def build(self):
        self.assertEqual(c.reconcile(self.root, sorted(RETRY.glob("policy-selection-*.json")),
                                      ROOT / "interviews/project-b-regulatory-compliance-interview4.md"), 1)
        docs = [json.loads(p.read_bytes()) for p in sorted(self.snaps.glob("*.json"))]
        available = set()
        for index, doc in enumerate(docs):
            c.VALIDATE(doc)
            self.assertFalse(set(doc["consumed_record_ids"])-available)
            available.update(doc["produced_record_ids"])
            if index:
                prev=doc["predecessor"]
                self.assertEqual(prev["sha256"],c.digest((self.root/prev["path"]).read_bytes()))
                self.assertEqual(prev["snapshot_id"],docs[index-1]["snapshot_id"])
                self.assertEqual(doc["run_id"],docs[0]["run_id"])
        return docs[2],docs[3]

    def test_rule_and_evidence_trace(self):
        authority, facts = self.build()
        transition = next(r for r in authority["state"]["timing_rules"] if r["id"]=="art111-4")
        for cite in transition["passages"]:
            name=cite["source_id"].removeprefix("source-")
            blocks=json.loads((self.root/f"sources/capture/{name}.json").read_bytes())["blocks"]
            self.assertEqual(cite["text"], next(b["text"] for b in blocks if b["block"]==cite["block"]))
        state=facts["state"]
        systems=[r for r in state["system_facts"] if "values" in r]
        self.assertEqual(len(systems),8)
        row=json.loads((self.root/"sources/capture/systems.json").read_bytes())["rows"][0]
        self.assertEqual(systems[0]["values"],row["values"])
        self.assertEqual(systems[0]["row"],row["row"])
        self.assertEqual({r["system_id"] for r in state["conflicts"]},{"AI-003","AI-007"})
        self.assertTrue(any(r.get("reported_state")=="missing" and r["owner"]=="Admissions" for r in state["evidence_gaps"]))
        self.assertEqual(next(r for r in state["policy_controls"] if r["id"]=="policy-effective")["effective_date"],"2026-08-15")
        self.assertEqual(len(state["calendar_proposals"]),8)

    def test_missing_amendment(self):
        p=self.snaps/"02-source-capture.json"
        doc=json.loads(p.read_bytes())
        rec=next(r for r in doc["state"]["sources"] if r["id"]=="source-amend")
        rec.update(retrieval_status="unavailable",local_reference=None,content_hash=None)
        p.write_bytes(c.encoded(doc))
        third,fourth=self.build()
        self.assertEqual((third["status"],fourth["status"]),("blocked","blocked"))
        self.assertEqual(third["state"]["binding_rules"],[])
        self.assertEqual(third["state"]["timing_rules"],[])
        self.assertTrue(fourth["state"]["incident_evidence"])

    def test_damaged_capture(self):
        (self.root/"sources/capture/amend.json").write_text("{}")
        with self.assertRaisesRegex(ValueError,"Damaged capture"):
            c.reconcile(self.root)
        self.assertFalse((self.snaps/"03-authority-and-timing.json").exists())

if __name__=="__main__":
    unittest.main()
