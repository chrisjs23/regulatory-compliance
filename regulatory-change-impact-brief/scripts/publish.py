"""Render review drafts and bind their verified bytes in snapshot 07."""
import argparse
import csv
from datetime import date, datetime, timedelta, timezone
from io import StringIO
import json
from pathlib import Path
from uuid import uuid4

from icalendar import Calendar, Event
from jsonschema.exceptions import ValidationError
from analyze import NAMES, upstream
from reconcile import VALIDATE, digest, encoded, now, record

FILES = {"register": "impact-register.csv", "brief": "compliance-brief.md", "calendar": "action-calendar.ics"}
HEADER = ["impact_id", "system_id", "rule_ref", "state", "evidence_ids", "reason", "owner",
          "proposed_action", "proposed_due_date", "approval_status", "record_type", "resolution_need"]


def inputs(root):
    docs = upstream(root)
    available = {i for doc in docs for i in doc["produced_record_ids"]}
    for seq in (5, 6):
        path = root / "snapshots" / (NAMES[seq - 1] + ".json")
        doc = json.loads(path.read_bytes())
        VALIDATE(doc)
        prior = root / "snapshots" / (NAMES[seq - 2] + ".json")
        if (doc["sequence"] != seq or doc["run_id"] != docs[0]["run_id"] or
                doc["predecessor"] != dict(path="snapshots/" + prior.name,
                                           snapshot_id=docs[-1]["snapshot_id"], sha256=digest(prior.read_bytes())) or
                set(doc["consumed_record_ids"]) - available):
            raise ValueError("Broken Stage D chain")
        available.update(doc["produced_record_ids"])
        docs.append(doc)
    if len({doc["snapshot_id"] for doc in docs}) != len(docs):
        raise ValueError("Duplicate snapshot ID")
    return docs


def register_rows(docs):
    five, six = docs[4:6]
    actions = six["state"]["proposed_actions"]
    first_action = {}
    for action in actions:
        first_action.setdefault(action["system_id"], action)
    rows = []
    for impact in five["state"]["impacts"]:
        action = first_action.get(impact["system_id"])
        rows.append(dict(impact_id=impact["id"], system_id=impact["system_id"], rule_ref=impact["rule_ref"],
                         state=impact["state"], evidence_ids=";".join(impact["evidence_ids"]),
                         reason=impact["reason"], owner=impact.get("owner") or "",
                         proposed_action=action["id"] + ": " + action["summary"] if action else "",
                         proposed_due_date=action.get("proposed_due_date") or "" if action else "",
                         approval_status=action["approval_status"] if action else "not-required",
                         record_type="impact", resolution_need=impact.get("resolution_need") or ""))
    # Preserve distinct source gaps/conflicts; derived impact and escalation records are represented above.
    for issue in six["unresolved"]:
        if issue["id"].startswith(("impact-", "escalation-")):
            continue
        rows.append(dict(impact_id="open-" + issue["id"], system_id=issue.get("system_id") or "",
                         rule_ref="", state="conflicting" if issue["id"] in
                         {r["id"] for r in docs[3]["state"]["conflicts"]} else "unresolved",
                         evidence_ids=";".join(issue["evidence_ids"]), reason=issue["summary"],
                         owner=issue.get("owner") or "", proposed_action="", proposed_due_date="",
                         approval_status="pending", record_type="source-issue",
                         resolution_need=issue.get("resolution_need") or ""))
    for action in actions:
        rows.append(dict(impact_id="proposal-" + action["action_id"], system_id=action["system_id"],
                         rule_ref="", state="unresolved", evidence_ids=";".join(action["evidence_ids"]),
                         reason="Source calendar proposal; approval and deadline are pending.",
                         owner=action.get("owner") or "", proposed_action=action["id"] + ": " + action["summary"],
                         proposed_due_date=action.get("proposed_due_date") or "",
                         approval_status=action["approval_status"], record_type="action-proposal",
                         resolution_need="Obtain a verified reviewer decision."))
    if len({r["impact_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate register ID")
    return rows


def csv_bytes(rows):
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=HEADER, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def brief_bytes(docs, rows):
    scope, capture, authority, reconciliation, five, six = docs
    state = six["status"]
    as_of = scope["state"]["as_of"][:10]
    lines = ["# Regulatory change impact brief — draft", "", f"Run ID: `{scope['run_id']}`  ",
             f"As of: {as_of} (Europe/Dublin calendar date)  ", "Recipients: Legal and Operations  ",
             f"Review state: **{state}**. No legal approval, policy activation, approved deadline or incident closure is asserted.", "",
             "The IDs below resolve through snapshots 01–06 and retained extracts in `sources/`. This is a local review draft; requests are unsent.", "",
             "## Source quality and limits", ""]
    for source in capture["state"]["sources"]:
        if source["retrieval_status"] != "retrieved":
            lines.append(f"- `{source['id']}` ({source['label']}): {source['retrieval_status']}; {source['summary']}")
    for blocker in authority["state"]["authority_blockers"]:
        lines.append(f"- `{blocker['id']}`: binding authority blocker; {blocker['summary']}")
    lines += ["- TIME is guidance only while its revision for the review date is unverified. POLICY browser selections cover only identified passages. The manager confirmed the captured policy edition's effective date; activation remains unverified.",
              "- Supplier market-entry dates for AI-003 and AI-008 are owner-reported product dates, not proof of supplier compliance or Academy provider status. AI-005 lacks current release evidence.", "",
              "## Impact register findings", ""]
    for item in five["state"]["impacts"]:
        lines.append(f"- `{item['id']}` · {item['system_id']} · `{item['rule_ref']}` · **{item['state']}**: {item['reason']} Basis: {', '.join('`'+x+'`' for x in item['evidence_ids'])}. Next: {item['resolution_need']}")
    lines += ["", "## Conflicts and unresolved evidence", ""]
    for row in rows:
        if row["record_type"] == "source-issue":
            lines.append(f"- `{row['impact_id']}` · {row['system_id'] or 'source-wide'} · {row['state']}: {row['reason'].rstrip('.')}. "
                         f"Owner: {row['owner'] or 'unassigned'}. Next: {(row['resolution_need'] or 'confirm evidence').rstrip('.')}.")
    lines += ["", "## Proposed actions and dates", ""]
    blocked = six["status"] in {"blocked", "failed"}
    for item in six["state"]["proposed_actions"]:
        due = item.get("proposed_due_date") or "undated"
        event = "omitted from calendar: upstream review blocked or failed" if blocked else (
            "omitted from calendar: no proposed date" if due == "undated" else "tentative calendar entry")
        lines.append(f"- `{item['id']}` · {item['system_id']} · {item['summary']} · owner {item.get('owner') or 'unassigned'} · proposed {due} · approval **{item['approval_status']}** · {event}. Basis: {', '.join('`'+x+'`' for x in item['evidence_ids'])}.")
    lines += ["", "## Decisions requested", "",
              "Review request bindings are in `snapshots/07-publication-validation.json` and identify this brief by exact path and hash. No request has been sent.", ""]
    for req in six["state"]["review_requests"]:
        lines.append(f"- `{req['id']}` · {req['reviewer']} · subject `{req['subject']}` · source version `{req.get('source_version') or 'unverified'}` · evidence {', '.join('`'+x+'`' for x in req['evidence_ids'])}: {req['question']}")
    lines += ["", "Legal retains interpretation and exception decisions. Operations retains policy activation, deadline approval and incident closure. System owners verify facts.", ""]
    return "\n".join(lines).encode("utf-8")


def calendar_bytes(docs):
    six = docs[5]
    cal = Calendar()
    cal.add("version", "2.0")
    cal.add("prodid", "-//Quillhaven Academy//Regulatory Change Review//EN")
    if six["status"] not in {"blocked", "failed"}:
        stamp = datetime.now(timezone.utc)
        for item in six["state"]["proposed_actions"]:
            value = item.get("proposed_due_date")
            if not value:
                continue
            day = date.fromisoformat(value)
            event = Event()
            event.add("uid", item["action_id"].lower() + "@quillhaven.invalid")
            event.add("dtstamp", stamp)
            event.add("dtstart", day)
            event.add("dtend", day + timedelta(days=1))
            event.add("summary", item["summary"])
            event.add("description", "Action " + item["action_id"] + "; system " + item["system_id"] +
                      "; responsible role " + (item.get("owner") or "unassigned") +
                      "; basis " + ", ".join(item["evidence_ids"]) +
                      "; approval " + item["approval_status"] + "; local draft proposal")
            event.add("status", "TENTATIVE")
            cal.add_component(event)
    return cal.to_ical()


def check_files(root, docs, rows):
    problems = []
    register_path = root / FILES["register"]
    with register_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        parsed = list(reader)
        if reader.fieldnames != HEADER or parsed != rows:
            problems.append("Register rows or columns differ from Stage D records")
    brief = (root / FILES["brief"]).read_text(encoding="utf-8")
    needed = [docs[0]["run_id"], docs[0]["state"]["as_of"][:10],
              "snapshots/07-publication-validation.json", "Legal and Operations"]
    needed += [x["id"] for x in docs[4]["state"]["impacts"]]
    needed += [x["id"] for x in docs[5]["state"]["proposed_actions"]]
    needed += [x["id"] for x in docs[5]["state"]["review_requests"]]
    if any(x not in brief for x in needed):
        problems.append("Brief is missing a run, finding, action or review reference")
    cal = Calendar.from_ical((root / FILES["calendar"]).read_bytes())
    if str(cal.get("VERSION")) != "2.0" or not cal.get("PRODID"):
        problems.append("Calendar lacks the required version or product identifier")
    events = list(cal.walk("VEVENT"))
    actions = docs[5]["state"]["proposed_actions"]
    dated = [] if docs[5]["status"] in {"blocked", "failed"} else [x for x in actions if x.get("proposed_due_date")]
    expected = {x["action_id"].lower() + "@quillhaven.invalid": x for x in dated}
    if len(events) != len(expected):
        problems.append("Calendar event count differs from dated proposals")
    for event in events:
        uid = str(event.get("UID"))
        action = expected.get(uid)
        if not action or str(event.get("STATUS")) != "TENTATIVE" or not event.get("DTSTAMP") or \
                event.decoded("DTSTART") != date.fromisoformat(action["proposed_due_date"]) or \
                event.decoded("DTEND") != date.fromisoformat(action["proposed_due_date"]) + timedelta(days=1):
            problems.append("Calendar event identity, status or date differs from proposal")
            continue
        stamp = event.decoded("DTSTAMP")
        if not isinstance(stamp, datetime) or stamp.utcoffset() != timedelta(0) or str(event.get("SUMMARY")) != action["summary"]:
            problems.append("Calendar timestamp or summary differs from proposal")
        description = str(event.get("DESCRIPTION"))
        if any(x not in description for x in [action["action_id"], action["system_id"],
                                               action.get("owner") or "unassigned", action["approval_status"],
                                               *action["evidence_ids"]]):
            problems.append("Calendar description lacks action, system, role or approval")
    return problems


def verify_bundle(root):
    try:
        docs = inputs(root)
        path = root / "snapshots/07-publication-validation.json"
        doc = json.loads(path.read_bytes())
        VALIDATE(doc)
        prior = root / "snapshots/06-actions-and-approvals.json"
        if doc["run_id"] != docs[0]["run_id"] or doc["predecessor"] != dict(
                path="snapshots/06-actions-and-approvals.json", snapshot_id=docs[5]["snapshot_id"],
                sha256=digest(prior.read_bytes())):
            return False
        upstream_ids = {i for upstream_doc in docs for i in upstream_doc["produced_record_ids"]}
        if (doc["sequence"] != 7 or set(doc["consumed_record_ids"]) - upstream_ids or
                len(doc["produced_record_ids"]) != len(set(doc["produced_record_ids"])) or
                doc["snapshot_id"] in {x["snapshot_id"] for x in docs}):
            return False
        artifacts = {x["id"]: x for x in doc["state"]["artifacts"]}
        if set(artifacts) != {"artifact-register", "artifact-brief", "artifact-calendar"}:
            return False
        for label, name in FILES.items():
            item = artifacts["artifact-" + label]
            if item["path"] != name or digest((root / name).read_bytes()) != item["sha256"]:
                return False
        if check_files(root, docs, register_rows(docs)):
            return False
        expected_publication = docs[5]["status"] if docs[5]["status"] in {"blocked", "failed"} else "validated"
        if (doc["status"] != docs[5]["status"] or doc["state"]["publication_status"] != expected_publication or
                any(x["validation_status"] != "valid" for x in artifacts.values()) or
                any(x.get("outcome") != "passed" for x in doc["state"]["validation_checks"])):
            return False
        requests = {x["id"] for x in docs[5]["state"]["review_requests"]}
        bindings = doc["state"]["review_request_bindings"]
        if {x["request_id"] for x in bindings} != requests or len(bindings) != len(requests):
            return False
        if any(x["reviewed_path"] != FILES["brief"] or
               x["reviewed_sha256"] != artifacts["artifact-brief"]["sha256"] for x in bindings):
            return False
        return True
    except (ValueError, KeyError, OSError, TypeError, ValidationError):
        return False


def publish(root):
    docs = inputs(root)
    if (root / "snapshots/07-publication-validation.json").exists() or any((root / name).exists() for name in FILES.values()):
        raise ValueError("Stage E output exists; preserve the prior draft before a retry.")
    rows = register_rows(docs)
    payloads = dict(register=csv_bytes(rows), brief=brief_bytes(docs, rows), calendar=calendar_bytes(docs))
    for label, name in FILES.items():
        with (root / name).open("xb") as file:
            file.write(payloads[label])
    problems = check_files(root, docs, rows)
    artifacts = [dict(id="artifact-" + label, path=name, sha256=digest((root / name).read_bytes()),
                      validation_status="valid" if not problems else "invalid") for label, name in FILES.items()]
    checks = [record("check-cross-file", "Parsed CSV, brief references and RFC 5545 calendar agree with Stage D." if not problems else
                     "; ".join(problems), [x["id"] for x in artifacts], outcome="passed" if not problems else "failed")]
    brief_hash = next(x["sha256"] for x in artifacts if x["id"] == "artifact-brief")
    bindings = [record("binding-" + req["id"], "Request binds to the exact reviewed brief.",
                       [req["id"], "artifact-brief"], request_id=req["id"], reviewer=req["reviewer"],
                       run_id=req["run_id"], source_version=req.get("source_version"),
                       reviewed_path=FILES["brief"], reviewed_sha256=brief_hash,
                       delivery_status="draft-not-sent") for req in docs[5]["state"]["review_requests"]]
    blocked = docs[5]["status"] == "blocked"
    failed = docs[5]["status"] == "failed"
    publication_status = "failed" if problems or failed else "blocked" if blocked else "validated"
    state = dict(artifacts=artifacts, validation_checks=checks, publication_status=publication_status,
                 review_request_bindings=bindings)
    decision = record("publication-basis", "Validate only the local review draft; retain all pending decisions.",
        [x["id"] for x in artifacts], concern="Cross-file agreement and review binding",
        options=["Validate bounded draft", "Claim final approval"], chosen="Validate bounded draft only",
        source_basis="Stages 05–06 and reread final artifact bytes",
        rationale="File hashes and parsed content establish draft consistency, not human approval.",
        tradeoffs=["Outstanding authority or evidence keeps the run partial or blocked."],
        downstream_effect="Stage F must archive and revalidate on any retry.")
    prior = "snapshots/06-actions-and-approvals.json"
    doc = dict(schema_version=docs[0]["schema_version"], run_id=docs[0]["run_id"], snapshot_id=str(uuid4()),
               sequence=7, stage="publication-validation", created_at=now(),
               status="failed" if problems or failed else "blocked" if blocked else docs[5]["status"],
               predecessor=dict(path=prior, snapshot_id=docs[5]["snapshot_id"], sha256=digest((root / prior).read_bytes())),
               consumed_record_ids=sorted({req["id"] for req in docs[5]["state"]["review_requests"]} |
                                          {x["id"] for x in docs[5]["state"]["proposed_actions"]} |
                                          {x["id"] for x in docs[4]["state"]["impacts"]}),
               produced_record_ids=[x["id"] for x in artifacts + checks + bindings] + [decision["id"]],
               state=state, unresolved=docs[5]["unresolved"], decisions=[decision])
    VALIDATE(doc)
    with (root / "snapshots/07-publication-validation.json").open("xb") as file:
        file.write(encoded(doc))
    print("07-publication-validation", doc["status"], publication_status)
    return 1 if doc["status"] != "complete" else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("deliverables"))
    parser.add_argument("--verify", action="store_true", help="Verify existing final artifact hashes")
    args = parser.parse_args()
    raise SystemExit(0 if verify_bundle(args.output) else 1) if args.verify else SystemExit(publish(args.output))
