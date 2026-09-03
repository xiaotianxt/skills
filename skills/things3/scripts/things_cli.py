#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any


APP_BUNDLE_ID = os.environ.get("THINGS_APP_BUNDLE_ID", "com.culturedcode.ThingsMac")
SKILL_DATA_DIR = Path(os.environ.get("SKILL_DATA_DIR", Path.home() / ".codex" / "skills-data" / "things3"))
ENV_FILE = SKILL_DATA_DIR / ".env"


def encode_url(command: str, params: dict[str, Any] | None = None) -> str:
    base = f"things:///{command}"
    if not params:
        return base

    encoded: list[str] = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        elif isinstance(value, list):
            value = ",".join(str(item) for item in value)
        encoded.append(f"{key}={urllib.parse.quote(str(value), safe='')}")
    return base + "?" + "&".join(encoded)


def execute(url: str, dry_run: bool) -> None:
    if dry_run:
        print(url)
        return

    subprocess.run(["open", "-b", APP_BUNDLE_ID, url], check=True)
    print(url)


def split_csv(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    items: list[str] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                items.append(part)
    return items or None


def read_json_payload(args: argparse.Namespace) -> str:
    if args.data:
        return args.data
    if args.data_file:
        if args.data_file == "-":
            return sys.stdin.read()
        return Path(args.data_file).read_text(encoding="utf-8")
    raise SystemExit("json requires --data or --data-file")


def json_requires_token(payload: Any) -> bool:
    if isinstance(payload, dict):
        operation = payload.get("operation")
        if operation == "update":
            return True
        attributes = payload.get("attributes")
        if json_requires_token(attributes):
            return True
        items = payload.get("items")
        if json_requires_token(items):
            return True
        return False
    if isinstance(payload, list):
        return any(json_requires_token(item) for item in payload)
    return False


def validate_json_payload(payload: Any) -> None:
    if not isinstance(payload, list):
        raise SystemExit(
            "Things json requires a top-level JSON array of to-do/project objects. "
            "Use [{\"type\":\"project\",\"attributes\":{...}}], not {\"items\":[...]}.",
        )
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise SystemExit(f"Things json item {index} must be an object.")
        item_type = item.get("type")
        if item_type not in {"to-do", "project"}:
            raise SystemExit(f"Things json item {index} has unsupported top-level type: {item_type!r}.")
        attributes = item.get("attributes")
        if not isinstance(attributes, dict):
            raise SystemExit(f"Things json item {index} must include an attributes object.")


def env_token(cli_token: str | None = None, required: bool = False) -> str | None:
    token = cli_token or os.environ.get("THINGS_AUTH_TOKEN") or None
    if required and not token:
        raise SystemExit("Missing Things auth token. Set THINGS_AUTH_TOKEN, use set-token, or pass --auth-token.")
    return token


def quote_env_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def write_env_key(key: str, value: str) -> None:
    SKILL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()

    replacement = f'{key}="{quote_env_value(value)}"'
    updated = False
    out_lines: list[str] = []
    for line in lines:
        if line.startswith(f"{key}="):
            out_lines.append(replacement)
            updated = True
        else:
            out_lines.append(line)
    if not updated:
        out_lines.append(replacement)
    ENV_FILE.write_text("\n".join(out_lines).rstrip() + "\n", encoding="utf-8")


def common_write_flags(parser: argparse.ArgumentParser, include_list: bool = True, include_heading: bool = False) -> None:
    parser.add_argument("--notes")
    parser.add_argument("--when")
    parser.add_argument("--deadline")
    parser.add_argument("--tag", action="append")
    parser.add_argument("--completed", action="store_true")
    parser.add_argument("--canceled", action="store_true")
    parser.add_argument("--reveal", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    if include_list:
        parser.add_argument("--list-title")
        parser.add_argument("--list-id")
    if include_heading:
        parser.add_argument("--heading")
        parser.add_argument("--heading-id")


def cmd_add_todo(args: argparse.Namespace) -> None:
    if not args.title and not args.titles:
        raise SystemExit("add-todo requires --title or --titles")
    params = {
        "title": args.title,
        "titles": "\n".join(args.titles) if args.titles else None,
        "notes": args.notes,
        "when": args.when,
        "deadline": args.deadline,
        "tags": split_csv(args.tag),
        "checklist-items": "\n".join(args.checklist) if args.checklist else None,
        "list": args.list_title,
        "list-id": args.list_id,
        "heading": args.heading,
        "heading-id": args.heading_id,
        "completed": True if args.completed else None,
        "canceled": True if args.canceled else None,
        "show-quick-entry": True if args.show_quick_entry else None,
        "reveal": True if args.reveal else None,
    }
    execute(encode_url("add", params), args.dry_run)


def cmd_add_project(args: argparse.Namespace) -> None:
    params = {
        "title": args.title,
        "notes": args.notes,
        "when": args.when,
        "deadline": args.deadline,
        "tags": split_csv(args.tag),
        "area": args.area_title,
        "area-id": args.area_id,
        "to-dos": "\n".join(args.todo) if args.todo else None,
        "completed": True if args.completed else None,
        "canceled": True if args.canceled else None,
        "reveal": True if args.reveal else None,
    }
    execute(encode_url("add-project", params), args.dry_run)


def cmd_update_todo(args: argparse.Namespace) -> None:
    params = {
        "id": args.id,
        "auth-token": env_token(args.auth_token, required=True),
        "title": args.title,
        "notes": args.notes,
        "prepend-notes": args.prepend_notes,
        "append-notes": args.append_notes,
        "when": args.when,
        "deadline": args.deadline,
        "tags": split_csv(args.tag),
        "add-tags": split_csv(args.add_tag),
        "checklist-items": "\n".join(args.checklist) if args.checklist else None,
        "prepend-checklist-items": "\n".join(args.prepend_checklist) if args.prepend_checklist else None,
        "append-checklist-items": "\n".join(args.append_checklist) if args.append_checklist else None,
        "list": args.list_title,
        "list-id": args.list_id,
        "heading": args.heading,
        "heading-id": args.heading_id,
        "completed": args.completed if args.completed else None,
        "canceled": args.canceled if args.canceled else None,
        "reveal": True if args.reveal else None,
        "duplicate": True if args.duplicate else None,
    }
    execute(encode_url("update", params), args.dry_run)


def cmd_update_project(args: argparse.Namespace) -> None:
    params = {
        "id": args.id,
        "auth-token": env_token(args.auth_token, required=True),
        "title": args.title,
        "notes": args.notes,
        "prepend-notes": args.prepend_notes,
        "append-notes": args.append_notes,
        "when": args.when,
        "deadline": args.deadline,
        "tags": split_csv(args.tag),
        "add-tags": split_csv(args.add_tag),
        "area": args.area_title,
        "area-id": args.area_id,
        "completed": args.completed if args.completed else None,
        "canceled": args.canceled if args.canceled else None,
        "reveal": True if args.reveal else None,
        "duplicate": True if args.duplicate else None,
    }
    execute(encode_url("update-project", params), args.dry_run)


def cmd_show(args: argparse.Namespace) -> None:
    if not args.id and not args.query:
        raise SystemExit("show requires --id or --query")
    params = {
        "id": args.id,
        "query": args.query,
        "filter": split_csv(args.filter_tag),
    }
    execute(encode_url("show", params), args.dry_run)


def cmd_search(args: argparse.Namespace) -> None:
    params = {"query": args.query}
    execute(encode_url("search", params), args.dry_run)


def cmd_version(args: argparse.Namespace) -> None:
    execute(encode_url("version"), args.dry_run)


def cmd_json(args: argparse.Namespace) -> None:
    data = read_json_payload(args)
    parsed = json.loads(data)
    validate_json_payload(parsed)
    token_required = json_requires_token(parsed)
    params = {
        "data": json.dumps(parsed, separators=(",", ":")),
        "reveal": True if args.reveal else None,
        "auth-token": env_token(args.auth_token, required=token_required),
    }
    execute(encode_url("json", params), args.dry_run)


def cmd_set_token(args: argparse.Namespace) -> None:
    write_env_key("THINGS_AUTH_TOKEN", args.token)
    print(str(ENV_FILE))


def cmd_print_config(_: argparse.Namespace) -> None:
    print(f"SKILL_DATA_DIR={SKILL_DATA_DIR}")
    print(f"ENV_FILE={ENV_FILE}")
    print(f"THINGS_APP_BUNDLE_ID={APP_BUNDLE_ID}")
    token = os.environ.get("THINGS_AUTH_TOKEN", "")
    if token:
        print(f"THINGS_AUTH_TOKEN_SET=yes length={len(token)}")
    else:
        print("THINGS_AUTH_TOKEN_SET=no")


def run_osascript(script: str, argv: list[str]) -> str:
    result = subprocess.run(
        ["osascript", "-", *argv],
        check=True,
        input=script,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def format_table(rows: list[dict[str, str]], columns: list[tuple[str, str]]) -> str:
    widths: dict[str, int] = {}
    for key, label in columns:
        widths[key] = len(label)
    for row in rows:
        for key, _ in columns:
            widths[key] = max(widths[key], len(row.get(key, "")))

    lines: list[str] = []
    header = "  ".join(label.ljust(widths[key]) for key, label in columns)
    divider = "  ".join("-" * widths[key] for key, _ in columns)
    lines.append(header)
    lines.append(divider)
    for row in rows:
        lines.append("  ".join(row.get(key, "").ljust(widths[key]) for key, _ in columns))
    return "\n".join(lines)


def cmd_find_open_todos(args: argparse.Namespace) -> None:
    script = r"""
on pad2(n)
    if n < 10 then
        return "0" & (n as text)
    end if
    return n as text
end pad2

on iso_date(d)
    if d is missing value then
        return ""
    end if
    set y to year of d as integer
    set m to month of d as integer
    set day_num to day of d as integer
    set hh to hours of d as integer
    set mm to minutes of d as integer
    set ss to seconds of d as integer
    return (y as text) & "-" & my pad2(m) & "-" & my pad2(day_num) & "T" & my pad2(hh) & ":" & my pad2(mm) & ":" & my pad2(ss)
end iso_date

on safe_project_name(t)
    try
        set parent_project to project of t
        if parent_project is missing value then
            return ""
        end if
        return name of parent_project
    on error
        return ""
    end try
end safe_project_name

on run argv
    set project_name to item 1 of argv
    set title_filter to item 2 of argv
    set field_sep to character id 31
    tell application "Things3"
        if project_name is not "" then
            try
                set xs to to dos of project project_name
            on error
                set xs to {}
            end try
        else
            set xs to to dos
        end if

        set rows to {}
        repeat with t in xs
            set title_text to name of t
            if title_filter is "" or title_text contains title_filter then
                set end of rows to (id of t) & field_sep & title_text & field_sep & ((status of t) as string) & field_sep & my iso_date(activation date of t) & field_sep & my iso_date(due date of t) & field_sep & my safe_project_name(t)
            end if
        end repeat
    end tell

    set AppleScript's text item delimiters to linefeed
    return rows as text
end run
"""
    output = run_osascript(script, [args.project or "", args.title_contains or ""])
    rows: list[dict[str, str]] = []
    if output:
        for line in output.splitlines():
            item_id, title, status, activation_date, due_date, project = (line.split("\x1f") + ["", "", "", "", "", ""])[:6]
            project_name = project or args.project or ""
            rows.append(
                {
                    "id": item_id,
                    "title": title,
                    "status": status,
                    "activation_date": activation_date,
                    "due_date": due_date,
                    "project": project_name,
                }
            )

    rows.sort(key=lambda row: (row["activation_date"] or "9999-99-99T99:99:99", row["due_date"] or "9999-99-99T99:99:99", row["title"]))

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    if not rows:
        print("No matching open to-dos.")
        return

    print(
        format_table(
            rows,
            [
                ("id", "ID"),
                ("title", "Title"),
                ("status", "Status"),
                ("activation_date", "Activation"),
                ("due_date", "Due"),
                ("project", "Project"),
            ],
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Things 3 URL-scheme CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_todo = subparsers.add_parser("add-todo", help="Create a Things to-do")
    add_todo.add_argument("--title")
    add_todo.add_argument("--titles", action="append")
    add_todo.add_argument("--checklist", action="append")
    add_todo.add_argument("--show-quick-entry", action="store_true")
    common_write_flags(add_todo, include_list=True, include_heading=True)
    add_todo.set_defaults(func=cmd_add_todo)

    add_project = subparsers.add_parser("add-project", help="Create a Things project")
    add_project.add_argument("--title", required=True)
    add_project.add_argument("--todo", action="append")
    add_project.add_argument("--area-title")
    add_project.add_argument("--area-id")
    common_write_flags(add_project, include_list=False, include_heading=False)
    add_project.set_defaults(func=cmd_add_project)

    update_todo = subparsers.add_parser("update-todo", help="Update a Things to-do")
    update_todo.add_argument("--id", required=True)
    update_todo.add_argument("--auth-token")
    update_todo.add_argument("--title")
    update_todo.add_argument("--prepend-notes")
    update_todo.add_argument("--append-notes")
    update_todo.add_argument("--add-tag", action="append")
    update_todo.add_argument("--checklist", action="append")
    update_todo.add_argument("--prepend-checklist", action="append")
    update_todo.add_argument("--append-checklist", action="append")
    update_todo.add_argument("--duplicate", action="store_true")
    common_write_flags(update_todo, include_list=True, include_heading=True)
    update_todo.set_defaults(func=cmd_update_todo)

    update_project = subparsers.add_parser("update-project", help="Update a Things project")
    update_project.add_argument("--id", required=True)
    update_project.add_argument("--auth-token")
    update_project.add_argument("--title")
    update_project.add_argument("--prepend-notes")
    update_project.add_argument("--append-notes")
    update_project.add_argument("--add-tag", action="append")
    update_project.add_argument("--area-title")
    update_project.add_argument("--area-id")
    update_project.add_argument("--duplicate", action="store_true")
    common_write_flags(update_project, include_list=False, include_heading=False)
    update_project.set_defaults(func=cmd_update_project)

    show = subparsers.add_parser("show", help="Open a built-in list, project, tag, or item")
    show.add_argument("--id")
    show.add_argument("--query")
    show.add_argument("--filter-tag", action="append")
    show.add_argument("--dry-run", action="store_true")
    show.set_defaults(func=cmd_show)

    search = subparsers.add_parser("search", help="Open Things search")
    search.add_argument("query", nargs="?", default="")
    search.add_argument("--dry-run", action="store_true")
    search.set_defaults(func=cmd_search)

    find_open_todos = subparsers.add_parser("find-open-todos", help="List matching open to-dos with ids and dates")
    find_open_todos.add_argument("--project")
    find_open_todos.add_argument("--title-contains")
    find_open_todos.add_argument("--json", action="store_true")
    find_open_todos.set_defaults(func=cmd_find_open_todos)

    version = subparsers.add_parser("version", help="Open the Things version command")
    version.add_argument("--dry-run", action="store_true")
    version.set_defaults(func=cmd_version)

    json_cmd = subparsers.add_parser("json", help="Send a JSON payload to Things")
    json_cmd.add_argument("--data")
    json_cmd.add_argument("--data-file")
    json_cmd.add_argument("--auth-token")
    json_cmd.add_argument("--reveal", action="store_true")
    json_cmd.add_argument("--dry-run", action="store_true")
    json_cmd.set_defaults(func=cmd_json)

    set_token = subparsers.add_parser("set-token", help="Persist THINGS_AUTH_TOKEN into the skill env file")
    set_token.add_argument("--token", required=True)
    set_token.set_defaults(func=cmd_set_token)

    print_config = subparsers.add_parser("print-config", help="Show env-backed config paths")
    print_config.set_defaults(func=cmd_print_config)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
