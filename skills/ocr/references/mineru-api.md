# MinerU API Reference

Source docs:

- English docs: https://mineru.net/doc/docs/index_en/
- Chinese docs: https://mineru.org.cn/doc/docs/
- Limits: https://mineru.org.cn/doc/docs/limit/

As of 2026-05-17, MinerU exposes two cloud API families.

## Precision Extract API

Use for non-confidential production parsing where structured outputs, formulas, tables, and large files matter.

Limits from the official docs:

- Token required.
- File size: up to 200MB.
- Page count: up to 600 pages.
- Batch: up to 200 files.
- Models: `pipeline`, `vlm`, `MinerU-HTML`.
- Output: ZIP with Markdown and JSON artifacts; export can include docx/html/latex.

Key endpoints:

```text
POST https://mineru.net/api/v4/extract/task
GET  https://mineru.net/api/v4/extract/task/{task_id}
POST https://mineru.net/api/v4/file-urls/batch
POST https://mineru.net/api/v4/extract/task/batch
GET  https://mineru.net/api/v4/extract-results/batch/{batch_id}
```

For local files, prefer signed upload:

1. `POST /api/v4/file-urls/batch` with Bearer token.
2. `PUT` file bytes to the returned `upload_url`.
3. Poll `GET /api/v4/extract-results/batch/{batch_id}`.
4. Download and unzip the returned result ZIP.

Common request fields:

```json
{
  "enable_formula": true,
  "enable_table": true,
  "language": "en",
  "model_version": "vlm",
  "files": [
    {
      "name": "document.pdf",
      "data_id": "stable-id",
      "is_ocr": true,
      "page_ranges": "1-10,15"
    }
  ]
}
```

Notes:

- `enable_formula` and `enable_table` apply to `pipeline` and `vlm`; for `vlm`, formula behavior especially affects inline formula extraction.
- `language` defaults to `ch` in docs; set `en` for English documents.
- `page_ranges` is a comma-separated 1-based range string.
- Use `MinerU-HTML` for HTML files.

## Precision API Parameter Guide

Use this table when calling `ocr-doc --engine mineru-api` or editing `ocr_router.py`.

| Parameter | Router flag | Default | Scope | Guidance |
|---|---|---:|---|---|
| `model_version` | `--model-version` | `vlm` in router, `pipeline` in official docs | Precision API | Use `vlm` for best cloud quality on complex PDFs. Use `pipeline` when speed/cost is more important or when reproducing local pipeline behavior. Use `MinerU-HTML` only for HTML files. |
| `is_ocr` | `--is-ocr` / `--no-is-ocr` | `true` in router, `false` in official docs | PDF with `pipeline`/`vlm` | `true` forces OCR behavior and is safer for scans/mixed PDFs. For born-digital PDFs with good text layer, `false` may preserve text-layer fidelity and reduce OCR artifacts. |
| `enable_formula` | `--enable-formula` / `--no-enable-formula` | `true` | `pipeline`/`vlm` | Keep `true` for textbooks, papers, STEM slides, finance/math docs. Disable only for speed or if formulas are irrelevant. For `vlm`, official docs note it mainly affects inline formula extraction. |
| `enable_table` | `--enable-table` / `--no-enable-table` | `true` | `pipeline`/`vlm` | Keep `true` for papers, invoices, reports, syllabi, tables of contents, and spreadsheets exported as PDF. Disable for pure prose if table recognition creates noise. |
| `language` | `--language` | `en` in router, `ch` in official docs | OCR recognition | Set explicitly. Use `en` for English, `ch` for Chinese, and supported language codes from MinerU docs for other languages. Wrong language mostly hurts OCR pages. |
| `page_ranges` | `--page-ranges` | omitted | Precision API local upload | Use to reduce cost/time or parse selected pages. Precision API supports comma-separated 1-based ranges such as `1-10,15`. |
| `files[].name` | derived from path | input filename | local upload | Must include a useful extension because MinerU uses it to infer file type. |
| `files[].data_id` | generated UUID | UUID | local upload | Stable caller-side ID for matching results in batch polling. Use deterministic IDs if integrating with a larger pipeline. |
| `url` / `files[].url` | not exposed by current router for local files | n/a | URL parse | Use URL parse only for already-public/non-confidential remote files. Local files should use signed upload. |

Parameter selection:

- Born-digital PDF, plain text needed: do not use cloud MinerU; use `native-text`.
- Born-digital textbook or long technical PDF with formulas/tables: start with `model_version=pipeline`, `is_ocr=false`, `enable_formula=true`, `enable_table=true`; test `vlm` only on representative difficult pages before scaling up.
- Born-digital short/complex PDF where generic cloud quality matters more than reproducing text-layer behavior: `model_version=vlm`, `is_ocr=false` is a reasonable first test.
- Scanned/mixed PDF: `model_version=vlm`, `is_ocr=true`, `enable_formula/table` as needed.
- HTML: `model_version=MinerU-HTML`; formula/table/OCR flags are not the primary controls.
- Selected pages: pass `--page-ranges` for cloud, or `--start-page/--end-page` for local MinerU.

## Agent Lightweight API

Use for quick, non-confidential, agent-style parsing.

Limits from the official docs:

- No token required.
- IP rate-limited.
- File size: up to 10MB.
- Page count: up to 20 pages.
- Single file only.
- Output: Markdown CDN link only.

Endpoints:

```text
POST https://mineru.net/api/v1/agent/parse/url
POST https://mineru.net/api/v1/agent/parse/file
GET  https://mineru.net/api/v1/agent/parse/{task_id}
```

Local file flow:

1. `POST /api/v1/agent/parse/file` with `file_name`, `language`, `page_range`, `enable_table`, `is_ocr`, `enable_formula`.
2. Upload file bytes with `PUT` to returned `data.file_url`.
3. Poll `GET /api/v1/agent/parse/{task_id}`.
4. Download returned Markdown URL when `data.state == done`.

## Agent API Parameter Guide

| Parameter | Router support | Default | Scope | Guidance |
|---|---|---:|---|---|
| `language` | current router uses default unless extended | `ch` in docs | PDF only | Same language guidance as Precision API. |
| `page_range` | not yet exposed by router | omitted | PDF only | Agent API supports either `from-to` such as `1-10` or a single page such as `5`; comma-separated complex ranges are not supported. |
| `enable_table` | current router uses API default unless extended | `true` | PDF only | Leave true unless table detection creates noise. |
| `is_ocr` | current router uses API default unless extended | `false` | PDF only | Set true for scans if extending the router. |
| `enable_formula` | current router uses API default unless extended | `true` | PDF only | Leave true for STEM papers; disable for prose-only documents if speed/noise matters. |
| `file_name` | derived from path | required for file upload | file upload | Include extension. |

The Agent API is intentionally narrow: single file, small size/page limits, no token, and Markdown-only output. Use it for quick agent ingestion, not durable production extraction.

Observed task states include:

```text
waiting-file
uploading
pending
running
done
failed
```

## Credential Rules

Prefer Keychain for local-only credentials:

```bash
keychain-secret get codex.mineru credential
```

The router also accepts:

```bash
MINERU_API_TOKEN=...
MINERU_TOKEN=...
```

Do not write MinerU tokens to source files, `.env` files, issue text, logs, or final responses.
