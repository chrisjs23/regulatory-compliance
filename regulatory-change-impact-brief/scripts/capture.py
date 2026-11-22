"""Write snapshot 02 by extending a saved scope snapshot exactly once."""
import argparse
import csv
from datetime import date, datetime
from hashlib import sha256
from html.parser import HTMLParser
from http.client import HTTPException
import io
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import urlopen
from uuid import uuid4

from jsonschema import Draft202012Validator
from run import LABELS, SCHEMA, now

FIELDS = {
    "SYSTEMS": "system_id system_name use_case owner provider_role deployer_role exposed_group output_type current_notice human_review evidence_status evidence_updated_at record_version",
    "EVIDENCE": "record_id system_id record_type reported_at owner status evidence_ref evidence_state notes",
    "CALENDAR": "action_id system_id action owner due_date status approval_required source_version",
}
TERMS = json.loads((Path(__file__).resolve().parents[1] / "references/extract-values.json").read_text())
HOSTS = {"LAW": "ai-act-service-desk.ec.europa.eu", "TIME": "ai-act-service-desk.ec.europa.eu",
         "FAQ": "digital-strategy.ec.europa.eu", **dict.fromkeys(("OJ", "AMEND", "CONSOLIDATED"), "eur-lex.europa.eu")}
BINDING = {"OJ", "AMEND"}
LIMIT = 20 * 1024 * 1024


def digest(body):
    return "sha256:" + sha256(body).hexdigest()


def encoded(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()


class Page(HTMLParser):
    """Extract visible blocks and document title, omitting navigation and scripts."""
    skip = {"script", "style", "nav", "footer", "noscript", "svg"}
    blocks = {"br", "div", "li", "tr", "p", "h1", "h2", "h3", "h4", "title", "section"}

    def __init__(self, text):
        super().__init__()
        self.hidden = 0
        self.in_title = False
        self.title = ""
        self.parts = []
        self.lines = []
        self.feed(text)
        self.close()
        self.flush()

    def flush(self):
        line = " ".join("".join(self.parts).split())
        if line:
            self.lines.append(line)
        self.parts.clear()

    def handle_starttag(self, tag, attrs):
        if tag in self.skip:
            self.hidden += 1
        if tag in self.blocks:
            self.flush()
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in self.skip:
            self.hidden = max(0, self.hidden - 1)
        if tag in self.blocks:
            self.flush()
        if tag == "title":
            self.in_title = False

    def handle_data(self, text):
        if not self.hidden:
            self.parts.append(text)
            if self.in_title:
                self.title += text


def allowed(field, value):
    if value is None:
        return False
    if field in TERMS:
        return value in TERMS[field]
    if field in {"reported_at", "due_date", "evidence_updated_at"}:
        if not value and field == "due_date":
            return True
        try:
            return date.fromisoformat(value).isoformat() == value
        except ValueError:
            return False
    if field in {"source_version", "record_version"}:
        return bool(re.fullmatch(r"(?:register|calendar)-\d{4}-\d\d-\d\d", value)
                    and allowed("reported_at", value.split("-", 1)[1]))
    prefix = {"system_id": "AI", "record_id": "REC", "action_id": "ACT"}[field]
    return bool(re.fullmatch(prefix + r"-\d+", value)) or (field == "system_id" and value == "ALL")


def sheet_extract(label, text, record, as_of):
    fields = FIELDS[label].split()
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    headers = reader.fieldnames or []
    if any(headers.count(field) != 1 for field in fields):
        raise ValueError("Missing or ambiguous required sheet headers.")
    rows, issues, versions, seen = [], [], set(), set()
    for number, row in enumerate(reader, 2):
        values = {key: row[key] for key in fields if allowed(key, row[key])}
        omitted = sorted(set(fields) - values.keys())
        if omitted:
            issues.append(f"Row {number}: omitted fields pending validation or privacy review: {', '.join(omitted)}.")
        key = values.get(fields[0])
        if key in seen or key is None:
            issues.append(f"Row {number}: ambiguous or unavailable record identity.")
        seen.add(key)
        if None in row or any(x is None for x in row.values()):
            issues.append(f"Row {number}: value count differs from header.")
        rows.append({"row": number, "values": values})
        for field in ("source_version", "record_version", "reported_at", "evidence_updated_at"):
            if values.get(field):
                versions.add(values[field])
                if values[field][-10:] > as_of:
                    issues.append(f"Row {number}: {field} postdates the review day.")
    if not rows:
        raise ValueError("Register has no records.")
    record.update(version_metadata={"row_revisions_or_dates": sorted(versions)},
                  retrieval_status="unverified" if issues else "retrieved",
                  summary=f"Captured {len(rows)} selected rows from {label}.", issues=issues)
    return {"label": label, "tab": "default CSV export", "rows": rows}


def document_extract(label, text, record, as_of):
    page = Page(text)
    body = " ".join(page.lines)
    title = " ".join(page.title.split())
    signatures = {
        "LAW": ("article 50", "transparency obligations", "providers"),
        "TIME": ("timeline", "ai act", "2026"),
        "FAQ": ("transparency obligations", "article 50", "providers"),
        "OJ": ("2024/1689", "article 50", "article 113"),
        "AMEND": ("2026/1744", "2024/1689", "article 1"),
        "CONSOLIDATED": ("2024/1689", "27.07.2026", "article 50"),
        "POLICY": ("internal polic", "quillhaven"),
    }
    if not all(term in body.lower() for term in signatures[label]):
        raise ValueError("Returned page lacks the expected document identity or substantive text.")
    if label in ("LAW", "TIME", "FAQ") and not all(term in title.lower() for term in signatures[label][:2]):
        raise ValueError("Unexpected document title.")
    editions = {"OJ": ("2024/1689", "32024r1689"), "AMEND": ("2026/1744", "32026r1744"),
                "CONSOLIDATED": ("02024r1689-20260727",)}
    if label in editions and not any(marker in title.lower() for marker in editions[label]):
        raise ValueError("EUR-Lex title does not identify the requested edition.")
    if label == "POLICY":
        paragraphs = [dict(block=i, text=s) for i, s in enumerate(page.lines, 1) if s in TERMS["policy_paragraphs"]]
        # Only copy a stated revision from a paragraph reviewed for retention.
        versions = [m[1] for p in paragraphs for m in [re.search(r"(?i)version\s+([\w.-]+)", p["text"])] if m]
        record.update(retrieval_status="unverified", version_metadata={"stated_versions": versions},
                      summary="Policy identity detected; verify version and permitted control extracts.")
        if paragraphs and versions:
            effective = [m[1] for p in paragraphs for m in [re.search(r"(?i)effective\s+(\d{4}-\d{2}-\d{2})", p["text"])] if m]
            if effective and all(allowed("reported_at", d) and d <= as_of for d in effective):
                record.update(retrieval_status="retrieved", summary="Policy extracts with stated revision and effective date.")

        return {"blocks": paragraphs} if paragraphs else None
    # Preserve blocks, including currency notices, for pinpoint references at stage 03.
    pattern = r"(?:last updat(?:e|ed)|as at)\s*:?\s*(\d{1,2} [A-Za-z]+ \d{4})"
    dates = re.findall(pattern, body, re.I)
    record["version_metadata"] = {"title": title, "stated_dates": dates}
    if label in ("OJ", "AMEND", "CONSOLIDATED"):
        record["version_metadata"]["edition"] = {"OJ": "2024/1689 OJ", "AMEND": "2026/1744 OJ",
                                                "CONSOLIDATED": "02024R1689-20260727"}[label]
    status, note = "retrieved", "Document identified; claim applicability requires stage 03 review."
    if label in ("LAW", "TIME", "FAQ"):
        parsed = []
        for value in dates:
            try:
                parsed.append(datetime.strptime(value, "%d %B %Y").date().isoformat())
            except ValueError:
                pass
        if not parsed or max(parsed) > as_of:
            status, note = "unverified", "Could not establish a page version suitable for the review day."
        elif label == "LAW" and "disclaimer" in body.lower():
            note = "Service Desk text carries a currency disclaimer; check official editions at stage 03."
    record.update(retrieval_status=status, summary=note)
    return {"title": title, "blocks": [dict(block=i, text=s) for i, s in enumerate(page.lines, 1)]}


def fetch(label, locator, folder, as_of):
    sheet = label in FIELDS
    role, authority = ("operational-record", "operational-evidence") if sheet else ("official-guidance", "advisory")
    if label in BINDING:
        role, authority = "binding-regulation", "binding"
    elif label == "POLICY":
        role, authority = "internal-policy", "internal-control"
    elif label == "CONSOLIDATED":
        role, authority = "other", "advisory"
    rec = dict(id="source-" + label.lower(), label=label, locator=locator, source_role=role, authority=authority,
               evidence_ids=[], retrieved_at=now(), version_metadata=None, content_type="unknown",
               content_hash=None, local_reference=None)
    try:
        u = urlsplit(locator)
        if u.scheme != "https" or not u.hostname or u.username is not None:
            raise ValueError("Invalid HTTPS route.")
        if sheet:
            match = re.fullmatch(r"/spreadsheets/d/([\w-]+)(?:/edit)?/?", u.path)
            if u.netloc != "docs.google.com" or not match or u.query or u.fragment:
                raise ValueError("Expected disclosed Google Sheets workbook route.")
            url = f"https://docs.google.com/spreadsheets/d/{match[1]}/export?format=csv"
        else:
            if label == "POLICY":
                if not u.hostname.endswith(".notion.site"):
                    raise ValueError("Unexpected policy host.")
            elif u.hostname != HOSTS[label]:
                raise ValueError("Unexpected official source host.")
            url = locator
        rec["access_url"] = url
        with urlopen(url, timeout=25) as response:
            final = urlsplit(response.geturl())
            rec.update(http_status=response.status, content_type=response.headers.get_content_type())
            if final.scheme != "https" or not (final.hostname == u.hostname or
                    (sheet and final.hostname and final.hostname.endswith(".googleusercontent.com"))):
                raise ValueError("Unexpected redirect destination.")
            if response.status != 200:
                raise ValueError(f"HTTP {response.status} did not deliver the requested document.")
            body = response.read(LIMIT + 1)
            if not body or len(body) > LIMIT:
                raise ValueError("Empty or oversized source response.")
            typ = rec["content_type"]
            if (sheet and typ != "text/csv") or (not sheet and typ not in {"text/html", "application/xhtml+xml"}):
                raise ValueError("Unexpected response content type.")
            text = body.decode(response.headers.get_content_charset() or "utf-8-sig")
            extract = sheet_extract(label, text, rec, as_of) if sheet else document_extract(label, text, rec, as_of)
    except HTTPError as exc:
        rec.update(http_status=exc.code, content_type=exc.headers.get_content_type() if exc.headers else "unknown",
                   retrieval_status="unavailable", summary=f"HTTP {exc.code} on the disclosed route.")
        exc.close()
    except (OSError, EOFError, HTTPException) as exc:
        rec.update(retrieval_status="unavailable", summary=f"Read failed ({type(exc).__name__}).")
    except (ValueError, LookupError, csv.Error) as exc:
        # Decode/parser errors can include source bytes. Only expose controlled messages.
        rec.update(retrieval_status="invalid", summary=str(exc) if type(exc) is ValueError else "Invalid source encoding or structure.")
    else:
        if extract:
            data = encoded(extract)
            name = label.lower() + ".json"
            (folder / name).write_bytes(data)
            rec.update(local_reference=f"sources/capture/{name}", content_hash=digest(data))
    return rec


def read_selection(path, scope):
    """Validate an operator-selected passage; never ingest a full browser export."""
    with path.open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("POLICY selection exceeds 64 KiB.")
    data = json.loads(raw)
    fields = {"run_id", "locator", "title", "section", "passage", "page_loaded_at", "captured_at"}
    if not isinstance(data, dict) or set(data) != fields or any(not isinstance(v, str) or not v.strip() for v in data.values()):
        raise ValueError("Unexpected or missing POLICY selection fields.")
    if data["run_id"] != scope["run_id"] or data["locator"] != scope["state"]["routes"]["POLICY"].rstrip("/"):
        raise ValueError("Selection does not match this run and POLICY route.")
    if ("internal polic" not in data["title"].lower() or len(data["title"]) > 300
            or len(data["section"]) > 240 or len(data["passage"]) > 8000):
        raise ValueError("Invalid POLICY title, section or selected passage.")
    times = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in
             (scope["created_at"], data["page_loaded_at"], data["captured_at"], now())]
    if any(t.utcoffset() is None for t in times) or times != sorted(times):
        raise ValueError("Reload POLICY after starting scope and capture it before importing.")
    return data


def capture(output, policy_selections=()):
    """Continue the scope run; all ten labels get a fresh attempt."""
    validator = Draft202012Validator(json.loads(SCHEMA.read_text()), format_checker=Draft202012Validator.FORMAT_CHECKER)
    rel = "snapshots/01-scope.json"
    source = (output / rel).read_bytes()
    scope = json.loads(source)
    validator.validate(scope)
    routes = scope["state"]["routes"]
    if scope["stage"] != "scope" or not isinstance(routes, dict) or set(routes) != LABELS:
        raise ValueError("Expected snapshot 01 and all ten routes.")
    early, = scope["state"]["source_attempts"]
    if early["id"] not in scope["produced_record_ids"] or early["locator"] != routes["SYSTEMS"]:
        raise ValueError("Scope attempt does not match the recorded SYSTEMS route.")
    if early["retrieval_status"] == "retrieved":
        if (early["local_reference"] != "sources/systems-scope.json" or
                digest((output / "sources/systems-scope.json").read_bytes()) != early["content_hash"]):
            raise ValueError("Scope extract hash mismatch. Preserve this run and retry from scope.")
    target = output / "snapshots/02-source-capture.json"
    dest = output / "sources/capture"
    if target.exists() or dest.exists():
        raise ValueError("Capture already exists. Preserve this attempt and use a fresh run for a retry.")
    selections = [read_selection(path, scope) for path in policy_selections]
    records = [dict(early, label="SYSTEMS")]
    gaps = list(scope["unresolved"])
    with TemporaryDirectory(dir=output) as tmp:
        folder = Path(tmp) / "capture"
        folder.mkdir()
        for label, locator in routes.items():
            rec = fetch(label, locator, folder, scope["state"]["as_of"][:10])
            records.append(rec)
            print(f"{label}: {rec['retrieval_status']}", flush=True)
        for index, selected in enumerate(selections, 1):
            name = f"policy-browser-{index}.json"
            data = encoded(selected)
            (folder / name).write_bytes(data)
            records.append(dict(id=f"source-policy-browser-{index}", label="POLICY",
                                source_role="internal-policy", authority="internal-control", evidence_ids=[],
                                locator=selected["locator"], retrieved_at=selected["captured_at"],
                                content_type="application/json", method="operator-selected browser extract",
                                version_metadata=None, retrieval_status="unverified",
                                summary="Live browser selection retained. Check revision, applicability and coverage before relying on this clause.",
                                local_reference=f"sources/capture/{name}", content_hash=digest(data)))
        for rec in records:
            if rec["retrieval_status"] != "retrieved":
                gaps.append(dict(id="gap-" + rec["id"], summary=rec["summary"], evidence_ids=[rec["id"]],
                                 resolution_need="Obtain and verify the disclosed source or resolve the indicated extract gaps on retry."))
        systems = next(r for r in records if r["id"] == "source-systems")
        if systems["local_reference"] and scope["status"] == "complete":
            rows = json.loads((folder / "systems.json").read_text())["rows"]
            found = {r["values"].get("system_id") for r in rows}
            expected = set(scope["state"]["systems_in_scope"])
            if expected - found or (scope["state"]["review_type"] == "broad-inventory" and expected != found):
                gaps.append(dict(id="gap-scope-change", summary="Current SYSTEMS membership differs from confirmed scope.",
                                 evidence_ids=[early["id"], systems["id"]], resolution_need="Reconfirm scope and retry."))
        blocked = scope["status"] == "blocked" or any(r["label"] in BINDING | {"CONSOLIDATED"}
                    and r["retrieval_status"] != "retrieved" for r in records)
        status = "blocked" if blocked else "partial" if gaps else "complete"
        decision = dict(id="capture-retention", summary="Retain reviewable public text and selected operational extracts.",
                        evidence_ids=[r["id"] for r in records], concern="Preserve source evidence within disclosure limits.",
                        options=["Full captures", "Selected extracts with locators"], chosen="Selected extracts with locators",
                        source_basis="Requester interview and actual responses.",
                        rationale="Persist only permitted internal fields. Keep version uncertainty and failed attempts visible.",
                        tradeoffs=["Changed internal prose can need privacy review before inclusion."],
                        downstream_effect="Stage 03 must resolve authority blockers before formal dependent conclusions.")
        snapshot = dict(schema_version=scope["schema_version"], snapshot_id=str(uuid4()), run_id=scope["run_id"],
                        stage="source-capture", sequence=2, created_at=now(), status=status,
                        predecessor=dict(snapshot_id=scope["snapshot_id"], path=rel, sha256=digest(source)),
                        consumed_record_ids=scope["produced_record_ids"],
                        produced_record_ids=[r["id"] for r in records[1:] + gaps + [decision]],
                        state={"sources": records}, unresolved=gaps, decisions=[decision])
        validator.validate(snapshot)
        for rec in records[1:]:
            if rec["local_reference"] and digest((folder / Path(rec["local_reference"]).name).read_bytes()) != rec["content_hash"]:
                raise ValueError("Written evidence hash mismatch.")
        (Path(tmp) / "snapshot.json").write_bytes(encoded(snapshot))
        dest.parent.mkdir(exist_ok=True)
        folder.rename(dest)
        (Path(tmp) / "snapshot.json").rename(target)
    print(f"Source capture {status}: {target}")
    return 0 if status == "complete" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("deliverables"))
    parser.add_argument("--policy-selection", type=Path, action="append", default=[],
                        help="reviewed Edge selection for this run (repeat for additional passages)")
    args = parser.parse_args()
    try:
        raise SystemExit(capture(args.output, args.policy_selection))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Source capture failed: {exc}\n")
