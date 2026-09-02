#!/usr/bin/env python3
"""Download Panopto recordings discovered through a logged-in bro browser."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


MANIFEST_NAME = ".panopto-manifest.json"
MEDIA_JS = r"""(() => ({
  title: document.title,
  pageText: document.body.innerText.slice(0, 500),
  media: [...new Set(performance.getEntriesByType('resource').map(e => e.name)
    .filter(u => /\.(?:mp4|m3u8)(?:\?|$)/i.test(u)))]
}))()"""
START_JS = r"""(() => {
  const button = [...document.querySelectorAll('button')].find(node =>
    /play/i.test([node.innerText, node.getAttribute('aria-label'), node.title].join(' ')));
  if (button) button.click();
  const video = document.querySelector('video');
  if (video) video.play().catch(() => {});
  return Boolean(button || video);
})()"""


class DownloadError(RuntimeError):
    pass


def safe_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip()
    value = re.sub(r"[\x00-\x1f\x7f/:\\]+", "-", value)
    value = re.sub(r"\s+", " ", value).strip(" .-")
    return value[:180] or "Panopto recording"


def viewer_id(url: str) -> str:
    parsed = urlparse(url)
    identifier = parse_qs(parsed.query).get("id", [""])[0]
    if "panopto" not in parsed.netloc.lower() or not re.fullmatch(r"[0-9a-fA-F-]{32,36}", identifier):
        raise DownloadError(f"Not a Panopto Viewer URL: {url}")
    return identifier.lower()


def collect_sources(values: list[str]) -> list[tuple[str, str | None]]:
    sources: list[tuple[str, str | None]] = []
    for value in values:
        path = Path(value).expanduser()
        if path.is_file():
            try:
                payload = json.loads(path.read_text())
            except json.JSONDecodeError as error:
                raise DownloadError(f"Invalid JSON manifest: {path}") from error
            for link in payload.get("links", []):
                url = link.get("url")
                if url and "panopto" in urlparse(url).netloc.lower():
                    sources.append((url, link.get("title")))
        else:
            sources.append((value, None))
    unique: dict[str, tuple[str, str | None]] = {}
    for url, title in sources:
        unique.setdefault(viewer_id(url), (url, title))
    if not unique:
        raise DownloadError("No Panopto Viewer links found.")
    return list(unique.values())


def bro_helper() -> Path:
    candidates = [
        os.environ.get("PANOPTO_BRO_CALL"),
        str(Path.home() / ".codex/skills/bro-browser/scripts/bro-call.mjs"),
        str(Path.home() / "dev/skills/skills/bro-browser/scripts/bro-call.mjs"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise DownloadError("bro-browser is not installed.")


def bro_call(helper: Path, tool: str, arguments: dict) -> dict:
    command = [str(helper), tool, json.dumps(arguments, separators=(",", ":")), "--json"]
    if not os.access(helper, os.X_OK):
        command.insert(0, "node")
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DownloadError("bro call failed; verify the server and browser extension.") from error
    if result.returncode:
        raise DownloadError("bro call failed; verify the server and browser extension.")
    try:
        return json.loads(result.stdout)["result"]["structuredContent"]
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise DownloadError("bro returned an unreadable response.") from error


def eval_result(action: dict) -> dict:
    try:
        text = action["results"][-1]["result"]["content"][0]["text"]
        value = json.loads(text)
        if not isinstance(value, dict):
            raise TypeError
        return value
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise DownloadError("Could not read Panopto player state.") from error


def discover(helper: Path, viewer_url: str) -> tuple[str, list[str]]:
    flow = bro_call(
        helper,
        "browser.flow.start",
        {"url": viewer_url, "active": True, "cleanup": True},
    )
    session_id = flow["sessionId"]
    try:
        bro_call(
            helper,
            "browser.flow.act",
            {
                "sessionId": session_id,
                "steps": [
                    {"type": "wait", "ms": 8000},
                    {"type": "eval", "code": START_JS},
                ],
            },
        )
        action = bro_call(
            helper,
            "browser.flow.act",
            {
                "sessionId": session_id,
                "steps": [
                    {"type": "wait", "ms": 5000},
                    {"type": "eval", "code": MEDIA_JS},
                ],
            },
        )
        state = eval_result(action)
        if not state.get("media"):
            action = bro_call(
                helper,
                "browser.flow.act",
                {
                    "sessionId": session_id,
                    "steps": [
                        {"type": "wait", "ms": 5000},
                        {"type": "eval", "code": MEDIA_JS},
                    ],
                },
            )
            state = eval_result(action)
        if not state.get("media"):
            page_text = state.get("pageText", "").lower()
            reason = "Panopto login is required" if "sign in" in page_text or "log in" in page_text else "player exposed no media URL"
            raise DownloadError(reason)
        return state.get("title") or "Panopto recording", state["media"]
    finally:
        try:
            bro_call(helper, "browser.flow.finish", {"sessionId": session_id, "cleanup": True})
        except DownloadError:
            pass


def choose_media(urls: list[str]) -> str:
    direct = [url for url in urls if re.search(r"\.mp4(?:\?|$)", url, re.I)]
    direct.sort(key=lambda url: ("fragmented.mp4" not in url.lower(), "cloudfront" not in url.lower(), len(url)))
    if direct:
        return direct[0]
    renditions = [url for url in urls if re.search(r"/index\.m3u8(?:\?|$)", url, re.I)]
    if renditions:
        return re.sub(r"/index\.m3u8(?=\?|$)", "/fragmented.mp4", renditions[0], flags=re.I)
    raise DownloadError("Panopto exposed no downloadable MP4.")


def file_sha256(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def recorded_file_valid(path: Path, record: dict) -> tuple[bool, bool]:
    """Validate a recorded file, hashing only when its mtime no longer matches."""
    if not path.is_file():
        return False, False
    stat = path.stat()
    if stat.st_size != record.get("size"):
        return False, False
    with path.open("rb") as file:
        if b"ftyp" not in file.read(32):
            return False, False
    recorded_mtime = record.get("mtime_ns")
    if recorded_mtime == stat.st_mtime_ns:
        return True, False
    expected_hash = record.get("sha256")
    if not isinstance(expected_hash, str) or file_sha256(path) != expected_hash:
        return False, False
    record["mtime_ns"] = stat.st_mtime_ns
    return True, recorded_mtime != stat.st_mtime_ns


def write_manifest(path: Path, manifest: dict) -> None:
    temporary = path.with_name(path.name + ".part")
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    os.replace(temporary, path)


def download(media_url: str, viewer_url: str, destination: Path) -> tuple[int, str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    offset = partial.stat().st_size if partial.is_file() else 0
    headers = {"Referer": viewer_url, "User-Agent": "panopto-mp4-bulk-download/2"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    try:
        response = urlopen(Request(media_url, headers=headers), timeout=90)
    except (HTTPError, URLError) as error:
        raise DownloadError("Panopto media request failed.") from error
    with response:
        append = offset > 0 and response.status == 206
        if not append:
            offset = 0
        remaining = response.headers.get("Content-Length")
        total = offset + int(remaining) if remaining and remaining.isdigit() else None
        if total and shutil.disk_usage(destination.parent).free < total - offset + 512 * 1024 * 1024:
            raise DownloadError("Not enough free disk space for this recording.")
        downloaded = offset
        next_report = downloaded + 64 * 1024 * 1024
        with partial.open("ab" if append else "wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                downloaded += len(chunk)
                if downloaded >= next_report:
                    suffix = f"/{total // (1024 * 1024)} MiB" if total else " MiB"
                    print(f"  {downloaded // (1024 * 1024)}{suffix}", flush=True)
                    next_report += 64 * 1024 * 1024
    with partial.open("rb") as file:
        if b"ftyp" not in file.read(32):
            raise DownloadError("Downloaded response is not an MP4 file.")
        file.seek(0)
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    os.replace(partial, destination)
    stat = destination.stat()
    return stat.st_size, digest, stat.st_mtime_ns


def self_test() -> None:
    identifier = "00000000-0000-4000-8000-000000000000"
    url = f"https://tenant.hosted.panopto.com/Panopto/Pages/Viewer.aspx?id={identifier}"
    assert viewer_id(url) == identifier
    assert safe_name(" Course/One: Lecture 1 ") == "Course-One- Lecture 1"
    assert choose_media(["https://cdn/x/index.m3u8?a=1"]) == "https://cdn/x/fragmented.mp4?a=1"
    assert choose_media(["https://cdn/x/video.mp4?sig=example"]).endswith("sig=example")
    with tempfile.TemporaryDirectory() as directory:
        recording = Path(directory) / "recording.mp4"
        recording.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"a" * 32)
        record = {"size": recording.stat().st_size, "sha256": file_sha256(recording)}
        assert recorded_file_valid(recording, record) == (True, True)
        assert recorded_file_valid(recording, record) == (True, False)
        recording.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"b" * 32)
        changed_mtime = int(record["mtime_ns"]) + 1_000_000
        os.utime(recording, ns=(changed_mtime, changed_mtime))
        assert recorded_file_valid(recording, record) == (False, False)
    print("self-test: ok")


def run(sources: list[str], output_dir: str) -> int:
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / MANIFEST_NAME
    try:
        manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {"version": 1, "videos": {}}
    except json.JSONDecodeError as error:
        raise DownloadError(f"Invalid manifest: {manifest_path}") from error
    videos = manifest.setdefault("videos", {})
    helper = bro_helper()
    failures = 0
    for viewer_url, hinted_title in collect_sources(sources):
        identifier = viewer_id(viewer_url)
        existing = videos.get(identifier, {})
        existing_path = output / existing.get("path", "")
        valid, manifest_changed = recorded_file_valid(existing_path, existing)
        if valid:
            if manifest_changed:
                write_manifest(manifest_path, manifest)
            print(f"SKIP {existing_path.name}")
            continue
        print(f"DISCOVER {hinted_title or identifier}", flush=True)
        try:
            title, media_urls = discover(helper, viewer_url)
            filename = safe_name(title) + f"--{identifier[:8]}.mp4"
            destination = output / filename
            print(f"GET  {filename}", flush=True)
            size, digest, mtime_ns = download(choose_media(media_urls), viewer_url, destination)
            videos[identifier] = {
                "viewer": viewer_url,
                "title": title,
                "path": filename,
                "size": size,
                "sha256": digest,
                "mtime_ns": mtime_ns,
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
            }
            print(f"DONE {filename} ({size // (1024 * 1024)} MiB)", flush=True)
        except DownloadError as error:
            failures += 1
            print(f"FAIL {hinted_title or identifier}: {error}", file=sys.stderr, flush=True)
        write_manifest(manifest_path, manifest)
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", help="Panopto Viewer URLs or EdStem manifest files")
    parser.add_argument("--output-dir", default="panopto-videos")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.sources:
        parser.error("at least one Viewer URL or manifest is required")
    try:
        return run(args.sources, args.output_dir)
    except DownloadError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
