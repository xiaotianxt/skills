#!/usr/bin/env python3
import argparse
import asyncio
import getpass
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from telethon import TelegramClient, functions, types
from telethon.errors import SessionPasswordNeededError


DEFAULT_SESSION = "~/.local/share/codex-telegram/telegram"
DEFAULT_HISTORY_DB = "~/.local/share/codex-telegram/history.sqlite3"
DEFAULT_TIMEZONE = os.environ.get("TZ") or "America/Los_Angeles"


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"missing required env: {name}")
    return value


def clean(text: str, limit: int = 700) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) > limit:
        return text[: limit - 1] + "..."
    return text


def utc_text(dt) -> str:
    if not dt:
        return ""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_boundary(value: str, tz_name: str, *, until: bool = False) -> datetime:
    tz = ZoneInfo(tz_name)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        day = datetime.strptime(value, "%Y-%m-%d").date()
        local = datetime.combine(day, time.min, tzinfo=tz)
        if until:
            local += timedelta(days=1)
        return local.astimezone(timezone.utc)

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(timezone.utc)


def date_bounds(args) -> tuple[datetime, datetime]:
    if getattr(args, "day", None):
        since = parse_boundary(args.day, args.timezone)
        until = parse_boundary(args.day, args.timezone, until=True)
        return since, until

    if not args.since:
        raise SystemExit("missing --since")
    since = parse_boundary(args.since, args.timezone)
    until_value = args.until
    if until_value:
        until = parse_boundary(until_value, args.timezone, until=True)
    else:
        until = datetime.now(timezone.utc)
    if until <= since:
        raise SystemExit("--until must be after --since")
    return since, until


def today_bounds(tz_name: str) -> tuple[str, datetime, datetime]:
    tz = ZoneInfo(tz_name)
    day = datetime.now(tz).date().isoformat()
    since = parse_boundary(day, tz_name)
    until = parse_boundary(day, tz_name, until=True)
    return day, since, until


def display_time(utc_value: str, tz_name: str) -> str:
    if not utc_value:
        return ""
    dt = datetime.fromisoformat(utc_value.replace("Z", "+00:00"))
    return dt.astimezone(ZoneInfo(tz_name)).strftime("%Y-%m-%d %H:%M:%S %Z")


def display_username(entity) -> str:
    username = getattr(entity, "username", None)
    return f"@{username}" if username else ""


def normalized_chat_key(value: str) -> str:
    value = value.strip()
    if value.startswith("@"):
        return value.lower()
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{3,}", value):
        return f"@{value.lower()}"
    return value.lower()


def entity_chat_key(entity, fallback: str) -> str:
    username = getattr(entity, "username", None)
    if username:
        return f"@{username.lower()}"
    entity_id = getattr(entity, "id", None)
    if entity_id is not None:
        return f"{entity_kind(entity)}:{entity_id}"
    return normalized_chat_key(fallback)


def entity_kind(entity) -> str:
    if isinstance(entity, types.Channel):
        if getattr(entity, "megagroup", False):
            return "megagroup"
        if getattr(entity, "broadcast", False):
            return "channel"
        return "channel-like"
    if isinstance(entity, types.Chat):
        return "chat"
    if isinstance(entity, types.User):
        return "bot" if getattr(entity, "bot", False) else "user"
    return type(entity).__name__


def session_base(path: str) -> str:
    expanded = Path(path).expanduser()
    expanded.parent.mkdir(parents=True, exist_ok=True)
    return str(expanded)


def session_file(path: str) -> Path:
    expanded = Path(path).expanduser()
    if expanded.suffix == ".session":
        return expanded
    return Path(str(expanded) + ".session")


def history_db_file(path: str, *, create_parent: bool = True) -> Path:
    expanded = Path(path).expanduser()
    if create_parent:
        expanded.parent.mkdir(parents=True, exist_ok=True)
    return expanded


def connect_history_db(path: str, *, readonly: bool = False) -> sqlite3.Connection:
    db_path = history_db_file(path, create_parent=not readonly)
    if readonly:
        conn = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_history_schema(conn)
    return conn


def ensure_history_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS chats (
            chat_key TEXT PRIMARY KEY,
            peer_id INTEGER,
            title TEXT,
            username TEXT,
            kind TEXT,
            last_sync_utc TEXT
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            chat_key TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            date_utc TEXT NOT NULL,
            sender_id INTEGER,
            text TEXT NOT NULL,
            views INTEGER,
            forwards INTEGER,
            reply_to_msg_id INTEGER,
            grouped_id INTEGER,
            edit_date_utc TEXT,
            UNIQUE(chat_key, message_id),
            FOREIGN KEY(chat_key) REFERENCES chats(chat_key) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS messages_chat_date_idx
            ON messages(chat_key, date_utc);
        CREATE INDEX IF NOT EXISTS messages_date_idx
            ON messages(date_utc);
        CREATE INDEX IF NOT EXISTS messages_sender_idx
            ON messages(sender_id);

        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
            USING fts5(text, content='messages', content_rowid='id');

        CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
            INSERT INTO messages_fts(rowid, text) VALUES (new.id, new.text);
        END;
        CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
            INSERT INTO messages_fts(messages_fts, rowid, text)
            VALUES('delete', old.id, old.text);
        END;
        CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
            INSERT INTO messages_fts(messages_fts, rowid, text)
            VALUES('delete', old.id, old.text);
            INSERT INTO messages_fts(rowid, text) VALUES (new.id, new.text);
        END;
        """
    )


def make_client(args) -> TelegramClient:
    api_id = int(require_env("TELEGRAM_API_ID"))
    api_hash = require_env("TELEGRAM_API_HASH")
    return TelegramClient(session_base(args.session), api_id, api_hash)


async def require_authorized_client(args) -> TelegramClient:
    client = make_client(args)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        print("authorized=false", file=sys.stderr)
        raise SystemExit(3)
    return client


def chat_row(entity, chat_key: str) -> dict:
    return {
        "chat_key": chat_key,
        "peer_id": getattr(entity, "id", None),
        "title": getattr(entity, "title", None)
        or " ".join(
            part
            for part in [getattr(entity, "first_name", None), getattr(entity, "last_name", None)]
            if part
        ),
        "username": getattr(entity, "username", None),
        "kind": entity_kind(entity),
        "last_sync_utc": utc_text(datetime.now(timezone.utc)),
    }


def message_row(chat_key: str, msg) -> dict:
    reply_to = getattr(msg, "reply_to", None)
    return {
        "chat_key": chat_key,
        "message_id": msg.id,
        "date_utc": utc_text(msg.date),
        "sender_id": getattr(msg, "sender_id", None),
        "text": msg.raw_text or "",
        "views": getattr(msg, "views", None),
        "forwards": getattr(msg, "forwards", None),
        "reply_to_msg_id": getattr(reply_to, "reply_to_msg_id", None),
        "grouped_id": getattr(msg, "grouped_id", None),
        "edit_date_utc": utc_text(getattr(msg, "edit_date", None)),
    }


async def fetch_message_rows(client: TelegramClient, entity, chat_key: str, since: datetime, until: datetime, limit: int | None):
    rows = []
    async for msg in client.iter_messages(entity, limit=limit, offset_date=until):
        if not msg.date:
            continue
        msg_dt = msg.date.astimezone(timezone.utc)
        if msg_dt < since:
            break
        if msg_dt >= until:
            continue
        rows.append(message_row(chat_key, msg))
    rows.reverse()
    return rows


def upsert_chat(conn: sqlite3.Connection, row: dict) -> None:
    conn.execute(
        """
        INSERT INTO chats(chat_key, peer_id, title, username, kind, last_sync_utc)
        VALUES(:chat_key, :peer_id, :title, :username, :kind, :last_sync_utc)
        ON CONFLICT(chat_key) DO UPDATE SET
            peer_id=excluded.peer_id,
            title=excluded.title,
            username=excluded.username,
            kind=excluded.kind,
            last_sync_utc=excluded.last_sync_utc
        """,
        row,
    )


def upsert_messages(conn: sqlite3.Connection, rows: list[dict]) -> tuple[int, int]:
    inserted = 0
    updated = 0
    for row in rows:
        existed = conn.execute(
            "SELECT 1 FROM messages WHERE chat_key = ? AND message_id = ?",
            (row["chat_key"], row["message_id"]),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO messages(
                chat_key, message_id, date_utc, sender_id, text, views, forwards,
                reply_to_msg_id, grouped_id, edit_date_utc
            )
            VALUES(
                :chat_key, :message_id, :date_utc, :sender_id, :text, :views,
                :forwards, :reply_to_msg_id, :grouped_id, :edit_date_utc
            )
            ON CONFLICT(chat_key, message_id) DO UPDATE SET
                date_utc=excluded.date_utc,
                sender_id=excluded.sender_id,
                text=excluded.text,
                views=excluded.views,
                forwards=excluded.forwards,
                reply_to_msg_id=excluded.reply_to_msg_id,
                grouped_id=excluded.grouped_id,
                edit_date_utc=excluded.edit_date_utc
            """,
            row,
        )
        if existed:
            updated += 1
        else:
            inserted += 1
    return inserted, updated


def query_history_rows(args):
    conn = connect_history_db(args.db, readonly=True)
    try:
        clauses = []
        params = []
        if args.entity:
            clauses.append("m.chat_key = ?")
            params.append(normalized_chat_key(args.entity))
        if getattr(args, "since", None):
            clauses.append("m.date_utc >= ?")
            params.append(utc_text(parse_boundary(args.since, args.timezone)))
        if getattr(args, "until", None):
            clauses.append("m.date_utc < ?")
            params.append(utc_text(parse_boundary(args.until, args.timezone, until=True)))

        match = getattr(args, "match", None)
        if match:
            from_sql = "messages m JOIN messages_fts f ON f.rowid = m.id"
            clauses.append("messages_fts MATCH ?")
            params.append(match)
        else:
            from_sql = "messages m"

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        limit = "" if args.limit is None else "LIMIT ?"
        if args.limit is not None:
            params.append(args.limit)
        return conn.execute(
            f"""
            SELECT m.chat_key, m.message_id, m.date_utc, m.sender_id, m.text,
                   m.views, m.forwards, m.reply_to_msg_id, m.grouped_id, m.edit_date_utc
            FROM {from_sql}
            {where}
            ORDER BY m.date_utc ASC, m.message_id ASC
            {limit}
            """,
            params,
        ).fetchall()
    finally:
        conn.close()


def print_history_rows(rows, args) -> None:
    if args.format == "jsonl":
        for row in rows:
            print(json.dumps(dict(row), ensure_ascii=False, separators=(",", ":")))
        return

    for row in rows:
        text = clean(row["text"], args.max_text)
        print(
            f"[{display_time(row['date_utc'], args.timezone)}] "
            f"id={row['message_id']} sender={row['sender_id']} text={text}"
        )


async def login(args) -> int:
    phone = args.phone or os.environ.get("TELEGRAM_PHONE")
    if not phone:
        raise SystemExit("missing phone: pass --phone or TELEGRAM_PHONE")

    client = make_client(args)
    await client.connect()
    try:
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"already_authorized user_id={me.id} username={display_username(me)}")
            print(f"session={session_file(args.session)}")
            return 0

        await client.send_code_request(phone)
        print("code_sent=true")

        code = args.code or os.environ.get("TELEGRAM_CODE")
        if not code:
            code = input("Telegram login code: ").strip()

        try:
            await client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            password = args.password or os.environ.get("TELEGRAM_PASSWORD")
            if not password:
                password = getpass.getpass("Telegram 2FA password: ")
            await client.sign_in(password=password)

        me = await client.get_me()
        print(f"authorized=true user_id={me.id} username={display_username(me)}")
        print(f"session={session_file(args.session)}")
        return 0
    finally:
        await client.disconnect()


async def verify(args) -> int:
    client = make_client(args)
    await client.connect()
    try:
        authorized = await client.is_user_authorized()
        print(f"authorized={authorized}")
        print(f"session={session_file(args.session)}")
        if authorized:
            me = await client.get_me()
            print(f"user_id={me.id} username={display_username(me)}")
        return 0 if authorized else 3
    finally:
        await client.disconnect()


async def search(args) -> int:
    client = await require_authorized_client(args)
    try:
        result = await client(functions.contacts.SearchRequest(q=args.query, limit=args.limit))
        for chat in result.chats:
            title = getattr(chat, "title", "")
            participants = getattr(chat, "participants_count", None)
            print(
                f"{title}\t{display_username(chat)}\t{entity_kind(chat)}"
                f"\tparticipants={participants}\tid={getattr(chat, 'id', '')}"
            )
        return 0
    finally:
        await client.disconnect()


async def dialogs(args) -> int:
    pattern = re.compile(args.match, re.I) if args.match else None
    client = await require_authorized_client(args)
    try:
        count = 0
        async for dialog in client.iter_dialogs(limit=args.limit):
            entity = dialog.entity
            title = dialog.name or ""
            username = getattr(entity, "username", "") or ""
            haystack = f"{title} {username}"
            if pattern and not pattern.search(haystack):
                continue
            count += 1
            print(
                f"{title}\t{display_username(entity)}\t{entity_kind(entity)}"
                f"\tid={getattr(entity, 'id', '')}\tunread={dialog.unread_count}"
            )
        if count == 0:
            print("no_dialogs_matched")
        return 0
    finally:
        await client.disconnect()


async def inspect(args) -> int:
    client = await require_authorized_client(args)
    try:
        entity = await client.get_entity(args.entity)
        title = getattr(entity, "title", None) or " ".join(
            part for part in [getattr(entity, "first_name", None), getattr(entity, "last_name", None)] if part
        )
        print(f"title={title}")
        print(f"username={display_username(entity)}")
        print(f"kind={entity_kind(entity)}")
        print(f"id={getattr(entity, 'id', '')}")

        if isinstance(entity, types.Channel):
            try:
                full = await client(functions.channels.GetFullChannelRequest(entity))
                full_chat = full.full_chat
                participants = getattr(full_chat, "participants_count", None)
                if participants is not None:
                    print(f"participants={participants}")
                about = clean(getattr(full_chat, "about", ""))
                if about:
                    print(f"about={about}")
                linked_chat_id = getattr(full_chat, "linked_chat_id", None)
                if linked_chat_id:
                    print(f"linked_chat_id={linked_chat_id}")
                    for chat in getattr(full, "chats", []):
                        if getattr(chat, "id", None) == linked_chat_id:
                            print(f"linked_chat_title={getattr(chat, 'title', '')}")
                            username = display_username(chat)
                            if username:
                                print(f"linked_chat_username={username}")
                            print(f"linked_chat_kind={entity_kind(chat)}")
                            break
            except Exception as exc:
                print(f"full_info_error={type(exc).__name__}: {exc}")

        print("recent_messages:")
        async for msg in client.iter_messages(entity, limit=args.limit):
            dt = msg.date.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ") if msg.date else ""
            reply_info = ""
            if getattr(msg, "replies", None):
                replies = msg.replies
                reply_info = (
                    f" replies={getattr(replies, 'replies', '')}"
                    f" comments={getattr(replies, 'comments', '')}"
                    f" channel_id={getattr(replies, 'channel_id', '')}"
                    f" max_id={getattr(replies, 'max_id', '')}"
                )
            print(
                f"- date={dt} id={msg.id} views={getattr(msg, 'views', None)}"
                f" forwards={getattr(msg, 'forwards', None)}{reply_info} text={clean(msg.raw_text)}"
            )
        return 0
    finally:
        await client.disconnect()


async def sync_history(args) -> int:
    since, until = date_bounds(args)
    client = await require_authorized_client(args)
    try:
        entity = await client.get_entity(args.entity)
        chat_key = entity_chat_key(entity, args.entity)
        rows = await fetch_message_rows(client, entity, chat_key, since, until, args.limit)
    finally:
        await client.disconnect()

    conn = connect_history_db(args.db)
    try:
        with conn:
            upsert_chat(conn, chat_row(entity, chat_key))
            inserted, updated = upsert_messages(conn, rows)
        print(
            f"synced chat_key={chat_key} fetched={len(rows)} inserted={inserted} "
            f"updated={updated} since={utc_text(since)} until={utc_text(until)} "
            f"db={history_db_file(args.db)}"
        )
        return 0
    finally:
        conn.close()


async def today(args) -> int:
    if not args.day:
        args.day, since, until = today_bounds(args.timezone)
    else:
        since, until = date_bounds(args)

    client = await require_authorized_client(args)
    try:
        entity = await client.get_entity(args.entity)
        chat_key = entity_chat_key(entity, args.entity)
        rows = await fetch_message_rows(client, entity, chat_key, since, until, args.limit)
    finally:
        await client.disconnect()

    conn = connect_history_db(args.db)
    try:
        with conn:
            upsert_chat(conn, chat_row(entity, chat_key))
            inserted, updated = upsert_messages(conn, rows)
        print(
            f"synced chat_key={chat_key} day={args.day} fetched={len(rows)} "
            f"inserted={inserted} updated={updated} db={history_db_file(args.db)}"
        )
    finally:
        conn.close()

    query_args = argparse.Namespace(
        db=args.db,
        entity=chat_key,
        since=args.day,
        until=args.day,
        timezone=args.timezone,
        match=args.match,
        limit=args.print_limit,
        format=args.format,
        max_text=args.max_text,
    )
    rows = query_history_rows(query_args)
    print_history_rows(rows, query_args)
    return 0


async def query_history(args) -> int:
    rows = query_history_rows(args)
    print_history_rows(rows, args)
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description="Create, verify, and use a local Telegram MTProto session.")
    parser.add_argument("--session", default=DEFAULT_SESSION, help=f"Telethon session base path. Default: {DEFAULT_SESSION}")
    parser.add_argument("--db", default=DEFAULT_HISTORY_DB, help=f"SQLite history database. Default: {DEFAULT_HISTORY_DB}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("login", help="Create or refresh the local Telegram session.")
    p.add_argument("--phone", help="Phone number in international format. Defaults to TELEGRAM_PHONE.")
    p.add_argument("--code", help="Login code. Defaults to TELEGRAM_CODE, otherwise prompts.")
    p.add_argument("--password", help="2FA password. Defaults to TELEGRAM_PASSWORD, otherwise prompts if needed.")
    p.set_defaults(func=login)

    p = sub.add_parser("verify", help="Check whether a session is authorized.")
    p.set_defaults(func=verify)

    p = sub.add_parser("search", help="Search public Telegram chats/channels.")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=search)

    p = sub.add_parser("dialogs", help="List joined dialogs, optionally filtered by regex.")
    p.add_argument("--match", help="Regex filter over title and username.")
    p.add_argument("--limit", type=int, default=None)
    p.set_defaults(func=dialogs)

    p = sub.add_parser("inspect", help="Resolve an entity and print recent message summaries.")
    p.add_argument("entity", help="Username, invite-resolved entity, or joined chat/channel.")
    p.add_argument("--limit", type=int, default=5)
    p.set_defaults(func=inspect)

    p = sub.add_parser("sync", help="Fetch date-bounded Telegram history into local SQLite.")
    p.add_argument("entity", help="Username, id, invite-resolved entity, or joined chat/channel.")
    p.add_argument("--since", required=True, help="Inclusive local date/datetime, e.g. 2026-05-08.")
    p.add_argument("--until", help="Exclusive local date/datetime. Date values mean the next midnight.")
    p.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    p.add_argument("--limit", type=int, default=None, help="Optional maximum messages to fetch from Telegram.")
    p.set_defaults(func=sync_history)

    p = sub.add_parser("today", help="Sync and print one local day's Telegram history.")
    p.add_argument("entity", help="Username, id, invite-resolved entity, or joined chat/channel.")
    p.add_argument("--day", help="Local day to read, e.g. 2026-05-08. Defaults to today.")
    p.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    p.add_argument("--limit", type=int, default=None, help="Optional maximum messages to fetch from Telegram.")
    p.add_argument("--print-limit", type=int, default=None, help="Optional maximum rows to print after syncing.")
    p.add_argument("--match", help="Optional FTS5 search expression over local message text.")
    p.add_argument("--format", choices=["text", "jsonl"], default="text")
    p.add_argument("--max-text", type=int, default=900)
    p.set_defaults(func=today)

    p = sub.add_parser("query", help="Read previously synced Telegram history from local SQLite.")
    p.add_argument("entity", nargs="?", help="Optional chat key or username.")
    p.add_argument("--since", help="Inclusive local date/datetime.")
    p.add_argument("--until", help="Exclusive local date/datetime. Date values mean the next midnight.")
    p.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    p.add_argument("--match", help="Optional FTS5 search expression over local message text.")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--format", choices=["text", "jsonl"], default="text")
    p.add_argument("--max-text", type=int, default=900)
    p.set_defaults(func=query_history)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
