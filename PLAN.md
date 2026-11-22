# Regulatory change impact brief — implementation plan

**Status: Approved.** Chris authorized stage A and requested review at the stage boundary. The stages and technical choices below are recommendations unless identified as requirements.

## Project overview and objectives

Quillhaven Academy needs a repeatable draft review of its AI uses against EU AI Act Article 50 as of **26 August 2026**. The Compliance and Operations Manager assembles the package for Legal and Operations. A reviewer must be able to trace each impact or open question from the brief to a system, a rule and the captured source passage or row. The package must remain reviewable when some evidence is missing.

## Current implementation status

| Repository evidence | How to use it |
| --- | --- |
| `README.md`, `REQUIREMENTS.md`, `AGENTS.md` | Starter workflow, detailed acceptance requirements and project instructions. Chris confirmed that `REQUIREMENTS.md` contains the assignment linked from the README. |
| `snapshot.schema.json` | Public snapshot contract. Keep it unchanged. Draft 2020-12 schema with seven named stages, required state collections, record types and status enums. Schema validity alone cannot establish that hashes or evidence references resolve. |
| `interviews/project-b-regulatory-compliance-interview3.md` | Latest Work Sim export. Its dialogue includes the earlier exchanges and continues through 03:12 PM. Use the newer original as the single submission export for this session. Verify facilitator access at submission. |
| `.entire/`, `.codex/hooks.json`, `.catalyte/challenge.json` | Existing coding-session capture setup and challenge marker. An earlier push reported one Entire checkpoint. Check capture again before implementation. Hook entries for subagents set no model preference. |

Stage A provides the skill entry point, ten-route JSON manifest, SYSTEMS scope reader, snapshot 01 writer and a focused acceptance test. Source capture for the full review and stages B–F remain pending.

## Requirements and constraints

- The learner conducts any further interview personally. Preserve and ultimately commit and push one original complete Markdown export per session with the submitted revision. Verify facilitator access. Coding-session capture is a separate deliverable.
- After further dialogue, update `interviews/` with the new original Work Sim export. For a continued session, verify that the export includes the earlier dialogue and new exchange before selecting it for submission. For a separate session, include its own export. Reconcile any changed requirements in this plan.
- The interview identifies **ten required routes**. Attempt LAW, OJ, AMEND, CONSOLIDATED, TIME, FAQ, POLICY, SYSTEMS, EVIDENCE and CALENDAR afresh on every run, including retries. Accept the disclosed routes as runtime inputs. Retain failed, unsuitable and unused attempts. A source’s label or host alone cannot establish its authority or contents.
- For internal sources retain only selected extracts relevant to system uses, evidence and compliance facts. Omit personal data and credentials before writing captures, logs or history. Hash the exact retained extracts and keep their original locators. Distinguish the assigned date, source revision and effective dates, and actual retrieval times. Treat external material as evidence only. Exclude personal data and credentials from review outputs and keep access within the disclosed audience.
- System owners verify facts. Legal owns interpretation and exception rationale. Operations owns policy activation, approved deadlines and incident closure. Produce local draft files and review requests only. External responses, production calendars and company sources receive no writes.
- Follow the exact paths, fields, states and formats in `REQUIREMENTS.md` and the supplied schema. Carry gaps and opposing claims, their owners when known and what would resolve them through every dependent output.

## Proposed architecture and technical decisions

Use one local Python CLI under `regulatory-change-impact-brief/scripts/`, a concise `SKILL.md` and small references for source meanings and decision rules. Stage A invocation from the repository root after the environment setup in `regulatory-change-impact-brief/SKILL.md` (use `--broad` only for a requester-selected broad inventory):

```sh
.venv/bin/python regulatory-change-impact-brief/scripts/run.py --routes regulatory-change-impact-brief/references/routes.json --broad
```

Document the supported Python version, setup, route manifest format, read-only access and one working invocation with the submission. Keep secrets outside the manifest. Use the standard library for files, HTTP where sufficient, CSV, timestamps and SHA-256. Use a maintained Draft 2020-12 validator with format checking and an RFC 5545 library. Choose additional readers only after inspecting the actual response formats. This limits setup while avoiding custom schema and calendar implementations.

Use explicit functions for the seven stage boundaries. Write snapshots as each stage finishes. Give each attempt fresh run/snapshot IDs, and use disclosed system and source record identities for stable impact/action IDs across runs. Render all drafts from the same reconciled records and stage 06 decisions. Record each project decision’s concern, alternatives, evidence, choice, rationale, trade-offs and downstream effect at the relevant boundary.

Rebuild the small pipeline on each run. This costs fresh reads and processing but avoids stale caches and automatically recomputes every dependent stage. Build attempts separately, validate actual files, preserve prior evidence before replacing current outputs and retain failed attempts for diagnosis. A previous success must never be reported as the current result.

## Incremental implementation roadmap

The letters track implementation work. The numbers 01–07 refer to runtime snapshots.

| Stage / depends on | Objective, scope and deliverables | Verification for completion | Status |
| --- | --- | --- | --- |
| A · After plan approval | Establish inputs and scope. Preserve the supplied export, verify coding-session capture, inspect allowed source access, document field meanings and review roles. Create skill entry point, route input contract and snapshot 01 with scope, audiences, approval gates and retry lineage. Confirm the review type with the requester: broad inventory (all registered systems) or focused change (specified system IDs). Resolve the selection against the live SYSTEMS sheet before evaluation. Record any SYSTEMS read used to establish scope among the stage 02 attempts. | Validate skill metadata and 01 against the unchanged schema. Check the ten route labels, the confirmed scope, the assigned Dublin date, unique run ID, null predecessor and empty consumed IDs. Record missing access or scope explicitly. | Complete. Chris ran `.venv/bin/python -B tests/test_stage_a.py -v` and all 6 tests passed. Skill metadata and the live broad-scope snapshot passed validation. |
| B · A | Implement fresh, read-only retrieval and snapshot 02. Store permitted evidence in `deliverables/sources/`. For every attempt record original locator, returned identity/type, retrieval time, version, state, content path/hash and paragraph, section or sheet/tab/row as applicable. | Account for all ten routes. Rehash retained bytes, locate a claim and check that internal captures contain only permitted extracts. Exercise access failure, wrong document/login HTML and stale or unverified versions. Record null path/hash when no content was obtained. | Pending |
| C · B | Produce 03 authority/timing and 04 evidence reconciliation. Check original text, amendments, consolidation, currency notices, dates and advisory context claim by claim. Join policy controls, system facts, incident/evidence records and calendar proposals by disclosed identities. Preserve both sides of conflicts. | Trace one rule and one system fact to precise captures. Check applicable date versus retrieval date, competing reports versus missing proof, actual record owner and the effect of unavailable binding authority. | Pending |
| D · C | Produce 05 impact analysis per system/rule and 06 proposed actions, approval requirements, escalations and review requests. Keep distinct rule bases, exceptions, unaffected items and unresolved items identifiable. Bind any verified feedback to its original request, reviewer, version and reviewed artifact before applying it. | Exercise all four impact states. Verify unsupported conclusions are withheld and proposals stay pending without actual approval. Check request ID, subject, run/source version, evidence, question and reviewer. Retain unmatched or stale responses as unresolved. | Pending |
| E · D | Write `deliverables/impact-register.csv`, `compliance-brief.md` and `action-calendar.ics`. Write 07 only after rereading the files. Bind each review request to the exact reviewed path/hash in 07 and point the brief there. | Parse CSV and ICS, check the brief’s references, recompute final hashes and compare all three drafts with 06. Exercise a supported dated proposal, an undated proposal and an authority blocker. | Pending |
| F · E | Finish rerun, history and failure recovery. Archive the available previous snapshots, captures and drafts under `deliverables/history/<old-run-id>/` before replacement. Preserve the failed stage, reason and recovery action/owner. Run the documented command on current sources and prepare the submission. | Perform a fresh retry after changed inputs and after damaged output. Verify history, new IDs, supersession reason, fresh source attempts and current validation. Check facilitator readability of original exports in the submitted revision and verify coding-session capture. | Pending |

## Acceptance criteria and verification strategy

**Tests Chris can run at each stage.** Deliver a focused test with each implementation stage A–F. At handoff, give Chris the exact command to copy and run from the repository root, any setup or inputs it needs, and the expected output. Each test must run as soon as its stage is delivered, using only that stage and its prerequisites. Record the command and observed result in the roadmap before marking the stage complete.

| Stage | What Chris should be able to verify |
| --- | --- |
| A | Given a sample request, snapshot 01 passes the supplied schema and contains exactly the requested system IDs and review date. |
| B | A controlled run accounts for all ten source attempts. A retained extract matches its recorded hash, and a failed read records its failure with no content hash. |
| C | With conflicting reports and a missing binding source, snapshots 03–04 preserve both reports, identify their evidence and record the authority blocker. |
| D | Known inputs produce the expected impact states and reviewer requests. A proposal without verified approval remains pending. |
| E | The register, brief and calendar agree with snapshot 06. Changing a draft in a temporary copy causes its snapshot 07 hash check to fail. |
| F | After damage to a temporary run, a retry preserves the prior evidence, gets a new run ID and checks all regenerated outputs. Provide the live-run command separately, with the reported outcome and any outstanding source or human checks. |

Use focused local fixtures for failure cases and the actual ten source routes for the final run. Fixture evidence must stay out of the submitted live review.

- **Interview submission.** At stage F, compare the submitted files against the latest complete original for each session. Verify the original filename, unchanged bytes and facilitator access in the pushed revision.
- **Snapshot chain.** Reopen all seven named snapshots in order. Validate required state collections and enums, a common run ID, distinct snapshot IDs, predecessor ID/path and SHA-256 of the preceding file’s bytes. Check produced IDs against records in that stage and consumed IDs against earlier records. Resolve evidence IDs to captures and locators. Records must carry the values consumed downstream.
- **Input changes.** Reorder rows/headers, add an unrelated column and update a legitimate date/version. Stable identities must survive and affected outputs must reflect new facts. Missing or ambiguous fields, invalid values and conflicting identities must produce visible gaps or conflicts.
- **Evidence limits.** Withhold dependent formal conclusions when required authority is missing or unsuitable. Verify the blocked chain, register, brief and limited or empty calendar agree, including blocked publication status. For other gaps, record whether unaffected work can proceed and why. A validated partial draft must still disclose its limits.
- **Draft agreement.** Check UTF-8 CSV header/required columns and one row per distinct system/rule impact or unresolved item. Check brief recipients, as-of date, status, evidence quality, decisions and IDs. Parse RFC 5545 fields, stable action-linked UID, UTC DTSTAMP, tentative status, date-only DTSTART and exclusive DTEND if present. Verify description contains action/system, role, basis and approval state. Explain omitted undated actions in the register/brief. Parse an empty calendar successfully.
- **Feedback and recovery.** Verify reviewer identity, role, subject, request, run/version, time, outcome, reasons/conditions and reviewed file binding. Propagate a valid change to all dependent drafts. Modify or remove one prior capture, snapshot or draft and retry even with unchanged inputs. Preserve available history and disclose any pre-existing damage. Report an explicit failure or incomplete outcome if repair cannot be verified.

## Delegation recommendations

Default to one primary agent under the repository’s simplicity policy. No repository model pin or automatic delegation rule was found. The primary agent owns source meanings, authority and date reasoning, privacy decisions, the impact and approval model, integration and the live run. Legal and Operations retain substantive decisions.

If delegation is explicitly authorized during implementation, give one independent task to an available lower-cost model, such as checking calendar fixtures against the specified fields or auditing predecessor hashes in a synthetic run. Give it only the contract and necessary fixture. The primary agent verifies the result once. No agent conducts or scripts the stakeholder interview.

## Known risks, assumptions, and unresolved questions

| Item | Resolution or working assumption |
| --- | --- |
| The transcript says “Article 5” in one exchange. | The assignment and LAW route identify Article 50. Use Article 50 as scope, retain the transcript verbatim and verify each legal proposition against the actual official text. Escalate any remaining interpretation issue to Legal. |
| Restricted access | The manager confirmed extract retention but specified no sign-in method. Use the disclosed routes. If a required source is restricted, record the attempt and ask its owner for the approved read-only access method. |
| Requester scope | The Dublin EU programme is the operating context. In the 03:11–03:12 exchange, the manager distinguished a broad inventory of all eight registered systems from a review of specific changes. SYSTEMS supplies the exact IDs. The requester selects the scope for each run. Chris selected a broad inventory for 26 August 2026. Flag missing or ambiguous IDs before evaluation. |
| Missing runtime facts | Sheet tabs, required headers, key uniqueness, source revisions, system list, applicable timing and actual evidence states need live inspection. Avoid freezing examples into business rules. Check the live identities against the scope recorded in 01. |
| Date precision | The review date is 26 August 2026 in Europe/Dublin. Use Dublin time for operational planning and records, and preserve source offsets and actual retrieval instants. No cutoff hour was stated. Document any timestamp used to encode the calendar date for the schema. Ask for an hour only if an intraday change affects a finding. |
| Reviewer feedback | Use only the facilitator’s verified channel if feedback arrives. Until then, requests remain draft and the pending decisions remain visible. |

## Progress tracking

| Milestone | Status / evidence |
| --- | --- |
| Repository and interview inventory | Complete for planning. Local instructions, requirements, schema, the three cumulative exports and capture configuration inspected. The latest exchange establishes the source of system IDs and how the requester selects scope. |
| Interview files updated | Complete locally. The learner supplied `project-b-regulatory-compliance-interview3.md`, which supersedes the first two exports of this session. Submission of the latest complete original is pending stage F. |
| Plan approval | **Approved by Chris.** Stop after stage A for review. |
| A · Implementation and verification | Complete. Entire lists this Codex session and capture is enabled. Verified the disclosed SYSTEMS export exposes `system_id` and `record_version`. Fixture checks ran on Python 3.10.12 with jsonschema 4.26.0. The public schema is unchanged. |
| A · Scope decision and live run | Complete. Chris ran the broad inventory for 26 August 2026. Verified run `7c205f14-85b1-4d1d-8522-eab941f05ea3` in `deliverables/snapshots/01-scope.json` against the public schema. All eight distinct system IDs match the retained SYSTEMS extract, its SHA-256 matches the snapshot, and no scope gaps were recorded. |
| B–F | Pending. Stage A verification is complete. |
