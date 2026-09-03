#!/usr/bin/env python3
"""Incrementally download files exposed by EdStem Lessons and Resources."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree


MANIFEST = ".edstem-manifest.json"
DIRECT_EXTENSIONS = {
    ".7z", ".avi", ".csv", ".doc", ".docx", ".epub", ".gz", ".ipynb",
    ".jpeg", ".jpg", ".json", ".m4a", ".mkv", ".mov", ".mp3", ".mp4",
    ".odp", ".ods", ".odt", ".pdf", ".png", ".ppt", ".pptx", ".py",
    ".rar", ".tar", ".tex", ".tgz", ".tsv", ".txt", ".wav", ".webm",
    ".xls", ".xlsx", ".zip",
}


class SyncError(RuntimeError):
    pass


def parse_course(value: str) -> tuple[str, int]:
    if value.isdigit():
        return "us", int(value)
    match = re.search(r"/(us|eu|au|ap)/courses/(\d+)(?:/|$)", urlparse(value).path)
    if not match:
        raise SyncError("Expected an EdStem course URL or numeric course ID.")
    return match.group(1), int(match.group(2))


def safe_name(value: str, fallback: str = "untitled") -> str:
    value = unicodedata.normalize("NFKC", value).strip()
    value = re.sub(r"[\x00-\x1f\x7f/:\\]+", "-", value)
    value = re.sub(r"\s+", " ", value).strip(" .-")
    return value[:180] or fallback


def stable_url(value: str) -> str:
    """Remove transient credentials while preserving the remote object identity."""
    parsed = urlparse(value)
    return parsed._replace(query="", fragment="").geturl()


def indexed_name(index: object, identifier: object, name: str) -> str:
    return safe_name(f"{int(index or 0):02d}-{identifier}-{name}")


def resource_name(resource: dict) -> str:
    identifier = resource["id"]
    name = str(resource.get("name") or "resource")
    extension = str(resource.get("extension") or "")
    if extension and not extension.startswith("."):
        extension = f".{extension}"
    if extension and not name.lower().endswith(extension.lower()):
        name += extension
    return safe_name(f"{identifier}-{name}")


def resource_source(resource: dict, info: dict | None = None) -> dict:
    link = resource.get("link")
    return {
        "id": resource.get("id"),
        "name": resource.get("name"),
        "extension": resource.get("extension"),
        "category": resource.get("category"),
        "size": resource.get("size"),
        "created_at": resource.get("created_at"),
        "updated_at": resource.get("updated_at"),
        "link": stable_url(link) if isinstance(link, str) else None,
        "etag": (info or {}).get("etag"),
        "last_modified": (info or {}).get("last_modified"),
    }


def disposition_filename(value: str | None) -> str | None:
    if not value:
        return None
    message = Message()
    message["content-disposition"] = value
    filename = message.get_filename()
    return safe_name(unquote(filename)) if filename else None


def fingerprint(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def helper_path() -> Path:
    candidates = [
        os.environ.get("EDSTEM_BRO_CALL"),
        str(Path.home() / ".codex/skills/bro-browser/scripts/bro-call.mjs"),
        str(Path.home() / "dev/skills/skills/bro-browser/scripts/bro-call.mjs"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise SyncError("bro-browser is not installed; install/connect it before syncing EdStem.")


def bro_call(helper: Path, tool: str, arguments: dict) -> dict:
    command = [str(helper), tool, json.dumps(arguments, separators=(",", ":")), "--json"]
    if not os.access(helper, os.X_OK):
        command.insert(0, "node")
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SyncError("bro call failed; verify that bro and its browser extension are connected.") from error
    if result.returncode:
        raise SyncError("bro call failed; verify that bro and its browser extension are connected.")
    try:
        payload = json.loads(result.stdout)
        return payload["result"]["structuredContent"]
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise SyncError("bro returned an unreadable response.") from error


def edstem_token(helper: Path, region: str, course_id: int) -> str:
    flow = bro_call(
        helper,
        "browser.flow.start",
        {
            "url": f"https://edstem.org/{region}/courses/{course_id}/lessons",
            "active": False,
            "cleanup": True,
        },
    )
    session_id = flow["sessionId"]
    try:
        code = (
            "localStorage.getItem("
            + json.dumps(f"authToken:{region}")
            + ") || localStorage.getItem('authToken')"
        )
        action = bro_call(
            helper,
            "browser.flow.act",
            {
                "sessionId": session_id,
                "steps": [
                    {"type": "wait", "ms": 1200},
                    {"type": "eval", "code": code},
                ],
            },
        )
        text = action["results"][-1]["result"]["content"][0]["text"]
        token = json.loads(text)
        if not isinstance(token, str) or not token:
            raise SyncError("No EdStem login found in the connected browser.")
        return token
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise SyncError("Could not read the EdStem login from the connected browser.") from error
    finally:
        try:
            bro_call(helper, "browser.flow.finish", {"sessionId": session_id, "cleanup": True})
        except SyncError:
            pass


class EdStem:
    def __init__(self, region: str, token: str) -> None:
        self.base = f"https://{region}.edstem.org/api"
        self.headers = {"X-Token": token, "User-Agent": "edstem-course-materials/1"}

    def json(self, path: str) -> dict:
        try:
            with urlopen(Request(self.base + path, headers=self.headers), timeout=45) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code in (401, 403):
                raise SyncError("EdStem login expired or lacks access to this course.") from error
            raise SyncError(f"EdStem API returned HTTP {error.code} for {path}.") from error
        except URLError as error:
            raise SyncError(f"Could not reach EdStem for {path}.") from error


def probe(url: str) -> dict:
    try:
        request = Request(url, method="HEAD", headers={"User-Agent": "edstem-course-materials/1"})
        with urlopen(request, timeout=30) as response:
            headers = response.headers
            return {
                "filename": disposition_filename(headers.get("Content-Disposition")),
                "content_type": headers.get_content_type(),
                "size": int(headers["Content-Length"]) if headers.get("Content-Length", "").isdigit() else None,
                "etag": headers.get("ETag"),
                "last_modified": headers.get("Last-Modified"),
            }
    except (HTTPError, URLError):
        return {}


def extension_for(slide: dict, info: dict) -> str:
    filename = info.get("filename")
    if filename and Path(filename).suffix:
        return Path(filename).suffix
    path_extension = Path(urlparse(slide.get("file_url") or slide.get("url") or "").path).suffix
    if path_extension:
        return path_extension
    return {"pdf": ".pdf", "audio": ".mp3", "video": ".mp4"}.get(slide.get("type"), "")


def download(urls: list[str], destination: Path, headers: dict, expected_size: int | None) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    temporary.unlink(missing_ok=True)
    last_error = "download failed"
    for url in urls:
        try:
            request = Request(url, headers={**headers, "User-Agent": "edstem-course-materials/1"})
            with urlopen(request, timeout=90) as response, temporary.open("wb") as output:
                content_type = response.headers.get_content_type()
                if destination.suffix.lower() in DIRECT_EXTENSIONS and content_type == "text/html":
                    raise SyncError("server returned HTML instead of the requested file")
                digest = hashlib.sha256()
                size = 0
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                if expected_size is not None and size != expected_size:
                    raise SyncError(f"size mismatch: expected {expected_size}, received {size}")
                os.replace(temporary, destination)
                return {"size": size, "sha256": digest.hexdigest(), "content_type": content_type}
        except HTTPError as error:
            last_error = f"HTTP {error.code}"
        except (URLError, OSError, SyncError) as error:
            last_error = str(error)
        finally:
            temporary.unlink(missing_ok=True)
    raise SyncError(last_error)


def direct_link(url: str | None) -> bool:
    return bool(url and Path(urlparse(url).path).suffix.lower() in DIRECT_EXTENSIONS)


def document_text(content: str) -> str:
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise SyncError("EdStem document contains invalid XML") from error
    blocks = {"blockquote", "break", "heading", "list-item", "paragraph", "table-cell", "table-row"}
    pieces: list[str] = []

    def walk(node: ElementTree.Element) -> None:
        if node.text:
            pieces.append(node.text)
        for child in node:
            walk(child)
            if child.tail:
                pieces.append(child.tail)
        if node.tag in blocks:
            pieces.append("\n")

    walk(root)
    text = "".join(pieces)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def self_test() -> None:
    assert parse_course("12345") == ("us", 12345)
    assert parse_course("https://edstem.org/us/courses/12345/lessons") == ("us", 12345)
    assert safe_name("  Lecture/1:\tIntro  ") == "Lecture-1-Intro"
    assert disposition_filename('attachment; filename="slides.pdf"') == "slides.pdf"
    assert direct_link("https://example.edu/files/notes.PDF?download=1")
    assert stable_url("https://example.edu/files/notes.pdf?sig=example#page=1") == "https://example.edu/files/notes.pdf"
    assert indexed_name(1, 42, "slides.pdf") == "01-42-slides.pdf"
    assert resource_name({"id": 7, "name": "slides.pdf", "extension": "pdf"}) == "7-slides.pdf"
    assert resource_name({"id": 8, "name": "slides", "extension": "pdf"}) == "8-slides.pdf"
    resource_a = {"id": 7, "name": "slides", "link": "https://example.edu/slides.pdf?sig=one"}
    resource_b = {"id": 7, "name": "slides", "link": "https://example.edu/slides.pdf?sig=two"}
    assert fingerprint(resource_source(resource_a)) == fingerprint(resource_source(resource_b))
    assert document_text("<document><heading>Title</heading><paragraph>Hello <bold>world</bold>.</paragraph></document>") == "Title\nHello world.\n"
    assert fingerprint({"b": 2, "a": 1}) == fingerprint({"a": 1, "b": 2})
    print("self-test: ok")


def run(course: str, destination_arg: str | None) -> int:
    region, course_id = parse_course(course)
    destination = Path(destination_arg or f"edstem-{course_id}").expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / MANIFEST
    try:
        old = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    except json.JSONDecodeError as error:
        raise SyncError(f"Invalid manifest: {manifest_path}") from error

    token = edstem_token(helper_path(), region, course_id)
    api = EdStem(region, token)
    index = api.json(f"/courses/{course_id}/lessons")
    resources = api.json(f"/courses/{course_id}/resources").get("resources", [])
    old_files = old.get("files", {})
    current: dict[str, dict] = {}
    links: list[dict] = []
    failures: list[dict] = []
    path_owners: dict[str, str] = {}
    downloaded = skipped = 0

    def claim_path(key: str, relative: Path) -> str:
        relative_string = relative.as_posix()
        owner = path_owners.get(relative_string)
        if owner is not None and owner != key:
            raise SyncError(f"Output path collision between {owner} and {key}: {relative_string}")
        path_owners[relative_string] = key
        return relative_string

    def sync(key: str, relative: Path, urls: list[str], source: object, headers: dict, size: int | None) -> None:
        nonlocal downloaded, skipped
        relative_string = claim_path(key, relative)
        source_fingerprint = fingerprint(source)
        previous = old_files.get(key, {})
        local = destination / relative
        if (
            previous.get("fingerprint") == source_fingerprint
            and previous.get("path") == relative_string
            and local.is_file()
            and (size is None or local.stat().st_size == size)
        ):
            current[key] = {name: value for name, value in previous.items() if name != "stale"}
            skipped += 1
            print(f"SKIP {relative_string}")
            return
        try:
            result = download(urls, local, headers, size)
            current[key] = {
                "path": relative_string,
                "fingerprint": source_fingerprint,
                **result,
            }
            downloaded += 1
            print(f"GET  {relative_string}")
        except SyncError as error:
            failures.append({"key": key, "path": relative_string, "error": str(error)})
            if previous:
                current[key] = {name: value for name, value in previous.items() if name != "stale"}
            print(f"FAIL {relative_string}: {error}", file=sys.stderr)

    def sync_text(key: str, relative: Path, content: str, source: object) -> None:
        nonlocal downloaded, skipped
        relative_string = claim_path(key, relative)
        source_fingerprint = fingerprint(source)
        payload = content.encode()
        previous = old_files.get(key, {})
        local = destination / relative
        if (
            previous.get("fingerprint") == source_fingerprint
            and previous.get("path") == relative_string
            and local.is_file()
            and local.stat().st_size == len(payload)
        ):
            current[key] = {name: value for name, value in previous.items() if name != "stale"}
            skipped += 1
            print(f"SKIP {relative_string}")
            return
        local.parent.mkdir(parents=True, exist_ok=True)
        temporary = local.with_name(local.name + ".part")
        temporary.write_bytes(payload)
        os.replace(temporary, local)
        current[key] = {
            "path": relative_string,
            "fingerprint": source_fingerprint,
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "content_type": "text/plain",
        }
        downloaded += 1
        print(f"GET  {relative_string}")

    for lesson_stub in index.get("lessons", []):
        lesson = api.json(f"/lessons/{lesson_stub['id']}").get("lesson", {})
        lesson_dir = Path("lessons") / safe_name(f"{lesson['id']}-{lesson.get('title', 'lesson')}")
        for slide in lesson.get("slides", []):
            slide_key = f"lesson:{lesson['id']}:slide:{slide['id']}"
            title = slide.get("title") or f"slide-{slide['id']}"
            file_url = slide.get("file_url")
            url = slide.get("url")
            if file_url:
                info = probe(file_url)
                filename = info.get("filename") or safe_name(title) + extension_for(slide, info)
                relative = lesson_dir / indexed_name(slide.get("index"), slide["id"], filename)
                source = {
                    "slide_id": slide["id"],
                    "file_url": stable_url(file_url),
                    "updated_at": slide.get("updated_at"),
                    "created_at": slide.get("created_at"),
                    "etag": info.get("etag"),
                    "last_modified": info.get("last_modified"),
                    "size": info.get("size"),
                }
                sync(slide_key, relative, [file_url], source, {}, info.get("size"))
            elif direct_link(url):
                filename = safe_name(Path(urlparse(url).path).name)
                relative = lesson_dir / indexed_name(slide.get("index"), slide["id"], filename)
                info = probe(url)
                sync(
                    slide_key,
                    relative,
                    [url],
                    {"slide_id": slide["id"], "url": stable_url(url), **info},
                    {},
                    info.get("size"),
                )
            elif slide.get("type") == "document" and slide.get("content"):
                relative = lesson_dir / indexed_name(slide.get("index"), slide["id"], f"{title}.txt")
                sync_text(slide_key, relative, document_text(slide["content"]), {"content": slide["content"]})
            else:
                links.append({
                    "lesson_id": lesson["id"],
                    "lesson_title": lesson.get("title"),
                    "slide_id": slide["id"],
                    "title": title,
                    "type": slide.get("type"),
                    "url": url,
                })

    for resource in resources:
        resource_id = resource["id"]
        name = resource_name(resource)
        category = safe_name(resource.get("category") or "uncategorized")
        key = f"resource:{resource_id}"
        if resource.get("link"):
            if direct_link(resource["link"]):
                info = probe(resource["link"])
                sync(
                    key,
                    Path("resources") / category / name,
                    [resource["link"]],
                    resource_source(resource, info),
                    {},
                    info.get("size"),
                )
            else:
                links.append({"resource_id": resource_id, "title": name, "type": "resource-link", "url": resource["link"]})
            continue
        encoded_name = quote(name, safe="")
        urls = [
            f"{api.base}/resources/{resource_id}/download/{encoded_name}?dl=1",
            f"{api.base}/resources/{resource_id}/download?dl=1",
        ]
        sync(
            key,
            Path("resources") / category / name,
            urls,
            resource_source(resource),
            api.headers,
            resource.get("size"),
        )

    stale = sorted(set(old_files) - set(current))
    for key in stale:
        current[key] = {**old_files[key], "stale": True}
    manifest = {
        "version": 1,
        "course_id": course_id,
        "region": region,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "files": current,
        "links": links,
        "failed": failures,
        "stale": stale,
    }
    temporary_manifest = manifest_path.with_name(MANIFEST + ".part")
    temporary_manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    os.replace(temporary_manifest, manifest_path)
    print(f"downloaded: {downloaded}; skipped: {skipped}; links: {len(links)}; failed: {len(failures)}")
    print(f"manifest: {manifest_path}")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("course", nargs="?", help="EdStem course URL or numeric course ID")
    parser.add_argument("destination", nargs="?", help="output folder (default: edstem-COURSE_ID)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.course:
        parser.error("course is required unless --self-test is used")
    try:
        return run(args.course, args.destination)
    except SyncError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
