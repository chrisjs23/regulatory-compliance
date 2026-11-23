"""Focused Stage D checks against retained Stage B and C evidence."""
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
REVIEWED = ROOT / "deliverables/history/75cff7ce-c62c-405a-9014-65049ec2197c"
sys.path.insert(0, str(ROOT / "regulatory-change-impact-brief/scripts"))
import analyze as a
import reconcile as c


class StageD(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.snaps = self.root / "snapshots"
        self.snaps.mkdir()
        for name in a.NAMES[:4]:
            shutil.copy(REVIEWED / "snapshots" / (name + ".json"), self.snaps)
        shutil.copytree(REVIEWED / "sources", self.root / "sources")

    def build(self):
        self.assertEqual(a.analyze(self.root), 1)
        five, six = [json.loads((self.snaps / (name + ".json")).read_bytes()) for name in a.NAMES[4:]]
        available = set()
        for name in a.NAMES:
            doc = json.loads((self.snaps / (name + ".json")).read_bytes())
            c.VALIDATE(doc)
            self.assertFalse(set(doc["consumed_record_ids"]) - available)
            available.update(doc["produced_record_ids"])
            if doc["sequence"] > 1:
                self.assertEqual(doc["predecessor"]["sha256"],
                                 c.digest((self.root / doc["predecessor"]["path"]).read_bytes()))
        return five, six

    def test_distinct_impact_states_and_pending_review(self):
        five, six = self.build()
        impacts = {}
        for item in five["state"]["impacts"]:
            impacts.setdefault(item["system_id"], item)
        self.assertEqual(set(impacts), {f"AI-{n:03}" for n in range(1, 9)})
        self.assertEqual(impacts["AI-001"]["state"], "supported-no-impact")
        self.assertEqual(impacts["AI-004"]["state"], "supported-impact")
        self.assertEqual(impacts["AI-007"]["state"], "conflicting")
        self.assertEqual(impacts["AI-005"]["state"], "unresolved")
        self.assertEqual(impacts["AI-003"]["state"], "unresolved")
        provider = next(x for x in five["state"]["impacts"] if x["system_id"] == "AI-003" and x["rule_ref"] == "art111-4")
        self.assertEqual(provider["state"], "supported-no-impact")
        self.assertEqual(provider["reported_product_market_entry"], "2026-06-01")
        self.assertEqual(next(x for x in five["state"]["impacts"] if x["system_id"] == "AI-005" and x["rule_ref"] == "art111-4")["state"], "unresolved")
        self.assertEqual(len(six["state"]["proposed_actions"]), 8)
        self.assertTrue(all(x["status"] == "pending" for x in six["state"]["approval_requirements"]))
        self.assertTrue(all(x["delivery_status"] == "draft-not-sent" for x in six["state"]["review_requests"]))
        self.assertTrue(all(x["run_id"] == five["run_id"] for x in six["state"]["review_requests"]))
        self.assertEqual(next(x for x in five["state"]["policy_context"] if x["id"] == "policy-review-context")["activation_status"], "unverified")
        self.assertTrue(any(x["id"] == "request-policy-activation" for x in six["state"]["review_requests"]))

    def test_missing_binding_edition_blocks_formal_findings(self):
        for name in a.NAMES[2:4]:
            (self.snaps / (name + ".json")).unlink()
        path = self.snaps / "02-source-capture.json"
        two = json.loads(path.read_bytes())
        amend = next(x for x in two["state"]["sources"] if x["id"] == "source-amend")
        amend.update(retrieval_status="unavailable", local_reference=None, content_hash=None)
        path.write_bytes(c.encoded(two))
        self.assertEqual(c.reconcile(self.root), 1)
        five, six = self.build()
        self.assertEqual((five["status"], six["status"]), ("blocked", "blocked"))
        self.assertTrue(all(x["state"] == "unresolved" for x in five["state"]["impacts"]))
        self.assertTrue(six["state"]["proposed_actions"])

    def test_rejects_damaged_predecessor(self):
        path = self.snaps / "04-evidence-reconciliation.json"
        path.write_text("{}")
        with self.assertRaises(ValidationError):
            a.analyze(self.root)
        self.assertFalse((self.snaps / "05-impact-analysis.json").exists())


if __name__ == "__main__":
    unittest.main()
