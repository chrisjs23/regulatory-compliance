# Regulatory change impact brief — draft

Run ID: `98d7b402-5aa2-4fbc-b631-ae0e47552264`  
As of: 2026-08-26 (Europe/Dublin calendar date)  
Recipients: Legal and Operations  
Review state: **blocked**. No legal approval, policy activation, approved deadline or incident closure is asserted.

The IDs below resolve through snapshots 01–06 and retained extracts in `sources/`. This is a local review draft; requests are unsent.

## Source quality and limits

- `source-oj` (OJ): invalid; HTTP 202 did not deliver the requested document.
- `source-amend` (AMEND): invalid; HTTP 202 did not deliver the requested document.
- `source-consolidated` (CONSOLIDATED): invalid; HTTP 202 did not deliver the requested document.
- `source-time` (TIME): unverified; Could not establish a page version suitable for the review day.
- `source-policy` (POLICY): unavailable; HTTP 403 on the disclosed route.
- `authority-gap-oj`: binding authority blocker; Required oj edition unavailable, unsuitable or changed since passage review.
- `authority-gap-amend`: binding authority blocker; Required amend edition unavailable, unsuitable or changed since passage review.
- `authority-gap-consolidated`: binding authority blocker; Required consolidated edition unavailable, unsuitable or changed since passage review.
- TIME is guidance only while its revision for the review date is unverified. POLICY browser selections cover only identified passages. The manager confirmed the captured policy edition's effective date; activation remains unverified.
- Supplier market-entry dates for AI-003 and AI-008 are owner-reported product dates, not proof of supplier compliance or Academy provider status. AI-005 lacks current release evidence.

## Impact register findings

- `impact-AI-001-art50-1` · AI-001 · `art50-1` · **unresolved**: Required binding authority is unavailable or has changed. Basis: `systems-AI-001`, `evidence-REC-001`. Next: Legal must verify the official edition before any dependent conclusion.
- `impact-AI-002-art50-4-text` · AI-002 · `art50-4-text` · **unresolved**: Required binding authority is unavailable or has changed. Basis: `systems-AI-002`, `evidence-REC-002`, `issue-REC-002`. Next: Legal must verify the official edition before any dependent conclusion.
- `impact-AI-003-art50-4-media` · AI-003 · `art50-4-media` · **unresolved**: Required binding authority is unavailable or has changed. Basis: `systems-AI-003`, `evidence-REC-003`, `issue-REC-003`. Next: Legal must verify the official edition before any dependent conclusion.
- `impact-AI-003-art50-2` · AI-003 · `art50-2` · **unresolved**: Provider role, product release or binding authority is not verified for this provider-only rule. Basis: `systems-AI-003`, `authority-gap-oj`, `authority-gap-amend`, `authority-gap-consolidated`. Next: Legal confirms role; Operations obtains supplier marking evidence.
- `impact-AI-003-art111-4` · AI-003 · `art111-4` · **unresolved**: Provider role, product release or binding authority is not verified for this provider-only rule. Basis: `systems-AI-003`, `authority-gap-oj`, `authority-gap-amend`, `authority-gap-consolidated`. Next: Legal confirms role; Operations obtains supplier marking evidence.
- `impact-AI-004-art50-1` · AI-004 · `art50-1` · **unresolved**: Required binding authority is unavailable or has changed. Basis: `systems-AI-004`, `evidence-REC-004`. Next: Legal must verify the official edition before any dependent conclusion.
- `impact-AI-005-art50-3` · AI-005 · `art50-3` · **unresolved**: Required binding authority is unavailable or has changed. Basis: `systems-AI-005`, `evidence-REC-005`, `evidence-REC-006`, `issue-REC-005`. Next: Legal must verify the official edition before any dependent conclusion.
- `impact-AI-005-art111-4` · AI-005 · `art111-4` · **unresolved**: The current release, market-entry date and provider role are unknown; qualifying generative output is not established. Basis: `systems-AI-005`, `authority-gap-oj`, `authority-gap-amend`, `authority-gap-consolidated`. Next: Obtain current release and role evidence; Legal assesses eligibility.
- `impact-AI-006-art50-4-text` · AI-006 · `art50-4-text` · **unresolved**: Required binding authority is unavailable or has changed. Basis: `systems-AI-006`, `evidence-REC-007`. Next: Legal must verify the official edition before any dependent conclusion.
- `impact-AI-007-art50-1` · AI-007 · `art50-1` · **unresolved**: Required binding authority is unavailable or has changed. Basis: `systems-AI-007`, `evidence-REC-008`, `issue-REC-008`. Next: Legal must verify the official edition before any dependent conclusion.
- `impact-AI-008-art50-4-media` · AI-008 · `art50-4-media` · **unresolved**: Required binding authority is unavailable or has changed. Basis: `systems-AI-008`, `evidence-REC-009`, `evidence-REC-010`, `issue-REC-009`, `issue-REC-010`. Next: Legal must verify the official edition before any dependent conclusion.
- `impact-AI-008-art50-2` · AI-008 · `art50-2` · **unresolved**: Provider role, product release or binding authority is not verified for this provider-only rule. Basis: `systems-AI-008`, `authority-gap-oj`, `authority-gap-amend`, `authority-gap-consolidated`. Next: Legal confirms role; Operations obtains supplier marking evidence.
- `impact-AI-008-art111-4` · AI-008 · `art111-4` · **unresolved**: Provider role, product release or binding authority is not verified for this provider-only rule. Basis: `systems-AI-008`, `authority-gap-oj`, `authority-gap-amend`, `authority-gap-consolidated`. Next: Legal confirms role; Operations obtains supplier marking evidence.

## Conflicts and unresolved evidence

- `open-gap-source-oj` · source-wide · unresolved: HTTP 202 did not deliver the requested document. Owner: unassigned. Next: Obtain and verify the disclosed source or resolve the indicated extract gaps on retry.
- `open-gap-source-amend` · source-wide · unresolved: HTTP 202 did not deliver the requested document. Owner: unassigned. Next: Obtain and verify the disclosed source or resolve the indicated extract gaps on retry.
- `open-gap-source-consolidated` · source-wide · unresolved: HTTP 202 did not deliver the requested document. Owner: unassigned. Next: Obtain and verify the disclosed source or resolve the indicated extract gaps on retry.
- `open-gap-source-time` · source-wide · unresolved: Could not establish a page version suitable for the review day. Owner: unassigned. Next: Obtain and verify the disclosed source or resolve the indicated extract gaps on retry.
- `open-gap-source-policy` · source-wide · unresolved: HTTP 403 on the disclosed route. Owner: unassigned. Next: Obtain and verify the disclosed source or resolve the indicated extract gaps on retry.
- `open-authority-gap-oj` · source-wide · unresolved: Required oj edition unavailable, unsuitable or changed since passage review. Owner: Legal. Next: Verify the official edition and recheck passage locators.
- `open-authority-gap-amend` · source-wide · unresolved: Required amend edition unavailable, unsuitable or changed since passage review. Owner: Legal. Next: Verify the official edition and recheck passage locators.
- `open-authority-gap-consolidated` · source-wide · unresolved: Required consolidated edition unavailable, unsuitable or changed since passage review. Owner: Legal. Next: Verify the official edition and recheck passage locators.
- `open-issue-REC-002` · AI-002 · unresolved: No evidence that recipients are told when generated text is used. Owner: Admissions. Next: Obtain missing or current proof from the record owner.
- `open-issue-REC-005` · AI-005 · unresolved: Provider role questionnaire predates the current release. Owner: Assessment Operations. Next: Obtain missing or current proof from the record owner.
- `open-issue-REC-009` · AI-008 · unresolved: Visible label verified but machine-readable provenance not checked. Owner: Communications. Next: Obtain missing or current proof from the record owner.
- `open-issue-REC-010` · AI-008 · unresolved: No Legal approval or expiry date recorded. Owner: Communications. Next: Obtain missing or current proof from the record owner.
- `open-policy-coverage` · source-wide · unresolved: Retained policy evidence covers only selected passages. Other control requirements remain unresolved. Owner: Operations. Next: Supply versioned policy clauses for each remaining control.
- `open-issue-REC-003` · AI-003 · conflicting: Visible label exists but exported platform copy may have lost metadata. Owner: Communications. Next: Obtain current owner evidence and reconcile competing reports.
- `open-issue-REC-008` · AI-007 · conflicting: Owner says a banner exists but the current capture shows none. Owner: Marketing. Next: Obtain current owner evidence and reconcile competing reports.

## Proposed actions and dates

- `action-ACT-001` · AI-004 · Add and verify first-interaction AI notice · owner Learning Experience · proposed 2026-09-04 · approval **pending** · omitted from calendar: upstream review blocked or failed. Basis: `calendar-ACT-001`, `impact-AI-004-art50-1`.
- `action-ACT-002` · AI-007 · Resolve disclosure evidence conflict · owner Marketing · proposed 2026-09-03 · approval **pending** · omitted from calendar: upstream review blocked or failed. Basis: `calendar-ACT-002`, `impact-AI-007-art50-1`.
- `action-ACT-003` · AI-002 · Confirm recipient disclosure practice · owner Admissions · proposed 2026-09-08 · approval **pending** · omitted from calendar: upstream review blocked or failed. Basis: `calendar-ACT-003`, `impact-AI-002-art50-4-text`.
- `action-ACT-004` · AI-003 · Verify machine-readable provenance after publishing · owner Communications · proposed 2026-09-10 · approval **pending** · omitted from calendar: upstream review blocked or failed. Basis: `calendar-ACT-004`, `impact-AI-003-art50-4-media`.
- `action-ACT-005` · AI-005 · Refresh provider-role and release evidence · owner Assessment Operations · proposed 2026-09-12 · approval **pending** · omitted from calendar: upstream review blocked or failed. Basis: `calendar-ACT-005`, `impact-AI-005-art50-3`.
- `action-ACT-006` · AI-008 · Complete provenance test · owner Communications · proposed 2026-09-09 · approval **pending** · omitted from calendar: upstream review blocked or failed. Basis: `calendar-ACT-006`, `impact-AI-008-art50-4-media`.
- `action-ACT-007` · AI-008 · Review exception request · owner Legal · proposed 2026-09-15 · approval **pending** · omitted from calendar: upstream review blocked or failed. Basis: `calendar-ACT-007`, `impact-AI-008-art50-4-media`.
- `action-ACT-008` · ALL · Quarterly AI register evidence review · owner Operations · proposed 2026-10-02 · approval **pending** · omitted from calendar: upstream review blocked or failed. Basis: `calendar-ACT-008`.

## Decisions requested

Review request bindings are in `snapshots/07-publication-validation.json` and identify this brief by exact path and hash. No request has been sent.

- `request-ACT-001` · Operations · subject `action-ACT-001` · source version `calendar-2026-08-26` · evidence `action-ACT-001`, `calendar-ACT-001`, `impact-AI-004-art50-1`: Approve or amend this proposed action and date after reviewing its evidence?
- `request-ACT-002` · Operations · subject `action-ACT-002` · source version `calendar-2026-08-26` · evidence `action-ACT-002`, `calendar-ACT-002`, `impact-AI-007-art50-1`: Approve or amend this proposed action and date after reviewing its evidence?
- `request-ACT-003` · Legal · subject `action-ACT-003` · source version `calendar-2026-08-26` · evidence `action-ACT-003`, `calendar-ACT-003`, `impact-AI-002-art50-4-text`: Approve or amend this proposed action and date after reviewing its evidence?
- `request-ACT-004` · Operations · subject `action-ACT-004` · source version `calendar-2026-08-26` · evidence `action-ACT-004`, `calendar-ACT-004`, `impact-AI-003-art50-4-media`: Approve or amend this proposed action and date after reviewing its evidence?
- `request-ACT-005` · Legal · subject `action-ACT-005` · source version `calendar-2026-08-26` · evidence `action-ACT-005`, `calendar-ACT-005`, `impact-AI-005-art50-3`: Approve or amend this proposed action and date after reviewing its evidence?
- `request-ACT-006` · Operations · subject `action-ACT-006` · source version `calendar-2026-08-26` · evidence `action-ACT-006`, `calendar-ACT-006`, `impact-AI-008-art50-4-media`: Approve or amend this proposed action and date after reviewing its evidence?
- `request-ACT-007` · Legal · subject `action-ACT-007` · source version `calendar-2026-08-26` · evidence `action-ACT-007`, `calendar-ACT-007`, `impact-AI-008-art50-4-media`: Approve or amend this proposed action and date after reviewing its evidence?
- `request-ACT-008` · Operations · subject `action-ACT-008` · source version `calendar-2026-08-26` · evidence `action-ACT-008`, `calendar-ACT-008`: Approve or amend this proposed action and date after reviewing its evidence?
- `request-impact-AI-001-art50-1` · Legal · subject `impact-AI-001-art50-1` · source version `register-2026-08-26` · evidence `impact-AI-001-art50-1`: Legal must verify the official edition before any dependent conclusion.
- `request-impact-AI-002-art50-4-text` · Legal · subject `impact-AI-002-art50-4-text` · source version `register-2026-08-26` · evidence `impact-AI-002-art50-4-text`: Legal must verify the official edition before any dependent conclusion.
- `request-impact-AI-003-art50-4-media` · Legal · subject `impact-AI-003-art50-4-media` · source version `register-2026-08-26` · evidence `impact-AI-003-art50-4-media`: Legal must verify the official edition before any dependent conclusion.
- `request-impact-AI-003-art50-2` · Legal · subject `impact-AI-003-art50-2` · source version `register-2026-08-26` · evidence `impact-AI-003-art50-2`: Legal confirms role; Operations obtains supplier marking evidence.
- `request-impact-AI-003-art111-4` · Legal · subject `impact-AI-003-art111-4` · source version `register-2026-08-26` · evidence `impact-AI-003-art111-4`: Legal confirms role; Operations obtains supplier marking evidence.
- `request-impact-AI-004-art50-1` · Legal · subject `impact-AI-004-art50-1` · source version `register-2026-08-26` · evidence `impact-AI-004-art50-1`: Legal must verify the official edition before any dependent conclusion.
- `request-impact-AI-005-art50-3` · Legal · subject `impact-AI-005-art50-3` · source version `register-2026-08-26` · evidence `impact-AI-005-art50-3`: Legal must verify the official edition before any dependent conclusion.
- `request-impact-AI-005-art111-4` · Legal · subject `impact-AI-005-art111-4` · source version `unverified` · evidence `impact-AI-005-art111-4`: Obtain current release and role evidence; Legal assesses eligibility.
- `request-impact-AI-006-art50-4-text` · Legal · subject `impact-AI-006-art50-4-text` · source version `register-2026-08-26` · evidence `impact-AI-006-art50-4-text`: Legal must verify the official edition before any dependent conclusion.
- `request-impact-AI-007-art50-1` · Legal · subject `impact-AI-007-art50-1` · source version `register-2026-08-26` · evidence `impact-AI-007-art50-1`: Legal must verify the official edition before any dependent conclusion.
- `request-impact-AI-008-art50-4-media` · Legal · subject `impact-AI-008-art50-4-media` · source version `register-2026-08-26` · evidence `impact-AI-008-art50-4-media`: Legal must verify the official edition before any dependent conclusion.
- `request-impact-AI-008-art50-2` · Legal · subject `impact-AI-008-art50-2` · source version `register-2026-08-26` · evidence `impact-AI-008-art50-2`: Legal confirms role; Operations obtains supplier marking evidence.
- `request-impact-AI-008-art111-4` · Legal · subject `impact-AI-008-art111-4` · source version `register-2026-08-26` · evidence `impact-AI-008-art111-4`: Legal confirms role; Operations obtains supplier marking evidence.

Legal retains interpretation and exception decisions. Operations retains policy activation, deadline approval and incident closure. System owners verify facts.
