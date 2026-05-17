#!/usr/bin/env python3

import argparse
import json
import os
import plistlib
import sqlite3
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_DB = (
    Path.home()
    / "Library"
    / "Group Containers"
    / "group.com.apple.calendar"
    / "Calendar.sqlitedb"
)

STORE_TYPES = {
    0: "local/default",
    2: "caldav/account",
    4: "subscribed",
    5: "other/system",
    6: "reminders",
}


def run_command(command: list[str]) -> str | None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout


def load_ical_defaults() -> dict[str, Any]:
    output = run_command(["defaults", "export", "com.apple.iCal", "-"])
    if not output:
        return {}
    try:
        return plistlib.loads(output.encode())
    except Exception:
        return {}


def load_writable_names() -> dict[str, list[bool]]:
    script = [
        'tell application "Calendar"',
        "set rows to {}",
        "repeat with c in calendars",
        "set end of rows to ((name of c as text) & tab & (writable of c as text))",
        "end repeat",
        "set AppleScript's text item delimiters to linefeed",
        "return rows as text",
        "end tell",
    ]
    command: list[str] = ["osascript"]
    for line in script:
        command.extend(["-e", line])
    output = run_command(command)
    writable: dict[str, list[bool]] = {}
    if not output:
        return writable
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            name, value = line.rsplit("\t", 1)
        except ValueError:
            continue
        writable.setdefault(name, []).append(value.lower() == "true")
    return writable


def query_calendars(db_path: Path) -> list[dict[str, Any]]:
    if not db_path.exists():
        raise SystemExit(f"Calendar database not found: {db_path}")

    uri = f"file:{db_path}?mode=ro"
    query = """
        select
            c.ROWID as calendar_rowid,
            c.UUID as calendar_uuid,
            c.title as calendar_title,
            c.external_id as calendar_external_id,
            c.type as calendar_type,
            c.self_identity_email,
            c.owner_identity_email,
            c.shared_owner_address,
            c.subcal_url,
            s.ROWID as store_rowid,
            s.name as store_name,
            s.owner_name as store_owner,
            s.type as store_type,
            s.external_id as store_external_id,
            s.persistent_id as store_persistent_id
        from Calendar c
        left join Store s on c.store_id = s.ROWID
        order by s.name, c.display_order, c.title
    """
    with sqlite3.connect(uri, uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(row) for row in conn.execute(query)]
    for row in rows:
        row["store_type_label"] = STORE_TYPES.get(row.get("store_type"), "unknown")
    return rows


def build_report(db_path: Path) -> dict[str, Any]:
    calendars = query_calendars(db_path)
    writable_names = load_writable_names()
    defaults = load_ical_defaults()

    by_uuid = {row["calendar_uuid"]: row for row in calendars if row.get("calendar_uuid")}
    default_uuid = defaults.get("defaultCalendarID")
    default_calendar = by_uuid.get(default_uuid) if default_uuid else None

    for row in calendars:
        values = writable_names.get(row["calendar_title"], [])
        if not values:
            row["applescript_writable_by_name"] = None
        elif len(values) == 1:
            row["applescript_writable_by_name"] = values[0]
        else:
            row["applescript_writable_by_name"] = "ambiguous"

    counts = Counter(row["calendar_title"] for row in calendars)
    duplicates = sorted(name for name, count in counts.items() if count > 1)

    return {
        "database": str(db_path),
        "default_policy": defaults.get("CalDefaultCalendar"),
        "default_calendar_id": default_uuid,
        "default_calendar": default_calendar,
        "duplicate_display_names": duplicates,
        "calendars": calendars,
    }


def print_text(report: dict[str, Any]) -> None:
    print(f"Database: {report['database']}")
    print(f"Default policy: {report.get('default_policy') or '(unknown)'}")
    default_calendar = report.get("default_calendar")
    if default_calendar:
        print(
            "Default calendar: "
            f"{default_calendar['calendar_title']} "
            f"[store={default_calendar.get('store_name') or ''}, "
            f"uuid={default_calendar.get('calendar_uuid') or ''}]"
        )
    elif report.get("default_calendar_id"):
        print(f"Default calendar UUID: {report['default_calendar_id']} (not found)")
    else:
        print("Default calendar: (unknown)")

    duplicates = report.get("duplicate_display_names") or []
    if duplicates:
        print("Duplicate display names: " + ", ".join(duplicates))
    else:
        print("Duplicate display names: none")

    print()
    print(
        "Calendar\tStore\tStore type\tStore owner\tSelf identity\tOwner identity\tWritable by name\tUUID"
    )
    for row in report["calendars"]:
        values = [
            row.get("calendar_title") or "",
            row.get("store_name") or "",
            row.get("store_type_label") or "",
            row.get("store_owner") or "",
            row.get("self_identity_email") or "",
            row.get("owner_identity_email") or "",
            str(row.get("applescript_writable_by_name")),
            row.get("calendar_uuid") or "",
        ]
        print("\t".join(values))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only audit of macOS Calendar.app sources and default calendar."
    )
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Calendar.sqlitedb path.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    db_path = Path(os.path.expanduser(args.db)).resolve()
    report = build_report(db_path)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    else:
        print_text(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
