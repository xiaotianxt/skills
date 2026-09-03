#!/usr/bin/env python3
"""Small, dependency-free Canvas LMS CLI bundled with the canvas skill."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import mimetypes
import os
import pathlib
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from typing import Any

DEFAULT_BASE_URL = "https://canvas.cmu.edu"
DEFAULT_TOKEN_COMMAND = "keychain-secret get codex.canvas credential"
STRING_ID_ACCEPT = "application/json+canvas-string-ids"
RETRYABLE_HTTP_STATUS = {429, 500, 502, 503, 504}
SENSITIVE_KEYS = {"access_token", "authorization", "token", "verifier"}
SENSITIVE_QUERY_RE = re.compile(
    r"(?P<prefix>(?:access_token|token|verifier)=)(?P<value>[^&\"'<>\\\s]+)",
    re.IGNORECASE,
)


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def ensure_dir(path: pathlib.Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text_atomic(path: pathlib.Path, text: str) -> None:
    ensure_dir(path.parent)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path: pathlib.Path, data: Any) -> None:
    write_text_atomic(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def redact_string(value: str) -> str:
    return SENSITIVE_QUERY_RE.sub(r"\g<prefix>[REDACTED]", value)


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.casefold() in SENSITIVE_KEYS else redact_secrets(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, str):
        return redact_string(value)
    return value


def resolve_token(token_command: str | None = None) -> str:
    env_token = os.environ.get("CANVAS_TOKEN", "").strip()
    if env_token:
        return env_token

    command = token_command or os.environ.get("CANVAS_TOKEN_COMMAND") or DEFAULT_TOKEN_COMMAND
    argv = shlex.split(command)
    if not argv:
        raise RuntimeError("Canvas token command is empty")

    process = subprocess.run(argv, check=False, capture_output=True, text=True)
    token = process.stdout.strip()
    if process.returncode == 0 and token:
        return token

    detail = process.stderr.strip() or f"exit status {process.returncode}"
    raise RuntimeError(f"Canvas token command failed: {detail}")


def encode_form_pairs(pairs: Iterable[tuple[str, str]]) -> bytes:
    return urllib.parse.urlencode(list(pairs), doseq=True).encode("utf-8")


def encode_multipart(
    fields: dict[str, Any], file_field: str, file_path: pathlib.Path
) -> tuple[str, bytes]:
    boundary = f"----CanvasBoundary{uuid.uuid4().hex}"
    body = bytearray()

    def add_line(text: str) -> None:
        body.extend(text.encode("utf-8"))
        body.extend(b"\r\n")

    for key, value in fields.items():
        values = value if isinstance(value, list) else [value]
        for item in values:
            add_line(f"--{boundary}")
            add_line(f'Content-Disposition: form-data; name="{key}"')
            add_line("")
            add_line(str(item))

    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    add_line(f"--{boundary}")
    add_line(
        f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"'
    )
    add_line(f"Content-Type: {content_type}")
    add_line("")
    body.extend(file_path.read_bytes())
    body.extend(b"\r\n")
    add_line(f"--{boundary}--")
    return boundary, bytes(body)


def extract_next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for chunk in link_header.split(","):
        match = re.search(r'<([^>]+)>\s*;\s*rel="([^"]+)"', chunk.strip())
        if match and match.group(2) == "next":
            return match.group(1)
    return None


class CanvasClient:
    def __init__(self, base_url: str, token: str, timeout: int = 60, retries: int = 4):
        self.base_url = base_url.rstrip("/")
        self.base_origin = urllib.parse.urlsplit(self.base_url)[:2]
        self.token = token
        self.timeout = timeout
        self.retries = retries

    def api_url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            origin = urllib.parse.urlsplit(path)[:2]
            if origin != self.base_origin:
                raise ValueError("Refusing to send Canvas credentials to a different origin")
            return path
        return f"{self.base_url}/{'/'.join(part for part in path.split('/') if part)}"

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": STRING_ID_ACCEPT,
        }
        if extra:
            headers.update(extra)
        return headers

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        form_pairs: Iterable[tuple[str, str]] | None = None,
        raw_data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ):
        final_url = self.api_url(url)
        if params:
            query = urllib.parse.urlencode(params, doseq=True)
            final_url = f"{final_url}{'&' if '?' in final_url else '?'}{query}"

        data = raw_data
        request_headers = self._headers(headers)
        if form_pairs is not None:
            data = encode_form_pairs(form_pairs)
            request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            request = urllib.request.Request(
                final_url, data=data, headers=request_headers, method=method
            )
            try:
                return urllib.request.urlopen(request, timeout=self.timeout)
            except urllib.error.HTTPError as error:
                last_error = error
                if error.code not in RETRYABLE_HTTP_STATUS or attempt >= self.retries:
                    break
                retry_after = error.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else min(2**attempt, 10)
                eprint(f"HTTP {error.code}; retrying in {delay:.1f}s")
                time.sleep(delay)
            except urllib.error.URLError as error:
                last_error = error
                if attempt >= self.retries:
                    break
                delay = min(2**attempt, 10)
                eprint(f"network error; retrying in {delay:.1f}s")
                time.sleep(delay)

        assert last_error is not None
        raise last_error

    def request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        form_pairs: Iterable[tuple[str, str]] | None = None,
        raw_data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        with self._request(
            method,
            url,
            params=params,
            form_pairs=form_pairs,
            raw_data=raw_data,
            headers=headers,
        ) as response:
            payload = response.read()
            return json.loads(payload.decode("utf-8")) if payload else None

    def request_with_headers(
        self, method: str, url: str, *, params: dict[str, Any] | None = None
    ) -> tuple[Any, dict[str, str]]:
        with self._request(method, url, params=params) as response:
            payload = response.read()
            body = json.loads(payload.decode("utf-8")) if payload else None
            return body, dict(response.headers)

    def paginate(self, url: str, *, params: dict[str, Any] | None = None) -> list[Any]:
        items: list[Any] = []
        next_url: str | None = url
        next_params = params
        while next_url:
            body, headers = self.request_with_headers("GET", next_url, params=next_params)
            if isinstance(body, list):
                items.extend(body)
            elif body is not None:
                items.append(body)
            next_url = extract_next_link(headers.get("Link"))
            next_params = None
        return items

    def download_public_url(self, url: str, destination: pathlib.Path) -> None:
        """Download a Canvas verifier URL without forwarding the bearer token."""
        ensure_dir(destination.parent)
        temporary = destination.with_name(f".{destination.name}.{os.getpid()}.part")
        request = urllib.request.Request(url, headers={"Accept": "application/octet-stream"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response, temporary.open(
                "wb"
            ) as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    def upload_user_file(
        self, file_path: pathlib.Path, parent_folder_path: str | None = None
    ) -> Any:
        init_pairs = [
            ("name", file_path.name),
            ("size", str(file_path.stat().st_size)),
            ("content_type", mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"),
            ("on_duplicate", "rename"),
        ]
        if parent_folder_path:
            init_pairs.append(("parent_folder_path", parent_folder_path))

        init_response = self.request_json(
            "POST", "/api/v1/users/self/files", form_pairs=init_pairs
        )
        upload_url = init_response["upload_url"]
        upload_params = init_response["upload_params"]
        boundary, raw_data = encode_multipart(upload_params, "file", file_path)
        request = urllib.request.Request(
            upload_url,
            data=raw_data,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = response.read()
            return json.loads(payload.decode("utf-8")) if payload else None


def safe_fetch(bundle: dict[str, Any], key: str, operation: Callable[[], Any]) -> None:
    try:
        bundle[key] = operation()
    except Exception as error:
        bundle[f"{key}_error"] = f"{type(error).__name__}: {error}"


def fetch_pages_with_bodies(client: CanvasClient, course_id: str) -> list[dict[str, Any]]:
    pages = client.paginate(
        f"/api/v1/courses/{course_id}/pages", params={"per_page": 100}
    )
    enriched = []
    for page in pages:
        page_url = page.get("url")
        if not page_url:
            enriched.append(page)
            continue
        try:
            detail = client.request_json(
                "GET", f"/api/v1/courses/{course_id}/pages/{page_url}"
            )
            enriched.append({**page, **detail})
        except Exception as error:
            enriched.append(
                {**page, "_detail_error": f"{type(error).__name__}: {error}"}
            )
    return enriched


def collect_resource_links(bundle: dict[str, Any]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def add_links(source: str, markup: str | None) -> None:
        if not markup:
            return
        for link_type, pattern in [
            ("href", r'href=["\']([^"\']+)'),
            ("src", r'src=["\']([^"\']+)'),
            ("data_api_endpoint", r'data-api-endpoint=["\']([^"\']+)'),
        ]:
            for match in re.findall(pattern, markup):
                url = html.unescape(match)
                key = (source, link_type, url)
                if key not in seen:
                    seen.add(key)
                    links.append({"source": source, "type": link_type, "url": url})

    add_links("course.syllabus_body", bundle.get("course", {}).get("syllabus_body"))
    for page in bundle.get("pages", []):
        add_links(f"pages:{page.get('url')}", page.get("body"))
    for topic in bundle.get("discussion_topics", []):
        add_links(f"discussion_topics:{topic.get('id')}", topic.get("message"))
    for announcement in bundle.get("announcements", []):
        add_links(f"announcements:{announcement.get('id')}", announcement.get("message"))
    for assignment in bundle.get("assignments", []):
        add_links(f"assignments:{assignment.get('id')}", assignment.get("description"))
    return links


def fetch_linked_canvas_files(
    client: CanvasClient, resource_links: list[dict[str, str]]
) -> list[dict[str, Any]]:
    endpoints: dict[str, str] = {}
    for item in resource_links:
        url = item["url"]
        if "/api/v1/" in url and re.search(r"/files/\d+", url):
            endpoints.setdefault(url, item["source"])

    metadata = []
    for endpoint, source in endpoints.items():
        try:
            item = client.request_json("GET", endpoint)
            metadata.append({**item, "_discovered_from": source})
        except Exception as error:
            metadata.append(
                {
                    "_endpoint": endpoint,
                    "_discovered_from": source,
                    "_error": f"{type(error).__name__}: {error}",
                }
            )
    return metadata


def fetch_course_bundle(client: CanvasClient, course_id: str) -> dict[str, Any]:
    bundle: dict[str, Any] = {}
    safe_fetch(
        bundle,
        "course",
        lambda: client.request_json(
            "GET",
            f"/api/v1/courses/{course_id}",
            params={
                "include[]": [
                    "syllabus_body",
                    "term",
                    "teachers",
                    "total_scores",
                    "course_image",
                    "banner_image",
                ]
            },
        ),
    )
    safe_fetch(
        bundle,
        "tabs",
        lambda: client.request_json("GET", f"/api/v1/courses/{course_id}/tabs"),
    )
    safe_fetch(
        bundle,
        "modules",
        lambda: client.paginate(
            f"/api/v1/courses/{course_id}/modules",
            params={"include[]": ["items", "content_details"], "per_page": 100},
        ),
    )
    safe_fetch(bundle, "pages", lambda: fetch_pages_with_bodies(client, course_id))
    safe_fetch(
        bundle,
        "assignments",
        lambda: client.paginate(
            f"/api/v1/courses/{course_id}/assignments",
            params={"include[]": ["submission", "rubric"], "per_page": 100},
        ),
    )
    safe_fetch(
        bundle,
        "assignment_groups",
        lambda: client.paginate(
            f"/api/v1/courses/{course_id}/assignment_groups",
            params={
                "include[]": ["assignments", "submission", "rules"],
                "per_page": 100,
            },
        ),
    )
    safe_fetch(
        bundle,
        "discussion_topics",
        lambda: client.paginate(
            f"/api/v1/courses/{course_id}/discussion_topics", params={"per_page": 100}
        ),
    )
    safe_fetch(
        bundle,
        "announcements",
        lambda: client.paginate(
            "/api/v1/announcements",
            params={"context_codes[]": [f"course_{course_id}"], "per_page": 100},
        ),
    )
    safe_fetch(
        bundle,
        "folders",
        lambda: client.paginate(
            f"/api/v1/courses/{course_id}/folders", params={"per_page": 100}
        ),
    )
    safe_fetch(
        bundle,
        "files",
        lambda: client.paginate(
            f"/api/v1/courses/{course_id}/files", params={"per_page": 100}
        ),
    )
    safe_fetch(
        bundle,
        "media_objects",
        lambda: client.paginate(
            f"/api/v1/courses/{course_id}/media_objects",
            params={"exclude[]": ["sources", "tracks"], "per_page": 100},
        ),
    )
    bundle["resource_links"] = collect_resource_links(bundle)
    safe_fetch(
        bundle,
        "linked_canvas_files",
        lambda: fetch_linked_canvas_files(client, bundle["resource_links"]),
    )
    return bundle


def save_course_bundle(bundle: dict[str, Any], out_dir: pathlib.Path) -> None:
    ensure_dir(out_dir)
    keys = [
        "course",
        "tabs",
        "modules",
        "pages",
        "assignments",
        "assignment_groups",
        "discussion_topics",
        "announcements",
        "folders",
        "files",
        "media_objects",
        "resource_links",
        "linked_canvas_files",
    ]
    safe_bundle = redact_secrets(bundle)
    for key in keys:
        data_path = out_dir / f"{key}.json"
        error_path = out_dir / f"{key}.error.json"
        if key in safe_bundle:
            write_json(data_path, safe_bundle[key])
            error_path.unlink(missing_ok=True)
        elif f"{key}_error" in safe_bundle:
            write_json(error_path, {"error": safe_bundle[f"{key}_error"]})

    syllabus = safe_bundle.get("course", {}).get("syllabus_body")
    if syllabus:
        write_text_atomic(out_dir / "syllabus.html", syllabus)


def safe_component(value: str, fallback: str) -> str:
    value = value.replace("\x00", "").replace("/", "-").replace("\\", "-").strip()
    return fallback if value in {"", ".", ".."} else value


def relative_folder_path(folder: dict[str, Any] | None) -> pathlib.Path:
    if not folder:
        return pathlib.Path()
    parts = [safe_component(part, "folder") for part in folder.get("full_name", "").split("/")]
    return pathlib.Path(*parts[1:]) if len(parts) > 1 else pathlib.Path()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_previous_manifest(path: pathlib.Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, list):
        return {}
    return {
        str(item["id"]): item
        for item in data
        if isinstance(item, dict) and item.get("id") is not None
    }


def manifest_destination(
    out_dir: pathlib.Path,
    file_obj: dict[str, Any],
    folder: dict[str, Any] | None,
    previous: dict[str, Any] | None,
) -> pathlib.Path:
    root = out_dir / "course-files"
    if previous and isinstance(previous.get("path"), str):
        candidate = out_dir / previous["path"]
        try:
            candidate.resolve().relative_to(root.resolve())
            return candidate
        except ValueError:
            pass
    filename = safe_component(
        file_obj.get("filename") or file_obj.get("display_name") or str(file_obj["id"]),
        str(file_obj["id"]),
    )
    return root / relative_folder_path(folder) / filename


def download_course_files(
    client: CanvasClient,
    files: list[dict[str, Any]],
    folders: list[dict[str, Any]],
    out_dir: pathlib.Path,
    *,
    force: bool = False,
) -> list[dict[str, Any]]:
    manifest_path = out_dir / "course-files-manifest.json"
    previous_by_id = load_previous_manifest(manifest_path)
    folders_by_id = {str(folder["id"]): folder for folder in folders}
    claimed_paths: dict[pathlib.Path, str] = {}
    manifest: list[dict[str, Any]] = []

    for file_obj in sorted(files, key=lambda item: str(item.get("id", ""))):
        file_id = str(file_obj.get("id", "unknown"))
        previous = previous_by_id.get(file_id)
        folder = folders_by_id.get(str(file_obj.get("folder_id", "")))
        destination = manifest_destination(out_dir, file_obj, folder, previous)
        if destination in claimed_paths and claimed_paths[destination] != file_id:
            destination = destination.with_name(
                f"{destination.stem}-{file_id}{destination.suffix}"
            )
        claimed_paths[destination] = file_id

        relative_path = str(destination.relative_to(out_dir))
        expected_size = file_obj.get("size")
        remote_updated_at = file_obj.get("updated_at")
        reusable = not force and destination.is_file() and previous is not None
        if reusable and expected_size is not None:
            reusable = destination.stat().st_size == int(expected_size)
        if reusable and previous.get("sha256"):
            reusable = sha256_file(destination) == previous["sha256"]
        if reusable:
            reusable = (
                previous.get("updated_at") is not None
                and previous["updated_at"] == remote_updated_at
            )

        status = "existing"
        if not reusable:
            url = file_obj.get("url")
            if not url:
                manifest.append(
                    {
                        "id": file_id,
                        "status": "skipped",
                        "path": relative_path,
                        "reason": "missing download URL",
                    }
                )
                continue
            existed = destination.exists()
            client.download_public_url(url, destination)
            if expected_size is not None and destination.stat().st_size != int(expected_size):
                destination.unlink(missing_ok=True)
                raise RuntimeError(
                    f"Downloaded size mismatch for Canvas file {file_id}: "
                    f"expected {expected_size} bytes"
                )
            status = "updated" if existed else "downloaded"

        manifest.append(
            {
                "id": file_id,
                "status": status,
                "path": relative_path,
                "size": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "updated_at": remote_updated_at,
            }
        )

    write_json(manifest_path, manifest)
    return manifest


def parse_key_value_pairs(items: list[str] | None) -> dict[str, Any]:
    pairs: dict[str, Any] = {}
    for item in items or []:
        if "=" not in item:
            raise ValueError(f"Invalid --param value: {item}")
        key, value = item.split("=", 1)
        if key not in pairs:
            pairs[key] = value
        elif isinstance(pairs[key], list):
            pairs[key].append(value)
        else:
            pairs[key] = [pairs[key], value]
    return pairs


def command_whoami(client: CanvasClient, _args: argparse.Namespace) -> None:
    user = redact_secrets(client.request_json("GET", "/api/v1/users/self"))
    print(json.dumps(user, ensure_ascii=False, indent=2))


def command_courses(client: CanvasClient, args: argparse.Namespace) -> None:
    params: dict[str, Any] = {
        "include[]": ["term", "teachers", "syllabus_body", "total_scores"],
        "per_page": 100,
    }
    if args.active_only:
        params["state[]"] = ["available"]
    courses = client.paginate("/api/v1/users/self/courses", params=params)
    print(json.dumps(redact_secrets(courses), ensure_ascii=False, indent=2))


def command_raw_get(client: CanvasClient, args: argparse.Namespace) -> None:
    params = parse_key_value_pairs(args.param)
    data = (
        client.paginate(args.path, params=params)
        if args.paginate
        else client.request_json("GET", args.path, params=params)
    )
    print(json.dumps(redact_secrets(data), ensure_ascii=False, indent=2))


def command_sync_course(client: CanvasClient, args: argparse.Namespace) -> None:
    out_dir = pathlib.Path(args.out).expanduser().resolve()
    eprint(f"syncing Canvas course {args.course_id} -> {out_dir}")
    bundle = fetch_course_bundle(client, args.course_id)
    save_course_bundle(bundle, out_dir)

    manifest: list[dict[str, Any]] = []
    if not args.metadata_only and "files" in bundle and "folders" in bundle:
        manifest = download_course_files(
            client, bundle["files"], bundle["folders"], out_dir, force=args.force
        )

    endpoint_errors = {
        key.removesuffix("_error"): value
        for key, value in bundle.items()
        if key.endswith("_error")
    }
    summary = {
        "synced_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "course_id": args.course_id,
        "out": str(out_dir),
        "metadata": "partial" if endpoint_errors else "saved",
        "endpoint_errors": sorted(endpoint_errors),
        "accessible_files": len(bundle.get("files", [])),
        "downloaded": sum(item.get("status") == "downloaded" for item in manifest),
        "updated": sum(item.get("status") == "updated" for item in manifest),
        "existing": sum(item.get("status") == "existing" for item in manifest),
        "skipped": sum(item.get("status") == "skipped" for item in manifest),
    }
    write_json(
        out_dir / "canvas-sync.json",
        redact_secrets({**summary, "endpoint_error_details": endpoint_errors}),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def command_submit_text(client: CanvasClient, args: argparse.Namespace) -> None:
    body = args.body if args.body is not None else pathlib.Path(args.body_file).read_text()
    response = client.request_json(
        "POST",
        f"/api/v1/courses/{args.course_id}/assignments/{args.assignment_id}/submissions",
        form_pairs=[
            ("submission[submission_type]", "online_text_entry"),
            ("submission[body]", body),
        ],
    )
    print(json.dumps(redact_secrets(response), ensure_ascii=False, indent=2))


def command_submit_url(client: CanvasClient, args: argparse.Namespace) -> None:
    response = client.request_json(
        "POST",
        f"/api/v1/courses/{args.course_id}/assignments/{args.assignment_id}/submissions",
        form_pairs=[
            ("submission[submission_type]", "online_url"),
            ("submission[url]", args.url),
        ],
    )
    print(json.dumps(redact_secrets(response), ensure_ascii=False, indent=2))


def command_submit_file(client: CanvasClient, args: argparse.Namespace) -> None:
    upload = client.upload_user_file(
        pathlib.Path(args.file), parent_folder_path=args.parent_folder_path
    )
    submission = client.request_json(
        "POST",
        f"/api/v1/courses/{args.course_id}/assignments/{args.assignment_id}/submissions",
        form_pairs=[
            ("submission[submission_type]", "online_upload"),
            ("submission[file_ids][]", str(upload["id"])),
        ],
    )
    print(
        json.dumps(
            redact_secrets({"uploaded_file": upload, "submission": submission}),
            ensure_ascii=False,
            indent=2,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Canvas LMS API CLI")
    parser.add_argument("--base-url", default=os.environ.get("CANVAS_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--token-command")
    parser.add_argument("--timeout", type=int, default=60)
    subparsers = parser.add_subparsers(dest="command", required=True)

    whoami = subparsers.add_parser("whoami", help="show the authenticated Canvas user")
    whoami.set_defaults(func=command_whoami)

    courses = subparsers.add_parser("courses", help="list all visible courses with pagination")
    courses.add_argument("--active-only", action="store_true")
    courses.set_defaults(func=command_courses)

    raw_get = subparsers.add_parser("raw-get", help="perform a sanitized Canvas API GET")
    raw_get.add_argument("path")
    raw_get.add_argument("--param", action="append")
    raw_get.add_argument("--paginate", action="store_true")
    raw_get.set_defaults(func=command_raw_get)

    sync_course = subparsers.add_parser(
        "sync-course", help="sync course metadata and files incrementally"
    )
    sync_course.add_argument("course_id")
    sync_course.add_argument("--out", required=True)
    sync_course.add_argument("--metadata-only", action="store_true")
    sync_course.add_argument("--force", action="store_true", help="redownload every visible file")
    sync_course.set_defaults(func=command_sync_course)

    submit_text = subparsers.add_parser("submit-text")
    submit_text.add_argument("course_id")
    submit_text.add_argument("assignment_id")
    body_group = submit_text.add_mutually_exclusive_group(required=True)
    body_group.add_argument("--body")
    body_group.add_argument("--body-file")
    submit_text.set_defaults(func=command_submit_text)

    submit_url = subparsers.add_parser("submit-url")
    submit_url.add_argument("course_id")
    submit_url.add_argument("assignment_id")
    submit_url.add_argument("--url", required=True)
    submit_url.set_defaults(func=command_submit_url)

    submit_file = subparsers.add_parser("submit-file")
    submit_file.add_argument("course_id")
    submit_file.add_argument("assignment_id")
    submit_file.add_argument("--file", required=True)
    submit_file.add_argument("--parent-folder-path")
    submit_file.set_defaults(func=command_submit_file)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        token = resolve_token(token_command=args.token_command)
        client = CanvasClient(args.base_url, token, timeout=args.timeout)
        args.func(client, args)
    except KeyboardInterrupt:
        eprint("interrupted")
        return 130
    except Exception as error:
        eprint(f"error: {type(error).__name__}: {redact_string(str(error))}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
