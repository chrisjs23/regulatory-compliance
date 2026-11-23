"""Build authority/timing and evidence reconciliation for one captured run."""
import argparse
import json
from collections import Counter
from pathlib import Path
from uuid import uuid4

from jsonschema import Draft202012Validator
from capture import digest, encoded, read_selection
from run import SCHEMA, now

SKILL = Path(__file__).resolve().parents[1]
FILES = ["01-scope", "02-source-capture", "03-authority-and-timing", "04-evidence-reconciliation"]
VALIDATE = Draft202012Validator(json.loads(SCHEMA.read_bytes()), format_checker=Draft202012Validator.FORMAT_CHECKER).validate


def record(id, summary, evidence_ids, **values):
    return dict(id=id, summary=summary, evidence_ids=evidence_ids, **values)


def load_inputs(root):
    one, two = [json.loads((root / "snapshots" / (name + ".json")).read_bytes()) for name in FILES[:2]]
    for seq, doc in enumerate((one, two), 1):
        VALIDATE(doc)
        if doc["sequence"] != seq:
            raise ValueError("Wrong upstream snapshot sequence")
    first = "snapshots/01-scope.json"
    if (one["run_id"] != two["run_id"] or two["predecessor"] !=
            dict(path=first, snapshot_id=one["snapshot_id"], sha256=digest((root / first).read_bytes()))
            or set(two["consumed_record_ids"]) - set(one["produced_record_ids"])):
        raise ValueError("Broken upstream chain")
    sources, data = {}, {}
    for src in two["state"]["sources"]:
        key = src["id"]
        if key in sources:
            raise ValueError("Duplicate captured source ID")
        sources[key] = src
        if src["local_reference"]:
            p = (root / src["local_reference"]).resolve()
            if not p.is_relative_to((root / "sources").resolve()):
                raise ValueError("Capture path outside sources")
            b = p.read_bytes()
            if digest(b) != src["content_hash"]:
                raise ValueError(f"Damaged capture: {key}")
            data[key] = json.loads(b)
    return one, two, sources, data


def authority(sources, data):
    review = json.loads((SKILL / "references/reviewed-authority.json").read_bytes())
    state = dict(binding_rules=[], timing_rules=[], guidance_context=[], authority_blockers=[])
    current = {}
    for label, fingerprint in review["editions"].items():
        key = "source-" + label
        src = sources.get(key, {})
        formal = label in {"oj", "amend", "consolidated"}
        usable = src.get("retrieval_status") == "retrieved"
        if key in data and src.get("content_hash") == fingerprint and (usable or not formal and src.get("retrieval_status") == "unverified"):
            current[label] = {b["block"]: b["text"] for b in data[key]["blocks"]}
        elif formal:
            state["authority_blockers"].append(record("authority-gap-"+label,
                f"Required {label} edition unavailable, unsuitable or changed since passage review.",
                [key] if key in sources else [], owner="Legal", resolution_need="Verify the official edition and recheck passage locators."))
    for claim in review["claims"]:
        refs = claim["blocks"]
        advisory = claim["id"].endswith("-context")
        if set(refs) - current.keys() or (not advisory and state["authority_blockers"]):
            continue
        key = "guidance_context" if advisory else "binding_rules" if claim["id"].startswith("art50-") else "timing_rules"
        citations = [dict(source_id="source-"+label, block=n, text=current[label][n]) for label, numbers in refs.items() for n in numbers]
        state[key].append(record(claim["id"], claim["summary"], ["source-"+l for l in refs], passages=citations,
                                 **{k:v for k,v in claim.items() if k not in {"id","summary","blocks"}}))
    return state


def evidence(scope, sources, data, selections, interview):
    state = dict(system_facts=[], policy_controls=[], incident_evidence=[], calendar_proposals=[],
                 conflicts=[], evidence_gaps=[], supplemental_sources=[])
    gaps = state["evidence_gaps"]
    population = set(scope["state"]["systems_in_scope"])
    systems = {}
    for label, bucket, field in [("systems","system_facts","system_id"), ("evidence","incident_evidence","record_id"),
                                ("calendar","calendar_proposals","action_id")]:
        src = "source-" + label
        rows = data.get(src, {}).get("rows", [])
        counts = Counter(r["values"].get(field) for r in rows)
        for r in rows:
            v = r["values"]
            sid, key = v.get("system_id"), v.get(field)
            if not key or counts[key] != 1 or not sid:
                gaps.append(record(f"ambiguous-{label}-{r['row']}", "Missing or duplicate key; row cannot be joined.",
                                   [src], row=r["row"], resolution_need="Confirm source identities."))
                continue
            if sid not in population and not (label == "calendar" and sid == "ALL"):
                if scope["state"]["review_type"] == "broad-inventory":
                    gaps.append(record(f"orphan-{label}-{key}", "System missing from confirmed scope.", [src], values=v,row=r["row"]))
                continue
            rec = record(f"{label}-{key}",v.get("notes") or v.get("action") or v.get("system_name") or key,
                         [src], values=v, system_id=sid, row=r["row"], tab="default CSV export", owner=v.get("owner"))
            state[bucket].append(rec)
            if label == "systems":
                systems[sid] = rec
            if label == "evidence" and v.get("evidence_state") != "complete":
                conflict = v.get("evidence_state") == "conflicting"
                linked = systems.get(sid)
                state["conflicts" if conflict else "evidence_gaps"].append(record("issue-"+key, rec["summary"],
                    [src]+(["source-systems"] if linked else []), system_id=sid, owner=v.get("owner"),
                    reported_state=v.get("evidence_state"), related_records=[rec["id"]]+([linked["id"]] if linked else []),
                    resolution_need="Obtain current owner evidence and reconcile competing reports." if conflict else "Obtain missing or current proof from the record owner."))
    for sid in sorted(population-set(systems)):
        gaps.append(record("missing-"+sid, "No unambiguous captured register row.", ["source-systems"] if "source-systems" in sources else [], system_id=sid))
    for key in ("source-systems","source-evidence","source-calendar"):
        src = sources.get(key, {})
        if src.get("retrieval_status") != "retrieved":
            gaps.append(record("quality-"+key, "Operational extract unavailable or has unverified rows.", [key] if src else [],
                               issues=src.get("issues", []), resolution_need="Resolve affected rows before relying on the extract."))

    selected = [(key, val) for key,val in data.items() if sources[key]["label"] == "POLICY" and "passage" in val]
    for path in selections:
        val = read_selection(path, scope)
        fingerprint = digest(path.read_bytes())
        key = "supplement-" + fingerprint[7:23]
        if any(prev == val for _,prev in selected):
            continue
        selected.append((key,val))
        state["supplemental_sources"].append(record(key, "Operator-selected passage received after capture.",
            [], filename=path.name, sha256=fingerprint, selection=val))
    for key,val in selected:
        section = val["section"]
        bucket = "policy_controls" if section == "Internal AI-use policy" else "system_facts"
        state[bucket].append(record("passage-"+key,section,[key], section=section, text=val["passage"],
                                    system_id=section if section in population else None))
        passage = val["passage"]
        timing = ("The suppliers' product-release notices held by Operations report that the currently licensed "
                  "image-generation product used for AI-003 and audio/video-generation product used for AI-008 "
                  "were first offered commercially in the EU on 1 June 2026.")
        if section == "Product timing and evidence limits" and passage.startswith(timing):
            for sid in sorted({"AI-003","AI-008"} & population):
                state["system_facts"].append(record("market-entry-"+sid,
                    "Operations reports supplier product market entry; the original notices were not captured.",
                    [key], system_id=sid, reported_eu_market_entry="2026-06-01", owner="Operations"))
            if "AI-005" in population and "Current release and market-entry evidence for AI-005 remains unavailable." in passage:
                gaps.append(record("market-entry-gap-AI-005","Current release and market-entry evidence unavailable.",
                                   [key], system_id="AI-005",owner=systems.get("AI-005",{}).get("owner"),
                                   resolution_need="Obtain current supplier release and EU market-entry evidence."))
    policy = data.get("source-policy", {})
    for block in policy.get("blocks", []):
        state["policy_controls"].append(record("policy-block-"+str(block["block"]), "Captured internal policy paragraph.",
                                               ["source-policy"], **block))
    # The interview confirms this specific edition. Never infer dates for other versions.
    version_sources = [k for k,v in selected if v["passage"].strip()=="Policy version: AI-POL-2026-08-15"]
    if interview and version_sources:
        b = interview.read_bytes()
        lines = b.decode().splitlines()
        quote = "The effective date of our internal policy is August 15, 2026."
        hits = [i for i,t in enumerate(lines) if t.startswith(quote) and i >= 2 and lines[i-2].startswith("**Compliance and Operations Manager**")]
        if len(hits)==1 and any("which is AI-POL-2026-08-15" in t for t in lines):
            key = "interview-policy-date"
            state["supplemental_sources"].append(record(key, "Manager’s effective-date clarification.", [],
                            filename=interview.name, sha256=digest(b), line=hits[0]+1, text=lines[hits[0]]))
            state["policy_controls"].append(record("policy-effective", "Manager confirmed the effective date of the captured edition.",
                        [key,*version_sources],version="AI-POL-2026-08-15",effective_date="2026-08-15"))
    gaps.append(record("policy-coverage", "Retained policy evidence covers only selected passages. Other control requirements remain unresolved.",
                       [s for s in sources if sources[s]["label"]=="POLICY"], owner="Operations",
                       resolution_need="Supply versioned policy clauses for each remaining control."))
    return state


def reconcile(root, selections=(), interview=None):
    one, two, sources, data = load_inputs(root)
    out = root / "snapshots"
    if any((out / (name+".json")).exists() for name in FILES[2:]):
        raise ValueError("Stage C output exists; preserve this attempt before a retry.")
    third = authority(sources, data)
    inherited = two["unresolved"]
    blocked = two["status"] in {"blocked","failed"} or bool(third["authority_blockers"])
    previous = two
    for seq in (3,4):
        state = third if seq == 3 else evidence(one, sources, data, selections, interview)
        extra = state["authority_blockers"] if seq == 3 else state["evidence_gaps"] + state["conflicts"]
        unresolved = inherited + extra
        records = [r for collection in state.values() for r in collection]
        used = {key for r in records for key in r["evidence_ids"] if key in sources}
        used.update(r["id"] for r in inherited)
        if seq == 4:
            used.update(previous["produced_record_ids"])
            used.add("scope-selection")
        else:
            used.update(k for k in sources if sources[k]["label"] in {"OJ","AMEND","CONSOLIDATED","LAW","TIME","FAQ"})
        decision = record("authority-basis" if seq == 3 else "reconciliation-basis",
            "Use reviewed OJ text and amendment with a documentary cross-check." if seq == 3 else "Join system IDs while preserving each observation and proposal.",
            sorted(k for k in used if k in sources), concern="Limits of source evidence",
            options=["Use individual claims with evidence", "Defer the entire review"],
            chosen="Defer dependent conclusions where evidence is insufficient",
            source_basis="Current captured records and identified gaps",
            rationale="A missing authority prevents formal conclusions; missing operational records can be isolated.",
            tradeoffs=["Changed official text requires another passage review." if seq==3 else "Contradictory reports remain visible until a reviewer resolves them."],
            downstream_effect="Stage D must honor authority blockers, role distinctions and unresolved evidence.")
        prior = "snapshots/"+FILES[seq-2]+".json"
        doc = dict(schema_version=two["schema_version"],run_id=two["run_id"],snapshot_id=str(uuid4()),
                   sequence=seq, stage=FILES[seq-1][3:], created_at=now(), status="blocked" if blocked else "partial" if unresolved else "complete",
                   predecessor=dict(path=prior,snapshot_id=previous["snapshot_id"],sha256=digest((root/prior).read_bytes())),
                   consumed_record_ids=sorted(used), produced_record_ids=[r["id"] for r in records]+[decision["id"]],
                   state=state, decisions=[decision],unresolved=unresolved)
        VALIDATE(doc)
        with (out/(FILES[seq-1]+".json")).open("xb") as f:
            f.write(encoded(doc))
        previous, inherited = doc, unresolved
        print(FILES[seq-1],doc["status"])
    return 1 if previous["status"] != "complete" else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("deliverables"))
    parser.add_argument("--selection", type=Path, action="append", default=[])
    parser.add_argument("--interview", type=Path)
    args = parser.parse_args()
    raise SystemExit(reconcile(args.output,args.selection,args.interview))
