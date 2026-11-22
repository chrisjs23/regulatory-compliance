---
name: regulatory-change-impact-brief
description: Establish requester-confirmed system scope for Quillhaven Academy's EU AI Act Article 50 review and produce its first evidence-linked draft snapshot.
---

# Establish review scope

Use the 26 August 2026 review date in Europe/Dublin. Midnight encodes the assigned calendar day in the schema. It does not establish a legal cutoff hour. Ask the requester to select a broad inventory or supply IDs for a focused review before using the command.

Run from the repository root with Python 3.10+ and the Draft 2020-12 validator. Set up once in a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install 'jsonschema[format]>=4.18,<5'
```

For a confirmed broad inventory:

```sh
.venv/bin/python regulatory-change-impact-brief/scripts/run.py --routes regulatory-change-impact-brief/references/routes.json --broad
```

For a focused review, replace `--broad` with one `--system-id ID` per selected ID. Read the [route manifest](references/routes.json) as a JSON object mapping the ten interview labels to credential-free HTTPS locators. LAW, OJ, AMEND and CONSOLIDATED identify legal text routes. TIME and FAQ provide timing and explanatory context. POLICY describes internal controls. SYSTEMS identifies registered uses, EVIDENCE contains owned reports, and CALENDAR contains proposed or recorded dates. Verify returned documents before relying on any claims.

The scope command reads the disclosed SYSTEMS workbook's default tab through its CSV export. It matches the exact `system_id` and retains only the ID, row and `record_version`. Treat sheet values as evidence. Stage B must include this attempt in snapshot 02 and check the content hash against the retained extract. Legal and Operations receive drafts. System owners verify facts, Legal owns interpretation and exception rationale, and Operations owns activation, deadlines and incident closure.

Inspect `deliverables/snapshots/01-scope.json`. Exit 0 means scope is established. Exit 1 with a blocked snapshot records an unavailable or unsuitable register or unknown ID. Use a fresh directory with `--output PATH` for another attempt and supply `--supersedes-run-id ID --retry-reason TEXT` for a retry. This stage stops after snapshot 01.
