#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PRIMARY_ACCOUNT = "tianyupeiandy@gmail.com"
SCHOOL_ACCOUNT = "yupeit@andrew.cmu.edu"


def load_items(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict):
        items = payload.get("items", [])
    elif isinstance(payload, list):
        items = payload
    else:
        raise SystemExit(f"Unsupported JSON shape in {path}")
    if not isinstance(items, list):
        raise SystemExit(f"Expected items array in {path}")
    return [item for item in items if isinstance(item, dict)]


def text_blob(item: dict[str, Any]) -> str:
    values = [
        item.get("id"),
        item.get("summary"),
        item.get("summaryOverride"),
        item.get("description"),
    ]
    return " ".join(str(value or "") for value in values).casefold()


def classify(item: dict[str, Any]) -> dict[str, Any]:
    calendar_id = str(item.get("id") or "")
    summary = str(item.get("summary") or "")
    role = str(item.get("accessRole") or "")
    blob = text_blob(item)
    primary = bool(item.get("primary")) or calendar_id == PRIMARY_ACCOUNT
    selected = bool(item.get("selected"))
    hidden = bool(item.get("hidden"))

    if primary:
        bucket = "00 Core - Google 主号"
        action = "keep selected; use as default write target"
        reason = "primary Google source of truth"
    elif is_school_calendar(blob, summary):
        bucket = "30 School Transition - review"
        action = "inventory future events; migrate reviewed items; then hide"
        reason = "school lifecycle risk"
    elif is_reference_calendar(blob, summary):
        bucket = "90 Reference - review"
        action = "keep or hide; do not rename/delete as owned calendar"
        reason = "system, holiday, task, birthday, or subscribed reference source"
    elif role in {"reader", "freeBusyReader"}:
        bucket = "20 Shared - review"
        action = "keep visible only if useful; do not rename as owner"
        reason = f"current account has {role} access"
    elif hidden:
        bucket = "80 Archive - review"
        action = "keep hidden unless needed"
        reason = "already hidden from CalendarList"
    elif role in {"owner", "writer"}:
        bucket = "10 Projects - review"
        action = "confirm owner/lifecycle; label, hide, or keep"
        reason = f"current account can modify calendar ({role})"
    else:
        bucket = "Review"
        action = "inspect metadata before changing"
        reason = "ownership and lifecycle are unclear"

    return {
        "bucket": bucket,
        "action": action,
        "reason": reason,
        "id": calendar_id,
        "summary": summary,
        "summaryOverride": item.get("summaryOverride") or "",
        "primary": primary,
        "accessRole": role,
        "selected": selected,
        "hidden": hidden,
    }


def is_reference_calendar(blob: str, summary: str) -> bool:
    known_summary = summary.casefold() in {
        "birthdays",
        "tasks",
        "reminders",
        "siri suggestions",
    }
    return (
        known_summary
        or "holiday" in blob
        or "#holiday@group.v.calendar.google.com" in blob
        or "birthday" in blob
        or "contacts" in blob
        or "task" in blob
        or "subscribed" in blob
    )


def is_school_calendar(blob: str, summary: str) -> bool:
    summary_tokens = {
        token.strip(" -_:/()[]{}").casefold()
        for token in summary.replace("|", " ").split()
    }
    return (
        SCHOOL_ACCOUNT in blob
        or "andrew.cmu.edu" in blob
        or "carnegie mellon" in blob
        or "cmu" in summary_tokens
    )


def print_tsv(rows: list[dict[str, Any]]) -> None:
    fields = [
        "bucket",
        "action",
        "summary",
        "summaryOverride",
        "id",
        "primary",
        "accessRole",
        "selected",
        "hidden",
        "reason",
    ]
    print("\t".join(fields))
    for row in rows:
        print("\t".join(str(row.get(field, "")) for field in fields))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create an advisory governance review table from Google Calendar calendarList JSON."
    )
    parser.add_argument("--calendar-list", required=True, help="JSON from gws calendar calendarList list.")
    parser.add_argument("--format", choices=["json", "tsv"], default="tsv")
    args = parser.parse_args()

    rows = [classify(item) for item in load_items(Path(args.calendar_list))]
    if args.format == "json":
        json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print_tsv(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
