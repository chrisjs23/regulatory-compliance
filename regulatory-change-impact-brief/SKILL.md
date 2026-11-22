---
name: regulatory-change-impact-brief
description: Establish requester-confirmed system scope for Quillhaven Academy's EU AI Act Article 50 review and capture the ten disclosed sources for a review-ready evidence record.
---

# Establish review scope and capture evidence

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

Inspect `deliverables/snapshots/01-scope.json`. Exit 0 means scope is established. Exit 1 with a blocked snapshot records an unavailable or unsuitable register or unknown ID. Use a fresh directory with `--output PATH` for another attempt and supply `--supersedes-run-id ID --retry-reason TEXT` for a retry. This invocation stops after snapshot 01.

## Capture sources (stage B)

To extend an existing scope run, use the following command once from the repository root:

```sh
.venv/bin/python -B regulatory-change-impact-brief/scripts/capture.py --output deliverables
```

For a fresh attempt through both stages, append `--through-capture` to the scope command and provide a new, empty output directory. Each run fetches the ten routes. Snapshot 02 also carries the earlier SYSTEMS scope read, binds snapshot 01 by ID and SHA-256, and points to extracts relative to the output directory. Reusing an existing capture directory is refused.

Read `snapshots/02-source-capture.json` for the result. Exit 0 means complete capture. Exit 1 means a partial or blocked snapshot was written. Inspect each source’s status, issues, version metadata and evidence path. An unavailable or unsuitable required legal text blocks dependent conclusions. A captured page can still have unresolved currency. Source capture establishes what can be reviewed; legal applicability is evaluated at the next stage.

Official page extracts use numbered visible text blocks. Sheet extracts use the disclosed workbook, default tab and source row. Only the selected columns are retained. For internal text, the [retention list](references/extract-values.json) permits exact values inspected for disclosure. It supplies no evidence on its own. A changed value outside the list is omitted and flagged by field and row. Review the new value for disclosure before extending the list. Keep credentials, personal details, and raw internal responses out of the repository. If POLICY becomes accessible, inspect the policy revision and select permitted paragraphs before retaining its text.

Run the stage B acceptance test with `.venv/bin/python -B tests/test_stage_b.py -v`. It uses temporary fixtures and needs no network access.

### Optional Edge selection for POLICY

After starting a fresh scope run, generate its favorite URL with
`python3 regulatory-change-impact-brief/scripts/policy_bookmark.py --output RUN_DIRECTORY`.
In WSL, pipe that command to `clip.exe` to copy it directly. Edit the test favorite in Edge and paste into its URL field.

Reload POLICY **after** creating the scope snapshot. Highlight one permitted policy passage, click the favorite, enter the visible section heading and review the local download preview. The file records the passage, heading, title, route, run ID, page-load time and selection time. Capture visible policy revision or effective-date wording as another passage if available. Each run needs its own freshly generated favorite URL.

Run `capture.py --output RUN_DIRECTORY --policy-selection DOWNLOADED_JSON` with the project's Python interpreter. Repeat the option for multiple passages. Direct reads still run. Snapshot 02 distinguishes HTTP results from operator-selected evidence and retains the latter as unverified pending a check of coverage and revision. Keep prior runs intact. The preview favorite alone produces no evidence file.
