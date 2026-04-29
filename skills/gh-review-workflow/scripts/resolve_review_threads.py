#!/usr/bin/env python3
"""Resolve GitHub PR review threads by id or from a saved review-state JSON dump."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

MUTATION = """\
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread {
      id
      isResolved
    }
  }
}
"""


def _run(cmd: list[str], stdin: str | None = None) -> str:
    proc = subprocess.run(cmd, input=stdin, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "command failed")
    return proc.stdout


def _thread_ids_from_json(path: Path) -> list[str]:
    data = json.loads(path.read_text())
    ids = []
    for thread in data.get("review_threads", []):
        if not thread.get("isResolved"):
            ids.append(thread["id"])
    return ids


def _resolve(thread_id: str) -> dict[str, object]:
    payload = _run(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={MUTATION}",
            "-F",
            f"threadId={thread_id}",
        ]
    )
    return json.loads(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("thread_ids", nargs="*")
    parser.add_argument("--from-json", type=Path)
    args = parser.parse_args()

    thread_ids = list(args.thread_ids)
    if args.from_json is not None:
        thread_ids.extend(_thread_ids_from_json(args.from_json))
    if not thread_ids:
        raise RuntimeError("provide thread ids or --from-json")

    seen = set()
    for thread_id in thread_ids:
        if thread_id in seen:
            continue
        seen.add(thread_id)
        result = _resolve(thread_id)
        json.dump(result, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
