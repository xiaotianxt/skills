#!/usr/bin/env python3
"""Initialize a source-grounded learning workspace."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path


def slugify(value: str) -> str:
    out = []
    last_dash = False
    for ch in value.lower():
        if ch.isalnum():
            out.append(ch)
            last_dash = False
        elif not last_dash:
            out.append("-")
            last_dash = True
    return "".join(out).strip("-") or "learning-topic"


def render(template: str, topic: str, goal: str) -> str:
    return (
        template.replace("{TOPIC}", topic)
        .replace("{GOAL}", goal)
        .replace("{DATE}", date.today().isoformat())
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic", help="Human-readable topic name")
    parser.add_argument("--path", default=".", help="Parent directory for workspace")
    parser.add_argument("--name", help="Workspace folder name; defaults to topic slug")
    parser.add_argument("--goal", default="Build practical, source-grounded mastery.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing template files")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    assets = skill_dir / "assets"
    root = Path(args.path).expanduser().resolve() / (args.name or slugify(args.topic))
    root.mkdir(parents=True, exist_ok=True)

    for subdir in ["materials", "notes", "cases", "outputs"]:
        (root / subdir).mkdir(exist_ok=True)

    files = {
        "AGENTS.md": assets / "AGENTS.template.md",
        "tasklog.typ": assets / "tasklog.template.typ",
        "errorlog.typ": assets / "errorlog.template.typ",
        "workbook.typ": assets / "workbook.template.typ",
        "materials/source-index.md": assets / "source-index.template.md",
        "notes/reading-sequence.md": assets / "reading-sequence.template.md",
    }

    for rel, template_path in files.items():
        target = root / rel
        if target.exists() and not args.force:
            continue
        text = render(template_path.read_text(), args.topic, args.goal)
        target.write_text(text)

    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
