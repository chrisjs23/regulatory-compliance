"""Run all seven boundaries afresh, archive the prior bundle, and verify promotion."""
import argparse
import json
from pathlib import Path
import shutil
from uuid import uuid4

import analyze
import capture
import publish
import reconcile
import run

PARTS = ("snapshots", "sources", "impact-register.csv", "compliance-brief.md", "action-calendar.ics")


def failure(attempt, stage, reason, previous_id):
    attempt.mkdir(parents=True, exist_ok=True)
    data = dict(stage=stage, reason=reason, previous_run_id=previous_id,
                run_id=None, created_at=run.now(), owner="Automation operator",
                recovery_action="Inspect the retained attempt, resolve access or damaged input, then start a fresh run.")
    path = attempt / "snapshots/01-scope.json"
    if path.exists():
        try:
            data["run_id"] = json.loads(path.read_bytes())["run_id"]
        except (ValueError, KeyError):
            pass
    (attempt / "failure.json").write_bytes(capture.encoded(data))
    print(f"Run failed at {stage}; retained attempt: {attempt}")
    return 2


def current_id(root):
    snapshots = root / "snapshots"
    if not snapshots.exists():
        return None
    ids = set()
    for name in publish.NAMES + ["07-publication-validation"]:
        path = snapshots / (name + ".json")
        if not path.exists():
            continue
        try:
            value = json.loads(path.read_bytes()).get("run_id")
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(value, str) and value:
            ids.add(value)
    if len(ids) != 1:
        raise ValueError("Prior snapshot run ID is missing or conflicting; preserve and inspect it before retrying.")
    return ids.pop()


def network_failure(attempt):
    """Distinguish an inaccessible execution environment from partial source evidence."""
    path = attempt / "snapshots/02-source-capture.json"
    if not path.exists():
        return False
    doc = json.loads(path.read_bytes())
    sources = doc["state"]["sources"]
    fresh = sources[1:]
    failed = [x for x in fresh if x["retrieval_status"] == "unavailable" and
              x.get("summary", "").startswith("Read failed")]
    return len(failed) >= 8 and sources[0]["retrieval_status"] == "unavailable"


def archive(root, old_id):
    base = root / "history" / old_id
    history = base / ("rearchive-" + str(uuid4())) if base.exists() else base
    history.mkdir(parents=True)
    valid_before = publish.verify_bundle(root)
    manifest = dict(run_id=old_id, archived_at=run.now(), prior_bundle_valid=valid_before,
                    available={}, missing=[], damaged=[])
    for index, name in enumerate(publish.NAMES + ["07-publication-validation"]):
        relative = "snapshots/" + name + ".json"
        path = root / relative
        try:
            doc = json.loads(path.read_bytes())
            publish.VALIDATE(doc)
            if index:
                prior = root / "snapshots" / ((publish.NAMES + ["07-publication-validation"])[index - 1] + ".json")
                if doc["predecessor"]["sha256"] != capture.digest(prior.read_bytes()):
                    manifest["damaged"].append(relative + " predecessor hash")
        except (OSError, ValueError, KeyError, TypeError, publish.ValidationError):
            manifest["damaged"].append(relative)
    try:
        two = json.loads((root / "snapshots/02-source-capture.json").read_bytes())
        for source in two["state"]["sources"]:
            if source.get("local_reference"):
                path = (root / source["local_reference"]).resolve()
                if (not path.is_relative_to((root / "sources").resolve()) or
                        capture.digest(path.read_bytes()) != source["content_hash"]):
                    manifest["damaged"].append(source["local_reference"])
    except (OSError, ValueError, KeyError, TypeError):
        manifest["damaged"].append("snapshots/02-source-capture.json source references")
    try:
        seven = json.loads((root / "snapshots/07-publication-validation.json").read_bytes())
        for artifact in seven["state"]["artifacts"]:
            file = root / artifact["path"]
            if not file.exists() or capture.digest(file.read_bytes()) != artifact["sha256"]:
                manifest["damaged"].append(artifact["path"])
    except (OSError, ValueError, KeyError, TypeError):
        manifest["damaged"].append("snapshots/07-publication-validation.json or its artifact references")
    try:
        for name in PARTS:
            source = root / name
            if not source.exists():
                manifest["missing"].append(name)
                continue
            source.rename(history / name)
            target = history / name
            if target.is_file():
                manifest["available"][name] = capture.digest(target.read_bytes())
            else:
                manifest["available"][name] = {str(p.relative_to(target)): capture.digest(p.read_bytes())
                                                for p in target.rglob("*") if p.is_file()}
        (history / "archive-manifest.json").write_bytes(capture.encoded(manifest))
    except Exception:
        for name in PARTS:
            saved = history / name
            if saved.exists():
                saved.rename(root / name)
        if not any(history.iterdir()):
            history.rmdir()
        raise
    return history


def restore(root, history, attempt):
    """Keep the failed new output while restoring the archived prior bundle."""
    for name in PARTS:
        active = root / name
        if active.exists():
            active.rename(attempt / name)
        saved = history / name if history else None
        if saved and saved.exists():
            if saved.is_dir():
                shutil.copytree(saved, active)
            else:
                shutil.copy2(saved, active)


def promote(root, attempt, old_id):
    history = archive(root, old_id) if old_id else None
    try:
        for name in PARTS:
            source = attempt / name
            if not source.exists():
                raise ValueError(f"New run lacks {name}")
            source.rename(root / name)
        if not publish.verify_bundle(root):
            raise ValueError("Promoted bundle failed independent validation")
    except Exception:
        restore(root, history, attempt)
        raise
    return history


def full_run(root, routes, broad=False, system_ids=(), retry_reason=None):
    root.mkdir(parents=True, exist_ok=True)
    old_id = current_id(root)
    if old_id and not retry_reason:
        raise ValueError("A retry reason is required when superseding an active run.")
    if not old_id and any((root / name).exists() for name in PARTS):
        raise ValueError("Existing outputs have no readable scope ID; preserve them before a new run.")
    attempts = root.parent / "review-runs"
    attempts.mkdir(parents=True, exist_ok=True)
    attempt = attempts / ("run-" + str(uuid4()))
    args = ["--routes", str(routes), "--output", str(attempt)]
    args += ["--broad"] if broad else [value for sid in system_ids for value in ("--system-id", sid)]
    if old_id:
        args += ["--supersedes-run-id", old_id, "--retry-reason", retry_reason]
    stage = "scope"
    try:
        run.main(args)
        stage = "source-capture"
        capture.capture(attempt)
        if network_failure(attempt):
            return failure(attempt, stage, "Execution environment could not read the disclosed routes.", old_id)
        stage = "authority-and-timing/evidence-reconciliation"
        reconcile.reconcile(attempt)
        stage = "impact-analysis/actions-and-approvals"
        analyze.analyze(attempt)
        stage = "publication-validation"
        publish.publish(attempt)
        if not publish.verify_bundle(attempt):
            raise ValueError("The new draft failed independent validation before promotion.")
        stage = "archive-and-promote"
        history = promote(root, attempt, old_id)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return failure(attempt, stage, f"{type(exc).__name__}: {exc}", old_id)
    new = json.loads((root / "snapshots/01-scope.json").read_bytes())
    last = json.loads((root / "snapshots/07-publication-validation.json").read_bytes())
    print(f"Current run: {new['run_id']} · {last['status']} · draft {last['state']['publication_status']}")
    if history:
        print(f"Previous run archived: {history}")
    return 0 if last["status"] == "complete" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--routes", type=Path, required=True)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--broad", action="store_true")
    scope.add_argument("--system-id", action="append", default=[])
    parser.add_argument("--output", type=Path, default=Path("deliverables"))
    parser.add_argument("--retry-reason")
    options = parser.parse_args()
    raise SystemExit(full_run(options.output, options.routes, options.broad,
                              options.system_id, options.retry_reason))
