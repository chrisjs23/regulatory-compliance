"""Establish the scope of Quillhaven's 26 August review."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen
from uuid import uuid4

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
LABELS = set("LAW OJ AMEND CONSOLIDATED TIME FAQ POLICY SYSTEMS EVIDENCE CALENDAR".split())
SCHEMA = ROOT / "snapshot.schema.json"


def now():
    return datetime.now(timezone.utc).isoformat()


def unique_keys(pairs):
    values = {}
    for key, value in pairs:
        if key in values:
            raise ValueError("duplicate route label")
        values[key] = value
    return values


def load_routes(path):
    routes = json.loads(path.read_text(), object_pairs_hook=unique_keys)
    if not isinstance(routes, dict) or set(routes) != LABELS:
        raise ValueError("route manifest must contain exactly the ten disclosed labels")
    for label, url in routes.items():
        parts = urlsplit(url) if isinstance(url, str) else None
        if not parts or parts.scheme != "https" or not parts.hostname or parts.username is not None:
            raise ValueError(f"{label} requires a credential-free HTTPS locator")
    return routes


def read_register(locator):
    parts = urlsplit(locator)
    match = re.fullmatch(r"/spreadsheets/d/([\w-]+)(?:/edit)?/?", parts.path)
    if parts.netloc != "docs.google.com" or not match or parts.query or parts.fragment:
        raise ValueError("SYSTEMS requires the disclosed Google Sheets workbook URL")
    export = f"https://docs.google.com/spreadsheets/d/{match[1]}/export?format=csv"
    attempt = dict(id="source-systems-scope", locator=locator, access_url=export,
                   retrieved_at=now(), content_type="unknown", content_hash=None,
                   local_reference=None, version_metadata=None, evidence_ids=[],
                   authority="operational-evidence", source_role="operational-record")
    try:
        with urlopen(export, timeout=20) as response:
            attempt["content_type"] = response.headers.get_content_type()
            if attempt["content_type"] != "text/csv":
                raise ValueError("expected the SYSTEMS CSV export")
            rows = csv.DictReader(io.StringIO(response.read().decode("utf-8-sig"), newline=""), strict=True)
            fields = rows.fieldnames or []
            for key in ("system_id", "record_version"):
                if fields.count(key) != 1:
                    raise ValueError(f"missing or ambiguous {key} column")
            records = {}
            for row_number, row in enumerate(rows, 2):
                key = row["system_id"]
                if not key or not key.strip() or key != key.strip() or key in records:
                    raise ValueError(f"missing or ambiguous system ID at row {row_number}")
                if not row["record_version"] or not row["record_version"].strip():
                    raise ValueError(f"missing record version at row {row_number}")
                records[key] = dict(row=row_number, system_id=key, record_version=row["record_version"])
            if not records:
                raise ValueError("empty SYSTEMS register")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        attempt.update(retrieval_status="unavailable", summary=f"SYSTEMS read failed ({type(exc).__name__})")
        return attempt, {}
    except (ValueError, csv.Error) as exc:
        attempt.update(retrieval_status="invalid", summary=str(exc))
        return attempt, {}
    attempt.update(retrieval_status="retrieved", summary="System identifiers and row revisions from the default tab.",
                   version_metadata={"by_system": {key: row["record_version"] for key, row in records.items()}})
    return attempt, records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--routes", required=True, type=Path)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--broad", action="store_true", help="requester selected all registered systems")
    scope.add_argument("--system-id", action="append", help="one requester-selected ID, repeat for a focused review")
    parser.add_argument("--output", type=Path, default=Path("deliverables"))
    parser.add_argument("--supersedes-run-id")
    parser.add_argument("--retry-reason")
    args = parser.parse_args(argv)
    if bool(args.supersedes_run_id) != bool(args.retry_reason):
        parser.error("provide both --supersedes-run-id and --retry-reason for a retry")
    requested = args.system_id or []
    if len(set(requested)) != len(requested) or any(not key or key.strip() != key for key in requested):
        parser.error("provide distinct, nonblank system IDs")
    try:
        routes = load_routes(args.routes)
        # Never replace a previous attempt, including an interrupted write.
        if args.output.exists() and any(args.output.iterdir()):
            parser.error("--output must be empty or new")
        attempt, records = read_register(routes["SYSTEMS"])
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    missing = sorted(set(requested) - records.keys())
    issue = None
    if attempt["retrieval_status"] != "retrieved":
        issue = attempt["summary"]
    elif missing:
        issue = "Requested IDs absent from SYSTEMS: " + ", ".join(missing)
    systems = requested or sorted(records) or ["All registered systems (IDs unresolved)"]
    evidence = [attempt["id"]]
    review_type = "broad-inventory" if args.broad else "focused-change"
    decision = dict(id="scope-selection", summary="Apply the requester's selected scope.",
                    evidence_ids=evidence, concern="Which systems should be evaluated?",
                    options=["broad-inventory", "focused-change"], chosen=review_type,
                    source_basis="Requester CLI selection and SYSTEMS register",
                    rationale="The requester defines the review population using registered IDs.",
                    tradeoffs=["Scope verification requires a current SYSTEMS read."],
                    downstream_effect="A register read failure or unknown ID blocks evaluation.")
    unresolved = []
    if issue:
        unresolved.append(dict(id="scope-gap", summary=issue, evidence_ids=evidence,
                               owner="Compliance and Operations Manager", resolution_need="Reconcile scope with requester and system owners, then retry."))
    state = dict(as_of="2026-08-26T00:00:00+01:00", date_precision="day", timezone="Europe/Dublin",
                 review_type=review_type, systems_in_scope=systems, audiences=["Legal", "Operations"],
                 approval_gates=["System owners verify facts", "Legal reviews interpretation and exceptions",
                                 "Operations approves policy activation, deadlines and incident closure"],
                 routes=routes, source_attempts=[attempt])
    snapshot = dict(schema_version="regulatory-compliance-stage-snapshot/2", snapshot_id=str(uuid4()),
                    run_id=str(uuid4()), stage="scope", sequence=1, created_at=now(),
                    status="blocked" if issue else "complete", predecessor=None, consumed_record_ids=[],
                    produced_record_ids=evidence + [decision["id"]] + [row["id"] for row in unresolved],
                    supersedes_run_id=args.supersedes_run_id, retry_reason=args.retry_reason,
                    state=state, unresolved=unresolved, decisions=[decision])
    if records:
        extract = (json.dumps(list(records.values()), indent=2) + "\n").encode()
        attempt.update(local_reference="sources/systems-scope.json",
                       content_hash="sha256:" + hashlib.sha256(extract).hexdigest())
    validator = Draft202012Validator(json.loads(SCHEMA.read_text()), format_checker=Draft202012Validator.FORMAT_CHECKER)
    validator.validate(snapshot)
    folder = args.output / "snapshots"
    folder.mkdir(parents=True, exist_ok=False)
    if records:
        path = args.output / attempt["local_reference"]
        path.parent.mkdir()
        path.write_bytes(extract)
    target = folder / "01-scope.json"
    target.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    print(f"Scope {snapshot['status']}: {target}")
    if issue:
        print(issue)
    return 1 if issue else 0


if __name__ == "__main__":
    raise SystemExit(main())
