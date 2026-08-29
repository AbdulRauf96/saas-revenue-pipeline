"""One-off: print the date range each tag covers in a fixture."""

import json
import sys
from pathlib import Path


def main(path: str) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    tags = data["facts"]["us-gaap"]

    for tag, body in tags.items():
        ends = [f["end"] for unit in body["units"].values() for f in unit]
        count = len(ends)
        print(f"{tag:55} {min(ends)} to {max(ends)}  ({count} facts)")


if __name__ == "__main__":
    main(sys.argv[1])