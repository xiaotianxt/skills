#!/usr/bin/env python3

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def event_start(event: dict[str, Any]) -> str:
    start = event.get("start") or {}
    if not isinstance(start, dict):
        return ""
    if start.get("date"):
        return f"date:{start.get('date')}"
    date_time = str(start.get("dateTime") or "")
    return normalized_datetime(date_time)


def normalized_datetime(value: str) -> str:
    if not value:
        return ""
    candidate = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return " ".join(value.split())
    if parsed.tzinfo is None:
        return parsed.isoformat()
    return parsed.astimezone(timezone.utc).isoformat()


def event_start_display(event: dict[str, Any]) -> str:
    start = event.get("start") or {}
    if not isinstance(start, dict):
        return ""
    return str(start.get("dateTime") or start.get("date") or "")


def event_location(event: dict[str, Any]) -> str:
    return " ".join(str(event.get("location") or "").split()).casefold()


def event_summary(event: dict[str, Any]) -> str:
    return " ".join(str(event.get("summary") or "").split()).casefold()


def event_signature(event: dict[str, Any]) -> tuple[str, str, str]:
    return (event_summary(event), event_start(event), event_location(event))


def short_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": event.get("id"),
        "iCalUID": event.get("iCalUID"),
        "summary": event.get("summary"),
        "start": event.get("start"),
        "end": event.get("end"),
        "location": event.get("location"),
        "htmlLink": event.get("htmlLink"),
    }


def build_preview(source: list[dict[str, Any]], target: list[dict[str, Any]]) -> dict[str, Any]:
    target_ical_uids = Counter(
        str(event.get("iCalUID"))
        for event in target
        if event.get("iCalUID")
    )
    target_signatures = Counter(event_signature(event) for event in target)

    matches: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    for event in source:
        ical_uid = event.get("iCalUID")
        by_ical_uid = bool(ical_uid and str(ical_uid) in target_ical_uids)
        by_signature = event_signature(event) in target_signatures
        match_count = max(
            target_ical_uids[str(ical_uid)] if by_ical_uid else 0,
            target_signatures[event_signature(event)] if by_signature else 0,
        )
        record = {
            "matchedBy": "iCalUID" if by_ical_uid else "summary_start_location" if by_signature else None,
            "targetMatchCount": match_count,
            "ambiguous": match_count > 1,
            "event": short_event(event),
        }
        if by_ical_uid or by_signature:
            matches.append(record)
        else:
            unmatched.append(record)

    return {
        "source_count": len(source),
        "target_count": len(target),
        "matched_count": len(matches),
        "unmatched_count": len(unmatched),
        "matches": matches,
        "unmatched": unmatched,
    }


def print_tsv(preview: dict[str, Any]) -> None:
    print("matched\tstart\tsummary\tlocation\tiCalUID")
    for record in preview["unmatched"]:
        event = record["event"]
        print(
            "\t".join(
                [
                    "false",
                    event_start_display(event),
                    str(event.get("summary") or ""),
                    str(event.get("location") or ""),
                    str(event.get("iCalUID") or ""),
                ]
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preview source calendar events not already present in a target events.list JSON export."
    )
    parser.add_argument("--source", required=True, help="Source events JSON from gws calendar events list.")
    parser.add_argument("--target", required=True, help="Target events JSON from gws calendar events list.")
    parser.add_argument("--format", choices=["json", "tsv"], default="json")
    args = parser.parse_args()

    preview = build_preview(load_items(Path(args.source)), load_items(Path(args.target)))
    if args.format == "tsv":
        print_tsv(preview)
    else:
        json.dump(preview, sys.stdout, ensure_ascii=False, indent=2)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
