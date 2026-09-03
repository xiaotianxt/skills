#!/usr/bin/env python3

import argparse
import datetime as dt
import subprocess
import sys


MONTH_NAMES = {
    1: "january",
    2: "february",
    3: "march",
    4: "april",
    5: "may",
    6: "june",
    7: "july",
    8: "august",
    9: "september",
    10: "october",
    11: "november",
    12: "december",
}


def parse_local_timestamp(value: str) -> dt.datetime:
    try:
        return dt.datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise SystemExit(f"Invalid timestamp '{value}'. Use 'YYYY-MM-DD HH:MM'.") from exc


def run_osascript(lines: list[str], args: list[str] | None = None) -> str:
    command = ["osascript"]
    for line in lines:
        command.extend(["-e", line])
    if args:
        command.extend(args)

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "osascript failed"
        raise SystemExit(message)
    return result.stdout.strip()


def applescript_date(var_name: str, value: dt.datetime) -> list[str]:
    return [
        f"set {var_name} to (current date)",
        f"set year of {var_name} to {value.year}",
        f"set month of {var_name} to {MONTH_NAMES[value.month]}",
        f"set day of {var_name} to {value.day}",
        f"set time of {var_name} to ({value.hour} * hours + {value.minute} * minutes + {value.second})",
    ]


def cmd_list_calendars(_: argparse.Namespace) -> int:
    output = run_osascript(
        [
            'tell application "Calendar"',
            "set calendarNames to name of every calendar",
            "set AppleScript's text item delimiters to linefeed",
            "return calendarNames as text",
            "end tell",
        ]
    )
    if output:
        print(output)
    return 0


def cmd_create_event(args: argparse.Namespace) -> int:
    start = parse_local_timestamp(args.start)
    end = parse_local_timestamp(args.end)
    if end <= start:
        raise SystemExit("--end must be later than --start.")

    output = run_osascript(
        [
            "on run argv",
            "set calendarName to item 1 of argv",
            "set eventTitle to item 2 of argv",
            "set eventLocation to item 3 of argv",
            "set eventNotes to item 4 of argv",
            *applescript_date("startDate", start),
            *applescript_date("endDate", end),
            'tell application "Calendar"',
            "set matchingCalendars to every calendar whose name is calendarName",
            'if (count of matchingCalendars) is 0 then error "Calendar not found: " & calendarName',
            "set targetCalendar to first item of matchingCalendars",
            "tell targetCalendar",
            "set newEvent to make new event with properties {summary:eventTitle, start date:startDate, end date:endDate, location:eventLocation, description:eventNotes}",
            'return (summary of newEvent as text) & " | " & (start date of newEvent as text) & " | " & (end date of newEvent as text)',
            "end tell",
            "end tell",
            "end run",
        ],
        [args.calendar, args.title, args.location or "", args.notes or ""],
    )
    print(output)
    return 0


def cmd_verify_event(args: argparse.Namespace) -> int:
    start = parse_local_timestamp(args.start)
    output = run_osascript(
        [
            "on run argv",
            "set calendarName to item 1 of argv",
            "set eventTitle to item 2 of argv",
            *applescript_date("targetStart", start),
            'tell application "Calendar"',
            "set matchingCalendars to every calendar whose name is calendarName",
            'if (count of matchingCalendars) is 0 then error "Calendar not found: " & calendarName',
            "set targetCalendar to first item of matchingCalendars",
            "tell targetCalendar",
            "set matchingEvents to every event whose summary is eventTitle and start date is targetStart",
            'if (count of matchingEvents) is 0 then error "Event not found"',
            "set foundEvent to first item of matchingEvents",
            'return (summary of foundEvent as text) & " | " & (start date of foundEvent as text) & " | " & (end date of foundEvent as text) & " | " & (location of foundEvent as text)',
            "end tell",
            "end tell",
            "end run",
        ],
        [args.calendar, args.title],
    )
    print(output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List, create, and verify events in macOS Calendar.app."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-calendars", help="Print all calendar names.")
    list_parser.set_defaults(func=cmd_list_calendars)

    create_parser = subparsers.add_parser("create-event", help="Create a calendar event.")
    create_parser.add_argument("--calendar", required=True, help="Target calendar name.")
    create_parser.add_argument("--title", required=True, help="Event title.")
    create_parser.add_argument("--start", required=True, help="Local start time in 'YYYY-MM-DD HH:MM'.")
    create_parser.add_argument("--end", required=True, help="Local end time in 'YYYY-MM-DD HH:MM'.")
    create_parser.add_argument("--location", default="", help="Event location or meeting URL.")
    create_parser.add_argument("--notes", default="", help="Event notes.")
    create_parser.set_defaults(func=cmd_create_event)

    verify_parser = subparsers.add_parser("verify-event", help="Verify an event exists.")
    verify_parser.add_argument("--calendar", required=True, help="Target calendar name.")
    verify_parser.add_argument("--title", required=True, help="Event title.")
    verify_parser.add_argument("--start", required=True, help="Local start time in 'YYYY-MM-DD HH:MM'.")
    verify_parser.set_defaults(func=cmd_verify_event)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
