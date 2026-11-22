"""Print the Edge favorite URL for the specified scope run."""
import argparse
import json
from pathlib import Path
from urllib.parse import quote


def bookmark(output):
    if (output / "snapshots/02-source-capture.json").exists():
        raise ValueError("Snapshot 02 already exists. Start a fresh scope run first.")
    scope = json.loads((output / "snapshots/01-scope.json").read_bytes())
    binding = {"locator": scope["state"]["routes"]["POLICY"].rstrip("/"),
               "run_id": scope["run_id"], "started": scope["created_at"]}
    script = Path(__file__).with_suffix(".js").read_text()
    return "javascript:" + quote(script.replace("__SCOPE__", json.dumps(binding)), safe="()")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(bookmark(args.output))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"{exc}\n")
