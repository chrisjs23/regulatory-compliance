---
name: regulatory-change-impact-brief
description: Prepare Quillhaven Academy's evidence-backed EU AI Act Article 50 draft review, from confirmed scope and source capture through impact analysis, proposed actions and validated local artifacts.
---

# Prepare a regulatory change impact brief

Use the 26 August 2026 review date in Europe/Dublin. Midnight encodes the assigned calendar day in the schema. It does not establish a legal cutoff hour. Ask the requester to select a broad inventory or supply IDs for a focused review before using the command.

Run from the repository root with Python 3.10+ and the Draft 2020-12 validator. Set up once in a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install 'jsonschema[format]>=4.18,<5'
.venv/bin/python -m pip install 'icalendar>=6,<7'
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

## Reconcile authority and evidence (stage C)

Continue an existing run with snapshots 01 and 02. From the repository root, run the following once against the run directory. For the approved policy retry, pass the two later Edge selections and the original interview explicitly:

```sh
.venv/bin/python -B regulatory-change-impact-brief/scripts/reconcile.py --output deliverables \
  --selection review-runs/policy-retry/*3229777.json \
  --selection review-runs/policy-retry/*3381833.json \
  --interview interviews/project-b-regulatory-compliance-interview4.md
```

For a different run, omit these options or supply that run’s own reviewed selections. The script verifies the input chain and evidence hashes, then writes snapshots 03 and 04 in order. Exit 1 after both status lines means partial or blocked evidence. Existing Stage C outputs are protected. For an independent check after a run, use `.venv/bin/python -B tests/test_stage_c.py -v` (temporary copies, offline).

The [reviewed authority map](references/reviewed-authority.json) ties each claim to exact captured editions and blocks. A change to a required official extract requires rechecking those locators and the interpretation before updating its fingerprint. Even cosmetic changes can require review under this conservative check. Source rows retain their reported roles, dates, states and row locators. Later evidence is identified separately with its hash. Reported supplier market-entry dates concern products; each system’s provider/deployer role and rule applicability still require assessment.

## Analyze impacts and draft reviews (stage D)

From the repository root, continue a run that has snapshots 01–04:

```sh
.venv/bin/python -B regulatory-change-impact-brief/scripts/analyze.py --output deliverables
```

The script verifies the predecessor chain, retained captures and schema before writing snapshots 05 and 06. Existing Stage D outputs are protected. Exit 1 after both status lines means the snapshots are partial or blocked, not that they were lost. Inspect `state.impacts`, `state.proposed_actions`, `state.approval_requirements` and `state.review_requests`. The latter are local drafts; no request is sent and no approval is inferred. Source calendar dates remain proposals. A missing required official edition blocks dependent impact findings while preserving the operational record and open questions.

Run the focused offline check with `.venv/bin/python -B tests/test_stage_d.py -v`. It expects three passing tests. Stage E will render the register, brief and calendar from these same records after Stage D review.

## Render and validate the draft package (stage E)

From the repository root, continue a run that has snapshots 01–06:

```sh
.venv/bin/python -B regulatory-change-impact-brief/scripts/publish.py --output deliverables
```

This writes the register, brief and tentative iCalendar, rereads them, and writes snapshot 07 with exact artifact hashes and bindings for every unsent review request. A partial run can have `publication_status: validated` when its local files agree; the run remains partial and no human decision is implied. Exit 1 after the status line means the run is partial or blocked. Existing Stage E files are protected. For the active draft, run `.venv/bin/python -B regulatory-change-impact-brief/scripts/publish.py --output deliverables --verify`; exit 0 means the snapshot chain, parsed files, bindings and hashes still agree.

Run the focused offline acceptance check with `.venv/bin/python -B tests/test_stage_e.py -v`. It expects three passing tests and needs only the locally retained inputs. Calendar events are tentative date-only proposals. Undated proposals are omitted and explained in the brief and register. A binding authority blocker produces an empty calendar while keeping the proposed actions visible for review.

## Fresh end-to-end retry and recovery (stage F)

Run this one command from the repository root for the requester-confirmed broad inventory:

```sh
.venv/bin/python -B regulatory-change-impact-brief/scripts/full_run.py \
  --routes regulatory-change-impact-brief/references/routes.json \
  --broad --output deliverables \
  --retry-reason "Fresh end-to-end verification after Stage E review"
```

Use `--system-id ID` instead of `--broad` for each requester-selected ID in a focused review. The command makes a new run and attempts all ten disclosed routes, validates all seven stages and three drafts in a separate attempt directory, then archives the available previous active bundle under `deliverables/history/<old-run-id>/` before promotion. The archive manifest records missing or damaged prior files. A failed attempt stays under `review-runs/run-<id>/` with `failure.json` and a recovery action. An environment-wide read failure leaves the previous active bundle in place; it must be reported as a failed current attempt, never as a fresh success.

Exit 0 means a complete validated draft, exit 1 means a validated partial or blocked draft, and exit 2 means a failed attempt retained for diagnosis. The active draft can be checked independently with `.venv/bin/python -B regulatory-change-impact-brief/scripts/publish.py --output deliverables --verify`. Fresh POLICY browser selections require a new run-bound page load and operator capture; prior selections are preserved in history but cannot substitute for a fresh read. Run `.venv/bin/python -B tests/test_stage_f.py -v` for the focused offline recovery checks; expect two passing tests.
