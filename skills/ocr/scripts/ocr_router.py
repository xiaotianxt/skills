#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - fallback path for minimal hosts
    fitz = None

try:
    import requests
except ImportError:  # pragma: no cover - fallback path for minimal hosts
    requests = None


MINERU_BASE_URL = "https://mineru.net"
MINERU_TOKEN_KEYCHAIN = ("codex.mineru", "credential")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}
PDF_SUFFIXES = {".pdf"}
CLOUD_DOC_SUFFIXES = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".html",
    ".htm",
}


@dataclass
class PdfProfile:
    path: Path
    size_bytes: int
    page_count: int | None
    sample_pages: list[int]
    sample_text_chars: int
    pages_with_text: int
    sample_math_hits: int
    image_count: int | None

    @property
    def text_page_ratio(self) -> float:
        if not self.sample_pages:
            return 0.0
        return self.pages_with_text / len(self.sample_pages)

    @property
    def avg_text_chars(self) -> float:
        if not self.sample_pages:
            return 0.0
        return self.sample_text_chars / len(self.sample_pages)

    @property
    def has_good_text_layer(self) -> bool:
        return self.text_page_ratio >= 0.75 and self.avg_text_chars >= 250


def eprint(*parts: object) -> None:
    print(*parts, file=sys.stderr)


def human_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f}{unit}" if unit != "B" else f"{int(value)}B"
        value /= 1024
    return f"{size}B"


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"Required tool not found on PATH: {name}")
    return path


def run_text(cmd: list[str], *, timeout: int = 120) -> str:
    proc = subprocess.run(
        cmd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout


def text_char_count(value: str) -> int:
    return sum(1 for ch in value if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")


def math_hit_count(value: str) -> int:
    patterns = [
        r"\b(equation|formula|theorem|lemma|corollary)\b",
        r"[=+\-*/]\s*[A-Za-z0-9(]",
        r"[∑∫√≤≥≈≠∞σΣΔθλμ]",
        r"\b[A-Za-z]_[A-Za-z0-9]\b",
    ]
    return sum(len(re.findall(pattern, value, flags=re.IGNORECASE)) for pattern in patterns)


def pdf_page_count(path: Path) -> int | None:
    if fitz is not None:
        try:
            with fitz.open(path) as doc:
                return len(doc)
        except Exception:
            pass
    try:
        out = run_text(["pdfinfo", str(path)])
    except Exception:
        return None
    for line in out.splitlines():
        if line.startswith("Pages:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def sample_pages(page_count: int | None) -> list[int]:
    if not page_count or page_count <= 0:
        return [1]
    candidates = [1, 2, max(1, page_count // 2), page_count]
    return sorted({p for p in candidates if 1 <= p <= page_count})


def pdftotext_page(path: Path, page: int) -> str:
    return run_text(
        ["pdftotext", "-f", str(page), "-l", str(page), "-layout", "-enc", "UTF-8", str(path), "-"],
        timeout=120,
    )


def pdf_image_count(path: Path) -> int | None:
    if fitz is not None:
        try:
            with fitz.open(path) as doc:
                return sum(len(page.get_images(full=True)) for page in doc)
        except Exception:
            pass
    if not shutil.which("pdfimages"):
        return None
    try:
        out = run_text(["pdfimages", "-list", str(path)], timeout=120)
    except Exception:
        return None
    lines = [line for line in out.splitlines() if line.strip()]
    if len(lines) <= 2:
        return 0
    return max(0, len(lines) - 2)


def inspect_pdf(path: Path) -> PdfProfile:
    page_count = pdf_page_count(path)
    pages = sample_pages(page_count)
    total_chars = 0
    pages_with_text = 0
    total_math_hits = 0
    if fitz is not None:
        try:
            with fitz.open(path) as doc:
                for page in pages:
                    try:
                        text = doc[page - 1].get_text("text")
                    except Exception:
                        text = ""
                    chars = text_char_count(text)
                    total_chars += chars
                    total_math_hits += math_hit_count(text)
                    if chars >= 80:
                        pages_with_text += 1
        except Exception:
            total_chars = 0
            pages_with_text = 0
            total_math_hits = 0
    else:
        require_tool("pdfinfo")
        require_tool("pdftotext")
        for page in pages:
            try:
                text = pdftotext_page(path, page)
            except Exception:
                text = ""
            chars = text_char_count(text)
            total_chars += chars
            total_math_hits += math_hit_count(text)
            if chars >= 80:
                pages_with_text += 1
    return PdfProfile(
        path=path,
        size_bytes=path.stat().st_size,
        page_count=page_count,
        sample_pages=pages,
        sample_text_chars=total_chars,
        pages_with_text=pages_with_text,
        sample_math_hits=total_math_hits,
        image_count=pdf_image_count(path),
    )


def print_profile(profile: PdfProfile) -> None:
    payload = {
        "path": str(profile.path),
        "size": human_size(profile.size_bytes),
        "page_count": profile.page_count,
        "sample_pages": profile.sample_pages,
        "text_page_ratio": round(profile.text_page_ratio, 3),
        "avg_text_chars_per_sample_page": round(profile.avg_text_chars, 1),
        "sample_math_hits": profile.sample_math_hits,
        "image_count": profile.image_count,
        "has_good_text_layer": profile.has_good_text_layer,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def default_out_dir(input_path: Path, engine: str) -> Path:
    return input_path.with_suffix("").with_name(f"{input_path.stem}_ocr_{engine}")


def confirm_cloud_upload(path_or_url: str, service: str, args: argparse.Namespace) -> None:
    if args.allow_cloud:
        return
    if args.no_cloud:
        raise SystemExit(f"{service} requires uploading input to a cloud service, but --no-cloud was set.")

    eprint("")
    eprint("Cloud upload confirmation required.")
    eprint(f"Service: {service}")
    eprint(f"Input: {path_or_url}")
    eprint("Only continue for non-confidential documents that you are allowed to upload.")
    if not sys.stdin.isatty():
        raise SystemExit("Refusing cloud upload in non-interactive mode. Re-run with --allow-cloud if this is intended.")
    answer = input("Type UPLOAD to continue: ").strip()
    if answer != "UPLOAD":
        raise SystemExit("Cloud upload cancelled.")


def keychain_secret(service: str, account: str) -> str | None:
    tool = shutil.which("keychain-secret")
    if not tool:
        return None
    proc = subprocess.run(
        [tool, "get", service, account],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.replace("\r", "").split("\n", 1)[0] or None


def mineru_token() -> str:
    token = os.environ.get("MINERU_API_TOKEN") or os.environ.get("MINERU_TOKEN")
    if token:
        return token
    token = keychain_secret(*MINERU_TOKEN_KEYCHAIN)
    if token:
        return token
    raise SystemExit(
        "MinerU API token not found. Set MINERU_API_TOKEN or store it in Keychain as "
        "service codex.mineru account credential."
    )


def http_json(method: str, url: str, payload: dict[str, Any] | None, headers: dict[str, str], timeout: int = 60) -> dict[str, Any]:
    if requests is not None:
        try:
            response = requests.request(method, url, json=payload, headers=headers, timeout=timeout)
        except requests.RequestException as exc:
            raise RuntimeError(f"HTTP request failed for {url}: {exc}") from exc
        if response.status_code >= 400:
            raise RuntimeError(f"HTTP {response.status_code} from {url}: {response.text[:800]}")
        return response.json()

    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json", **headers}
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body[:800]}") from exc
    return json.loads(body)


def curl_upload_file(path: Path, url: str) -> None:
    if requests is not None:
        with path.open("rb") as handle:
            response = requests.put(url, data=handle, timeout=300)
        if response.status_code >= 400:
            raise RuntimeError(f"Signed URL upload failed: HTTP {response.status_code} {response.text[:500]}")
        return

    require_tool("curl")
    proc = subprocess.run(["curl", "-sS", "-f", "-X", "PUT", "-T", str(path), url], check=False)
    if proc.returncode != 0:
        raise RuntimeError("Signed URL upload failed.")


def curl_download(url: str, out: Path) -> None:
    if requests is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=300) as response:
            if response.status_code >= 400:
                raise RuntimeError(f"Download failed: HTTP {response.status_code} {response.text[:500]}")
            with out.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        return

    require_tool("curl")
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(["curl", "-L", "-sS", "-f", "-o", str(out), url], check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Download failed: {url}")


def extract_data(response: dict[str, Any]) -> dict[str, Any]:
    data = response.get("data")
    if isinstance(data, dict):
        return data
    raise RuntimeError(f"Unexpected MinerU response: {response}")


def first_url_value(value: Any, preferred_keys: tuple[str, ...], require_zip: bool = False) -> str | None:
    def is_usable(candidate: Any) -> bool:
        return isinstance(candidate, str) and (not require_zip or ".zip" in candidate.lower())

    if is_usable(value):
        return value
    if isinstance(value, dict):
        for key in preferred_keys:
            candidate = value.get(key)
            if is_usable(candidate):
                return candidate
        for candidate in value.values():
            found = first_url_value(candidate, preferred_keys, require_zip=require_zip)
            if found:
                return found
    if isinstance(value, list):
        for candidate in value:
            found = first_url_value(candidate, preferred_keys, require_zip=require_zip)
            if found:
                return found
    return None


def run_native_text(input_path: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    if shutil.which("pdftotext"):
        raw = run_text(["pdftotext", "-layout", "-enc", "UTF-8", str(input_path), "-"], timeout=900)
        pages = raw.split("\f")
        note = "Extracted from the PDF text layer with pdftotext -layout."
    elif fitz is not None:
        with fitz.open(input_path) as doc:
            pages = [page.get_text("text") for page in doc]
        note = "Extracted from the PDF text layer with PyMuPDF."
    else:
        raise SystemExit("native-text requires either pdftotext or PyMuPDF.")
    lines = [f"# {input_path.stem}", "", f"<!-- {note} -->", ""]
    for idx, page_text in enumerate(pages, start=1):
        if not page_text.strip() and idx == len(pages):
            continue
        lines.append(f"<!-- PDF_PAGE {idx:04d} -->")
        lines.append(f"## PDF Page {idx}")
        lines.append("")
        lines.append(page_text.strip())
        lines.append("")
    out_path = out_dir / "full.md"
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out_path


def run_apple_vision(input_path: Path, out_dir: Path, language: str | None) -> Path:
    tool = Path("/Users/yupeit/bin/ocr")
    if not tool.exists():
        raise SystemExit("Apple Vision OCR tool not found at /Users/yupeit/bin/ocr")
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(tool)]
    if language and language != "auto":
        cmd.extend(["--language", language])
    cmd.append(str(input_path))
    text = run_text(cmd, timeout=300)
    out_path = out_dir / f"{input_path.stem}.txt"
    out_path.write_text(text, encoding="utf-8")
    return out_path


def run_gemini_vlm(input_path: Path, out_dir: Path, args: argparse.Namespace) -> Path:
    confirm_cloud_upload(str(input_path), "Gemini VLM via /Users/yupeit/bin/ocr.py", args)
    tool = Path("/Users/yupeit/bin/ocr.py")
    if not tool.exists():
        raise SystemExit("Gemini OCR script not found at /Users/yupeit/bin/ocr.py")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "full.md"
    cmd = [
        str(tool),
        str(input_path),
        "--output",
        str(out_path),
        "--concurrent",
        str(args.concurrent),
        "--model",
        args.vlm_model,
    ]
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        raise SystemExit(f"Gemini VLM OCR failed with exit code {proc.returncode}")
    return out_path


def run_local_mineru(input_path: Path, out_dir: Path, args: argparse.Namespace) -> Path:
    require_tool("uvx")
    out_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("MINERU_TASK_RESULT_TIMEOUT_SECONDS", str(args.timeout_seconds))
    env.setdefault("MINERU_TASK_RESULT_DOWNLOAD_TIMEOUT_SECONDS", "1800")
    env.setdefault("MINERU_LOCAL_API_STARTUP_TIMEOUT_SECONDS", "600")

    cmd = [
        "uvx",
        "mineru[all]",
        "-p",
        str(input_path),
        "-o",
        str(out_dir),
        "-b",
        args.mineru_backend,
        "-l",
        args.language,
        "-f",
        "true" if args.enable_formula else "false",
        "-t",
        "true" if args.enable_table else "false",
        "--image-analysis",
        "true" if args.image_analysis else "false",
    ]
    if args.mineru_method:
        cmd.extend(["-m", args.mineru_method])
    if args.start_page is not None:
        cmd.extend(["-s", str(args.start_page)])
    if args.end_page is not None:
        cmd.extend(["-e", str(args.end_page)])

    log_path = out_dir / "mineru-local.log"
    with log_path.open("w", encoding="utf-8") as log:
        log.write("$ " + " ".join(cmd) + "\n\n")
        log.flush()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        assert proc.stdout is not None
        for line in proc.stdout:
            log.write(line)
            log.flush()
            if "Completed batch" in line or "Error:" in line or "Timed out" in line:
                print(line.rstrip(), flush=True)
        code = proc.wait()
    if code != 0:
        raise SystemExit(f"Local MinerU failed with exit code {code}; see {log_path}")
    markdowns = sorted(out_dir.rglob("*.md"))
    return markdowns[0] if markdowns else out_dir


def run_mineru_agent(input_path: Path, out_dir: Path, args: argparse.Namespace) -> Path:
    profile = inspect_pdf(input_path) if input_path.suffix.lower() == ".pdf" else None
    if input_path.stat().st_size > 10 * 1024 * 1024 or (profile and profile.page_count and profile.page_count > 20):
        raise SystemExit("MinerU agent API is limited to 10MB/20 pages. Use --engine mineru-api instead.")
    confirm_cloud_upload(str(input_path), "MinerU agent parse API", args)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"file_name": input_path.name}
    created = http_json("POST", f"{MINERU_BASE_URL}/api/v1/agent/parse/file", payload, {})
    data = extract_data(created)
    task_id = data.get("task_id") or data.get("id")
    upload_url = data.get("file_url") or data.get("upload_url")
    if not task_id or not upload_url:
        raise RuntimeError(f"Unexpected MinerU agent create response: {created}")
    curl_upload_file(input_path, upload_url)
    result = poll_agent_task(str(task_id), args.poll_interval, args.timeout_seconds)
    md_url = result.get("full_md_url") or result.get("md_url") or result.get("markdown_url")
    if not md_url:
        raise RuntimeError(f"Agent task completed but no Markdown URL was found: {result}")
    out_path = out_dir / "full.md"
    curl_download(md_url, out_path)
    return out_path


def poll_agent_task(task_id: str, interval: float, timeout_seconds: int) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    while True:
        response = http_json("GET", f"{MINERU_BASE_URL}/api/v1/agent/parse/{task_id}", None, {})
        data = extract_data(response)
        state = str(data.get("state") or data.get("status") or "").lower()
        if state in {"done", "completed", "success", "succeeded"}:
            return data
        if state in {"failed", "error"}:
            raise RuntimeError(f"MinerU agent task failed: {data}")
        if time.time() > deadline:
            raise TimeoutError(f"Timed out waiting for MinerU agent task {task_id}")
        eprint(f"MinerU agent task {task_id}: {state or 'processing'}")
        time.sleep(interval)


def run_mineru_api(input_path: Path, out_dir: Path, args: argparse.Namespace) -> Path:
    confirm_cloud_upload(str(input_path), "MinerU official API", args)
    out_dir.mkdir(parents=True, exist_ok=True)
    token = mineru_token()
    headers = {"Authorization": f"Bearer {token}"}

    data_id = str(uuid.uuid4())
    file_payload: dict[str, Any] = {
        "name": input_path.name,
        "data_id": data_id,
        "is_ocr": args.is_ocr,
    }
    if args.page_ranges:
        file_payload["page_ranges"] = args.page_ranges

    create_payload = {
        "enable_formula": args.enable_formula,
        "enable_table": args.enable_table,
        "language": args.language,
        "model_version": args.model_version,
        "files": [file_payload],
    }
    created = http_json("POST", f"{MINERU_BASE_URL}/api/v4/file-urls/batch", create_payload, headers)
    created_data = extract_data(created)
    batch_id = created_data.get("batch_id")
    files = created_data.get("file_urls") or created_data.get("files") or []
    if not batch_id or not files:
        raise RuntimeError(f"Unexpected MinerU signed URL response: {created}")
    upload_url = first_url_value(files, ("upload_url", "file_url", "url"))
    if not upload_url:
        raise RuntimeError(f"Signed URL response did not include upload_url: {created}")

    eprint(f"Uploading to MinerU batch {batch_id} ...")
    curl_upload_file(input_path, upload_url)
    result = poll_mineru_batch(str(batch_id), data_id, headers, args.poll_interval, args.timeout_seconds)
    zip_url = first_url_value(result, ("full_zip_url", "zip_url"), require_zip=True)
    if not zip_url:
        raise RuntimeError(f"MinerU task completed but no zip URL was found: {result}")

    zip_path = out_dir / "mineru_result.zip"
    curl_download(str(zip_url), zip_path)
    extract_dir = out_dir / "mineru_result"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_dir)
    markdowns = sorted(extract_dir.rglob("*.md"))
    return markdowns[0] if markdowns else extract_dir


def poll_mineru_batch(
    batch_id: str,
    data_id: str,
    headers: dict[str, str],
    interval: float,
    timeout_seconds: int,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    while True:
        response = http_json("GET", f"{MINERU_BASE_URL}/api/v4/extract-results/batch/{batch_id}", None, headers)
        data = extract_data(response)
        results = data.get("extract_result") or data.get("results") or data.get("files") or []
        if isinstance(results, dict):
            results = [results]
        if not isinstance(results, list):
            results = []
        target = None
        for item in results:
            if not isinstance(item, dict):
                continue
            if item.get("data_id") == data_id or not target:
                target = item
        state = str((target or data).get("state") or (target or data).get("status") or "").lower()
        if state in {"done", "completed", "success", "succeeded"}:
            return target or data
        if state in {"failed", "error"}:
            raise RuntimeError(f"MinerU batch task failed: {target or data}")
        if time.time() > deadline:
            raise TimeoutError(f"Timed out waiting for MinerU batch {batch_id}")
        eprint(f"MinerU batch {batch_id}: {state or 'processing'}")
        time.sleep(interval)


def choose_engine(input_path: Path, args: argparse.Namespace) -> tuple[str, PdfProfile | None]:
    suffix = input_path.suffix.lower()
    if args.engine != "auto":
        profile = inspect_pdf(input_path) if suffix == ".pdf" and args.show_profile else None
        return args.engine, profile
    if suffix in IMAGE_SUFFIXES:
        return "apple-vision", None
    if suffix not in PDF_SUFFIXES:
        return "mineru-api", None

    profile = inspect_pdf(input_path)
    if args.require_structure or args.need_formulas or args.need_tables:
        if shutil.which("uvx"):
            return "mineru-local", profile
        return "mineru-api", profile
    if profile.has_good_text_layer:
        return "native-text", profile
    if shutil.which("uvx"):
        return "mineru-local", profile
    if profile.size_bytes <= 10 * 1024 * 1024 and (profile.page_count or 999999) <= 20:
        return "mineru-agent", profile
    return "mineru-api", profile


def print_file_profile(input_path: Path, engine: str, profile: PdfProfile | None) -> None:
    if profile is not None:
        payload = {
            "recommended_engine": engine,
            "path": str(profile.path),
            "size": human_size(profile.size_bytes),
            "page_count": profile.page_count,
            "sample_pages": profile.sample_pages,
            "text_page_ratio": round(profile.text_page_ratio, 3),
            "avg_text_chars_per_sample_page": round(profile.avg_text_chars, 1),
            "sample_math_hits": profile.sample_math_hits,
            "image_count": profile.image_count,
            "has_good_text_layer": profile.has_good_text_layer,
        }
    else:
        payload = {
            "recommended_engine": engine,
            "path": str(input_path),
            "size": human_size(input_path.stat().st_size),
            "suffix": input_path.suffix.lower(),
        }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route OCR/document extraction to the best local or MinerU workflow.")
    parser.add_argument("input", type=Path, help="Local PDF/image/document path")
    parser.add_argument("--engine", choices=["auto", "native-text", "apple-vision", "gemini-vlm", "mineru-local", "mineru-api", "mineru-agent"], default="auto")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--show-profile", action="store_true")
    parser.add_argument("--profile-only", action="store_true", help="Inspect the file and recommended engine without extracting")
    parser.add_argument("--allow-cloud", action="store_true", help="Allow upload without an interactive confirmation prompt")
    parser.add_argument("--no-cloud", action="store_true", help="Forbid cloud OCR/API upload")
    parser.add_argument("--language", default="en")
    parser.add_argument("--need-formulas", action="store_true")
    parser.add_argument("--need-tables", action="store_true")
    parser.add_argument("--require-structure", action="store_true", help="Prefer MinerU structured output over plain text layer extraction")
    parser.add_argument("--enable-formula", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--enable-table", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--image-analysis", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--model-version", default="vlm", help="MinerU official API model_version, e.g. vlm, pipeline, MinerU-HTML")
    parser.add_argument("--is-ocr", action=argparse.BooleanOptionalAction, default=True, help="MinerU official API OCR flag")
    parser.add_argument("--page-ranges", help="MinerU API page ranges string, e.g. 1-5,9")
    parser.add_argument("--mineru-backend", default="pipeline")
    parser.add_argument("--mineru-method", default="txt")
    parser.add_argument("--start-page", type=int, help="0-based local MinerU start page")
    parser.add_argument("--end-page", type=int, help="0-based local MinerU inclusive end page")
    parser.add_argument("--vlm-model", default="gemini-2.5-flash-lite")
    parser.add_argument("--concurrent", type=int, default=2)
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--timeout-seconds", type=int, default=86400)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")
    if input_path.suffix.lower() not in CLOUD_DOC_SUFFIXES and args.engine in {"mineru-api", "mineru-agent"}:
        raise SystemExit(f"MinerU cloud engine does not support this suffix: {input_path.suffix}")

    engine, profile = choose_engine(input_path, args)
    if args.profile_only:
        print_file_profile(input_path, engine, profile)
        return 0
    if args.show_profile and profile is not None:
        print_profile(profile)
    elif profile is not None:
        eprint(
            "PDF profile:",
            f"pages={profile.page_count}",
            f"text_layer={profile.has_good_text_layer}",
            f"avg_chars={profile.avg_text_chars:.1f}",
            f"images={profile.image_count}",
        )
    eprint(f"Selected engine: {engine}")

    out_dir = (args.out_dir.expanduser().resolve() if args.out_dir else default_out_dir(input_path, engine))
    if engine == "native-text":
        out_path = run_native_text(input_path, out_dir)
    elif engine == "apple-vision":
        out_path = run_apple_vision(input_path, out_dir, args.language)
    elif engine == "gemini-vlm":
        out_path = run_gemini_vlm(input_path, out_dir, args)
    elif engine == "mineru-local":
        out_path = run_local_mineru(input_path, out_dir, args)
    elif engine == "mineru-api":
        out_path = run_mineru_api(input_path, out_dir, args)
    elif engine == "mineru-agent":
        out_path = run_mineru_agent(input_path, out_dir, args)
    else:
        raise SystemExit(f"Unknown engine: {engine}")

    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
