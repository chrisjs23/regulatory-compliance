"""Build impact analysis and draft approval requests from reconciled evidence."""
import argparse
import json
from pathlib import Path
from uuid import uuid4

from reconcile import FILES, VALIDATE, digest, encoded, now, record, load_inputs

NAMES = FILES + ["05-impact-analysis", "06-actions-and-approvals"]


def upstream(root):
    one, two, _, _ = load_inputs(root)
    docs = [one, two]
    available = set(one["produced_record_ids"] + two["produced_record_ids"])
    for seq in (3, 4):
        path = root / "snapshots" / (NAMES[seq - 1] + ".json")
        doc = json.loads(path.read_bytes())
        VALIDATE(doc)
        prior = root / "snapshots" / (NAMES[seq - 2] + ".json")
        if (doc["sequence"] != seq or doc["run_id"] != one["run_id"] or
                doc["predecessor"] != dict(path="snapshots/" + prior.name,
                                           snapshot_id=docs[-1]["snapshot_id"], sha256=digest(prior.read_bytes())) or
                set(doc["consumed_record_ids"]) - available):
            raise ValueError("Broken Stage C chain")
        available.update(doc["produced_record_ids"])
        docs.append(doc)
    return docs


def impacts(authority, reconciliation):
    rules = {r["id"] for bucket in ("binding_rules", "timing_rules") for r in authority["state"][bucket]}
    facts = reconciliation["state"]
    issues = facts["conflicts"] + facts["evidence_gaps"]
    by_system = {r["system_id"]: r for r in facts["system_facts"] if "values" in r}
    evidence = {}
    for item in facts["incident_evidence"]:
        evidence.setdefault(item["system_id"], []).append(item)
    market_entry = {r["system_id"]: r for r in facts["system_facts"] if r["id"].startswith("market-entry-")}
    state = dict(impacts=[], unaffected_items=[], conflicts=[], unresolved_items=[], policy_context=[])
    for control in facts["policy_controls"]:
        if control["id"] == "policy-effective":
            state["policy_context"].append(record("policy-review-context",
                "The captured policy edition was effective by the assigned review date; activation and full clause coverage remain unverified.",
                [control["id"]], version=control["version"], effective_date=control["effective_date"],
                activation_status="unverified", owner="Operations"))
    for sid, system in sorted(by_system.items()):
        values = system["values"]
        kind = values.get("output_type")
        rule = {"direct_interaction": "art50-1", "text": "art50-4-text",
                "synthetic_image": "art50-4-media", "synthetic_audio_video": "art50-4-media",
                "classification": "art50-3"}.get(kind)
        related = evidence.get(sid, [])
        conflicts = [x for x in issues if x.get("system_id") == sid and x in facts["conflicts"]]
        gaps = [x for x in issues if x.get("system_id") == sid and x in facts["evidence_gaps"]]
        ids = [system["id"], *[x["id"] for x in related], *[x["id"] for x in conflicts + gaps]]
        status, reason, need = "unresolved", "The captured facts do not establish this rule's applicability or compliance.", "Legal should confirm applicability; the system owner should verify current practice."
        if rule is None:
            reason = "The output type is not mapped to a reviewed Article 50 obligation."
            need = "Confirm the output type and applicable provision."
        elif rule not in rules or authority["state"]["authority_blockers"]:
            reason = "Required binding authority is unavailable or has changed."
            need = "Legal must verify the official edition before any dependent conclusion."
        elif kind == "direct_interaction":
            if conflicts:
                status, reason, need = "conflicting", "Owner and captured notice evidence disagree.", "System owner must reconcile the current first interaction display."
            elif values.get("current_notice") == "no" and any(x["values"].get("evidence_state") == "complete" for x in related):
                status, reason, need = "supported-impact", "The captured first interaction lacks an AI notice.", "Verify and implement a clear first interaction notice; Legal confirms responsibility."
            elif values.get("current_notice") == "yes" and values.get("evidence_status") == "complete" and not gaps:
                status, reason, need = "supported-no-impact", "Current notice and complete evidence show no identified notice remediation.", "System owner confirms the captured notice remains current."
            else:
                reason = "Current notice or proof is incomplete."
        elif (kind == "text" and values.get("exposed_group") == "staff" and
              any(x["values"].get("evidence_state") == "complete" for x in related)):
            status, reason, need = "supported-no-impact", "Captured use is restricted to internal staff summaries, not public-interest publication.", "Owner confirms the use has not expanded to public publication."
        elif kind == "text":
            reason = "The record does not establish public-interest publication or the editorial exception; recipient disclosure proof is also incomplete."
            need = "Legal confirms the rule basis and exception; owner supplies current recipient samples."
        elif kind in {"synthetic_image", "synthetic_audio_video"}:
            reason = "The record establishes generated media but not whether it constitutes a deep fake. A visible label is reported; machine-readable metadata is a separate question."
            need = "Legal assesses deep-fake applicability; owner verifies published labels and provenance separately."
        elif kind == "classification":
            reason = "The record does not establish biometric categorisation or emotion recognition; provider role and release evidence are stale."
            need = "Legal and the system owner confirm modality, role and current release evidence."
        if rule and rule in rules:
            ids.append(rule)
        if kind == "direct_interaction" and "art50-5" in rules:
            ids.append("art50-5")
        impact = record("impact-" + sid + "-" + (rule or "unmapped"), reason, list(dict.fromkeys(ids)),
                        state=status, system_id=sid, rule_ref=rule or "unmapped", owner=values.get("owner"),
                        reason=reason, resolution_need=need, source_version=values.get("record_version"),
                        provider_role=values.get("provider_role"), deployer_role=values.get("deployer_role"),
                        finding_scope="system transparency practice; Legal confirms statutory responsibility",
                        legal_interpretation_status="pending Legal review")
        state["impacts"].append(impact)
        if status == "supported-no-impact":
            state["unaffected_items"].append(record("unaffected-" + sid, reason, [impact["id"]],
                                                      system_id=sid, rule_ref=impact["rule_ref"]))
        elif status == "conflicting":
            state["conflicts"].append(record("impact-conflict-" + sid, reason, [impact["id"], *[x["id"] for x in conflicts]],
                                               system_id=sid, owner=values.get("owner"), resolution_need=need))
        elif status == "unresolved":
            state["unresolved_items"].append(record("impact-gap-" + sid, reason, [impact["id"], *[x["id"] for x in gaps]],
                                                      system_id=sid, owner=values.get("owner"), resolution_need=need))
        if kind in {"synthetic_image", "synthetic_audio_video"}:
            for provider_rule in ("art50-2", "art111-4"):
                supported = (provider_rule in rules and not authority["state"]["authority_blockers"] and
                             values.get("provider_role") == "no")
                entry = market_entry.get(sid)
                basis = [system["id"]] + ([provider_rule] if provider_rule in rules else
                                           [x["id"] for x in authority["state"]["authority_blockers"]])
                if entry:
                    basis.append(entry["id"])
                reason = ("The register says the Academy is a deployer, not this product's provider; the provider-only duty or transition does not establish an Academy deadline. Supplier compliance remains unverified."
                          if supported else "Provider role, product release or binding authority is not verified for this provider-only rule.")
                item = record("impact-" + sid + "-" + provider_rule, reason, basis,
                              state="supported-no-impact" if supported else "unresolved", system_id=sid,
                              rule_ref=provider_rule, owner=values.get("owner"), reason=reason,
                              finding_scope="Academy provider duty only; deployer disclosure assessed separately",
                              reported_product_market_entry=entry.get("reported_eu_market_entry") if entry else None,
                              source_version=values.get("record_version"),
                              resolution_need="Legal confirms role; Operations obtains supplier marking evidence.")
                state["impacts"].append(item)
                if supported:
                    state["unaffected_items"].append(record("unaffected-" + sid + "-" + provider_rule,
                        reason, [item["id"]], system_id=sid, rule_ref=provider_rule))
                else:
                    state["unresolved_items"].append(record("impact-gap-" + sid + "-" + provider_rule,
                        reason, [item["id"]], system_id=sid, owner=values.get("owner"),
                        resolution_need=item["resolution_need"]))
        if kind == "classification" and values.get("provider_role") == "unknown":
            reason = "The current release, market-entry date and provider role are unknown; qualifying generative output is not established."
            basis = [system["id"]] + (["art111-4"] if "art111-4" in rules else
                                      [x["id"] for x in authority["state"]["authority_blockers"]])
            item = record("impact-" + sid + "-art111-4", reason, basis,
                          state="unresolved", system_id=sid, rule_ref="art111-4", owner=values.get("owner"),
                          reason=reason, finding_scope="possible provider transition only",
                          resolution_need="Obtain current release and role evidence; Legal assesses eligibility.")
            state["impacts"].append(item)
            state["unresolved_items"].append(record("impact-gap-" + sid + "-art111-4", reason,
                [item["id"]], system_id=sid, owner=values.get("owner"), resolution_need=item["resolution_need"]))
    return state


def actions(scope, authority, reconciliation, analysis):
    state = dict(proposed_actions=[], approval_requirements=[], escalations=[], review_requests=[])
    impacts_by_system = {}
    for item in analysis["impacts"]:
        impacts_by_system.setdefault(item["system_id"], item)
    run_id = scope["run_id"]
    for row in reconciliation["state"].get("calendar_proposals", []):
        v = row["values"]
        sid, action_id = v["system_id"], v["action_id"]
        impact = impacts_by_system.get(sid)
        basis = [row["id"]] + ([impact["id"]] if impact else [])
        reviewer = "Legal" if v.get("approval_required") == "legal" else "Operations"
        proposed = record("action-" + action_id, v["action"], basis,
                          action_id=action_id, system_id=sid, owner=v.get("owner"),
                          proposed_due_date=v.get("due_date"), source_version=v.get("source_version"),
                          approval_status="pending", source_status=v.get("status"),
                          rationale="Source calendar proposal only; no approved deadline or activation was supplied.",
                          linked_impact_id=impact["id"] if impact else None)
        state["proposed_actions"].append(proposed)
        state["approval_requirements"].append(record("approval-" + action_id,
            "Review proposed action and date before activation.", [proposed["id"]], status="pending",
            action_id=action_id, reviewer=reviewer, subject=proposed["id"],
            resolution_need="Record a verified decision against the reviewed draft and source version."))
        state["review_requests"].append(record("request-" + action_id,
            "Draft request for action and date review.", [proposed["id"], *basis],
            subject=proposed["id"], system_id=sid, action_id=action_id, run_id=run_id,
            source_version=v.get("source_version"), reviewer=reviewer,
            question="Approve or amend this proposed action and date after reviewing its evidence?",
            delivery_status="draft-not-sent"))
    for impact in analysis["impacts"]:
        if impact["state"] not in {"conflicting", "unresolved", "supported-impact"}:
            continue
        sid = impact["system_id"]
        reviewer = "Legal" if impact["state"] == "unresolved" else "Operations"
        state["escalations"].append(record("escalation-" + impact["id"], impact["reason"], [impact["id"]],
                                           system_id=sid, owner=impact.get("owner"), reviewer=reviewer,
                                           resolution_need=impact["resolution_need"]))
        state["review_requests"].append(record("request-" + impact["id"],
            "Draft request to resolve impact basis.", [impact["id"]], subject=impact["id"],
            system_id=sid, run_id=run_id, source_version=impact.get("source_version"),
            reviewer=reviewer, question=impact["resolution_need"], delivery_status="draft-not-sent"))
    for context in analysis["policy_context"]:
        state["escalations"].append(record("escalation-policy-activation",
            "Policy activation and remaining control clauses are not verified.", [context["id"]],
            owner="Operations", reviewer="Operations",
            resolution_need="Confirm activation and provide the remaining versioned policy clauses."))
        state["review_requests"].append(record("request-policy-activation",
            "Draft request to confirm policy activation and coverage.", [context["id"]],
            subject=context["id"], run_id=run_id, source_version=context["version"],
            reviewer="Operations", question="Was this edition activated for the review date, and can the remaining clauses be supplied?",
            delivery_status="draft-not-sent"))
    return state


def analyze(root):
    docs = upstream(root)
    out = root / "snapshots"
    if any((out / (name + ".json")).exists() for name in NAMES[4:]):
        raise ValueError("Stage D output exists; preserve this attempt before a retry.")
    scope, _, authority, reconciliation = docs
    blocked = bool(authority["state"]["authority_blockers"]) or any(x["status"] == "blocked" for x in docs)
    previous = reconciliation
    for seq in (5, 6):
        state = impacts(authority, reconciliation) if seq == 5 else actions(scope, authority, reconciliation, previous["state"])
        extra = state["conflicts"] + state["unresolved_items"] if seq == 5 else state["escalations"]
        unresolved = previous["unresolved"] + extra
        records = [r for group in state.values() for r in group]
        available = {i for doc in docs for i in doc["produced_record_ids"]}
        used = sorted({i for r in records for i in r["evidence_ids"] if i in available})
        if not used:
            used = [reconciliation["produced_record_ids"][0]]
        decision = record("impact-basis" if seq == 5 else "action-basis",
            "Separate supported observations from conflicts and unresolved applicability." if seq == 5 else
            "Keep calendar dates and review requests as draft proposals.", used,
            concern="Legal and operational decisions require verified evidence and human review.",
            options=["Record bounded provisional findings", "Defer every finding"],
            chosen="Preserve supported findings and mark unresolved issues and approvals pending.",
            source_basis="Captured authority, system records, evidence and source calendar proposals.",
            rationale="Unavailable proof or approval cannot establish compliance or an activated deadline.",
            tradeoffs=["The draft retains open questions until owners and reviewers respond."],
            downstream_effect="Stage E must render the same states and keep dates tentative.")
        prior = "snapshots/" + NAMES[seq - 2] + ".json"
        doc = dict(schema_version=scope["schema_version"], run_id=scope["run_id"], snapshot_id=str(uuid4()),
                   sequence=seq, stage=NAMES[seq - 1][3:], created_at=now(),
                   status="blocked" if blocked else "partial" if unresolved else "complete",
                   predecessor=dict(path=prior, snapshot_id=previous["snapshot_id"], sha256=digest((root / prior).read_bytes())),
                   consumed_record_ids=used, produced_record_ids=[r["id"] for r in records] + [decision["id"]],
                   state=state, unresolved=unresolved, decisions=[decision])
        VALIDATE(doc)
        with (out / (NAMES[seq - 1] + ".json")).open("xb") as file:
            file.write(encoded(doc))
        docs.append(doc)
        previous = doc
        print(NAMES[seq - 1], doc["status"])
    return 1 if previous["status"] != "complete" else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("deliverables"))
    args = parser.parse_args()
    raise SystemExit(analyze(args.output))
