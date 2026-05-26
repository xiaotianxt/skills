# Local OCR Best Practices

## Local Tools

Known local tools:

- `/Users/yupeit/bin/ocr`: Swift CLI using macOS Apple Vision; supports image path, stdin image bytes, `capture`, and `fullscreen`.
- `/Users/yupeit/bin/ocr.py`: Gemini VLM OCR script; renders PDFs to images and returns Markdown page output.
- `/Users/yupeit/bin/ocr-doc`: document extraction router from this skill.
- `PyMuPDF/fitz`: preferred by `ocr-doc` for PDF profiling when available.
- `pdftotext`, `pdfinfo`, `pdfimages`: Poppler fallback tools for PDF text layer and metadata inspection.
- `uvx 'mineru[all]'`: local MinerU CLI.
- `tesseract`: traditional OCR fallback, usually lower priority than Apple Vision for screenshots on this Mac.

## `ocr-doc` Router Parameters

Common engine selection:

| Flag | Values | Default | Guidance |
|---|---|---:|---|
| `--engine` | `auto`, `native-text`, `apple-vision`, `gemini-vlm`, `mineru-local`, `mineru-api`, `mineru-agent` | `auto` | Use `auto` first. Pin an engine when testing quality or reproducing a workflow. |
| `--profile-only` | flag | off | Inspect file shape and recommended engine without extracting. Use this before touching unknown PDFs. |
| `--show-profile` | flag | off | Print profile and continue extraction. |
| `--no-cloud` | flag | off | Forbid all cloud upload paths. Use when confidentiality is unknown. |
| `--allow-cloud` | flag | off | Skip interactive upload confirmation. Use only after explicit user approval for that document. |
| `--out-dir` | path | derived from input and engine | Put outputs in a known directory for review/repro. |

Quality intent flags:

| Flag | Effect | Guidance |
|---|---|---|
| `--require-structure` | In `auto`, prefer MinerU over native text. | Use for Markdown with figures, layout artifacts, page markers, tables, or RAG ingestion. |
| `--need-formulas` | In `auto`, prefer MinerU. | Use for math, finance, papers, textbooks, and STEM slides. |
| `--need-tables` | In `auto`, prefer MinerU. | Use for reports, schedules, invoices, handbooks, papers, or any table-heavy PDF. |

MinerU shared flags:

| Flag | Maps to | Default | Guidance |
|---|---|---:|---|
| `--language` | MinerU `language` / local `-l` | `en` | Set explicitly. Use `en` for English docs and `ch` for Chinese docs. |
| `--enable-formula` / `--no-enable-formula` | `enable_formula` / local `-f` | true | Keep true for STEM/finance/math. Disable for prose if formula recognition creates noise. |
| `--enable-table` / `--no-enable-table` | `enable_table` / local `-t` | true | Keep true for table-bearing docs. Disable for prose if tables are irrelevant. |
| `--image-analysis` / `--no-image-analysis` | local `--image-analysis` | false | Turn on only when you want image/figure analysis from MinerU itself. Keep false if image assets are extracted by another pipeline. |
| `--timeout-seconds` | MinerU wait timeout env / router polling | 86400 | Keep long for local MinerU and large cloud jobs. |

Cloud MinerU flags:

| Flag | Maps to | Default | Guidance |
|---|---|---:|---|
| `--model-version` | `model_version` | `vlm` | Use `vlm` for official API quality, `pipeline` for speed/reproducibility, `MinerU-HTML` for HTML. |
| `--is-ocr` / `--no-is-ocr` | `is_ocr` | true | Use true for scans/mixed PDFs. Try false for born-digital PDFs with good text layers. |
| `--page-ranges` | `page_ranges` | omitted | Precision API only. Use 1-based comma-separated ranges, e.g. `1-5,9`. |
| `--poll-interval` | polling sleep | 5s | Increase for large jobs to reduce polling noise. |

Local MinerU CLI flags:

| Flag | Maps to MinerU CLI | Default | Guidance |
|---|---|---:|---|
| `--mineru-backend` | `-b/--backend` | `pipeline` | Use `pipeline` for full documents. Try `hybrid-auto-engine` or `vlm-auto-engine` only for selected pages where quality justifies time. |
| `--mineru-method` | `-m/--method` | `txt` | Use `txt` for PDFs with a good text layer. Use `ocr` for scans. Use `auto` when mixed and unsure. Applies to pipeline/hybrid backends. |
| `--start-page` | `-s` | omitted | 0-based local MinerU start page. Use to chunk or spot-check. |
| `--end-page` | `-e` | omitted | 0-based inclusive local MinerU end page. |

Important mismatch:

- Local MinerU page indexes are 0-based for `-s/-e`.
- Cloud Precision API `page_ranges` and Agent API `page_range` are 1-based.
- Precision API supports comma-separated ranges; Agent API supports a single page or `from-to`, not complex comma-separated ranges.

## PDF Shape Heuristics

Prefer native text extraction when:

- The PDF has a strong embedded text layer.
- The output can be plain Markdown/text.
- Tables do not need HTML structure.
- Formulas do not need semantic LaTeX.

Prefer MinerU when:

- You need table structure, formulas, images, page markers, layout JSON, or chunk-level artifacts.
- The PDF is scanned or mixed text/image.
- Text-layer extraction produces math/font garbage.
- You need a durable ingestion artifact for an agent/RAG pipeline.

Prefer VLM OCR when:

- Visual semantics matter more than deterministic layout.
- The page is a diagram, screenshot, form, slide, or mixed visual explanation.
- Local OCR sees text but misses intent.

Use cloud only when:

- The user explicitly says the document is non-confidential or otherwise permits upload.
- `--allow-cloud` is passed only after that permission.

Apple Vision note:

- Apple Vision may fail inside the Codex sandbox even for local images.
- If the error mentions `Foundation._GenericObjCError` or Vision request failure, rerun through an approved local command outside the sandbox.

Map/diagram note:

- MinerU can classify map-like pages as images and emit only an image reference.
- For visible map labels, compare `native-text` and Apple Vision OCR.

## MinerU Findings From Prior Local Work

For a technical 880-page book with a real text layer:

- `pdftotext -layout` produced good fast text-only output.
- `pipeline + txt` was the best full-book MinerU base because it preserved text-layer quality while adding formula/table recognition.
- `--formula true` was essential; plain text extraction could not recover custom math fonts into semantic LaTeX.
- `--table true` was worthwhile; table pages became HTML-like structured output instead of whitespace-only alignment.
- `--image-analysis false` was better when images were extracted separately by a dedicated PyMuPDF pipeline.
- `hybrid-auto-engine + txt` improved some formula formatting but was materially slower.
- `vlm-auto-engine` gave a useful second opinion on formula-heavy pages but was too expensive for full-book local runs.
- The best final artifact used `pipeline + txt` for the full book, then overlaid VLM pages for selected formula-heavy pages.

## Long Textbook Playbook

This playbook captures the John Hull textbook extraction lessons. Use it for long born-digital textbooks, lecture-note books, technical manuals, and similar PDFs.

### 1. First classify the PDF

Run:

```bash
ocr-doc file.pdf --profile-only --no-cloud
```

If the PDF has a strong text layer:

- Do not full-OCR it.
- Do not use `native-text` as the final artifact if formulas/tables matter.
- Use text-layer aware MinerU extraction so body text stays clean while MinerU adds formulas/tables/layout artifacts.

If the PDF is scanned or the text layer is bad:

- Use `--mineru-method ocr` locally, or cloud `--is-ocr`.
- Expect slower runtime and more spot-checking.

### 2. Full-book base extraction

For a long born-digital technical book, the best tested local base settings were:

```bash
python3 /Users/yupeit/dev/learn/quant/scripts/run_mineru_chunks.py \
  --pdf file.pdf \
  --output-dir out_chunks \
  --page-count PAGE_COUNT \
  --chunk-size 64 \
  --backend pipeline \
  --method txt \
  --lang en \
  --formula \
  --table \
  --no-image-analysis \
  --timeout-seconds 86400
```

Parameter rationale:

| Parameter | Setting | Why |
|---|---|---|
| `--backend` | `pipeline` | Fast enough for a full book and produced readable formulas. |
| `--method` | `txt` | Preserves real PDF text layer and avoids unnecessary OCR artifacts. |
| `--lang` | `en` | The tested textbook was English; set explicitly for OCR components. |
| `--formula` | true | Essential for semantic LaTeX; plain text extraction failed on custom math fonts. |
| `--table` | true | Produces structured table output instead of whitespace-only alignment. |
| `--image-analysis` | false | Better when figures/images are extracted separately and referenced by manifest. |
| `--chunk-size` | `64` | Completed reliably for an 880-page book in 14 chunks. |
| `--timeout-seconds` | `86400` | Avoids client timeout killing the temporary local MinerU service. |

Do not rely on one giant all-or-nothing MinerU run for a long textbook.

### 3. Merge and preserve auditability

After chunks finish, merge `*_content_list.json` instead of only concatenating Markdown:

```bash
python3 /Users/yupeit/dev/learn/quant/scripts/merge_mineru_chunks.py \
  --chunks-dir out_chunks \
  --out merged.md \
  --equations-out equations.json \
  --title "Book title - MinerU pipeline extraction"
```

Keep:

- Page markers.
- `mineru.log` per chunk.
- `chunk_status.json` per chunk.
- Equation JSON.
- Image/formula references when possible.

These artifacts make later quality review and selective reprocessing possible.

### 4. Formula-heavy page enhancement

For formula-heavy pages, do not rerun the whole book with VLM. Select pages using the equation manifest or manual review:

```bash
python3 /Users/yupeit/dev/learn/quant/scripts/run_mineru_selected_pages.py \
  --pdf file.pdf \
  --output-dir vlm_pages \
  --equations-json equations.json \
  --min-equations 8 \
  --backend vlm-auto-engine \
  --lang en \
  --formula \
  --table \
  --no-image-analysis \
  --timeout-seconds 86400
```

Then overlay selected page blocks:

```bash
python3 /Users/yupeit/dev/learn/quant/scripts/overlay_markdown_pages.py \
  --base merged.md \
  --overlay vlm_pages_merged.md \
  --out merged_vlm_formula_enhanced.md \
  --preserve-formula-image-markers
```

Prior measured result: the expanded VLM enhancement covered 139 pages containing about 55.9% of the original equation blocks; it took about 119.5 minutes across 90 chunks. This is useful as a targeted quality pass, not as the default full-book mode.

### 5. Backend tradeoffs for textbooks

| Backend/method | Use for | Avoid when |
|---|---|---|
| `pipeline + txt` | Full born-digital textbook base extraction. | Scanned books with no usable text layer. |
| `pipeline + ocr` | Scanned books or bad text layer. | Born-digital PDFs where OCR would degrade body text. |
| `hybrid-auto-engine + txt` | Selected pages where cleaner formulas justify slower runtime. | Whole-book extraction unless you have time budget. |
| `vlm-auto-engine` | Selected formula-heavy or semantically tricky pages. | Full long books by default; slower and still not perfect on complex variables/subscripts. |
| `native-text` | Fast preview, search, plain text, and baseline comparison. | Final artifact when formulas/tables/figures matter. |

### 6. Cloud equivalent for non-confidential textbooks

For official MinerU API on a non-confidential born-digital textbook, align cloud flags with the local finding:

```bash
ocr-doc file.pdf \
  --engine mineru-api \
  --allow-cloud \
  --model-version pipeline \
  --no-is-ocr \
  --enable-formula \
  --enable-table \
  --language en
```

Use `--page-ranges` to test representative slices before sending a whole document:

```bash
ocr-doc file.pdf --engine mineru-api --allow-cloud --page-ranges 31,203,337 --model-version pipeline --no-is-ocr
```

Then compare with `--model-version vlm` on the same pages if formulas or layout are weak. For a full textbook, do not assume `vlm + OCR` is superior just because `vlm` is the recommended generic cloud model.

### 7. Known limitations

- MinerU can misread complex formula subscripts, superscripts, or variables.
- Map-like/diagram-heavy pages may become image references without useful visible-label text.
- Textbook indexes, tables of contents, and dense tables need manual spot checks.
- Keep the original PDF page numbers visible in the output so questionable content can be traced back.

Reliability lessons:

- Local MinerU may start a temporary FastAPI service and write final artifacts only after a task finishes.
- Lack of output in the target directory does not always mean no progress; check temp output, logs, CPU, and local service health.
- Long runs should be chunked. A 64-page chunk size worked well for the 880-page book.
- Set long timeouts, especially `MINERU_TASK_RESULT_TIMEOUT_SECONDS=86400`.
- Keep each chunk directory, `mineru.log`, and `chunk_status.json`.

Relevant prior scripts in `/Users/yupeit/dev/learn/quant/scripts/`:

- `run_mineru_chunks.py`: resumable local MinerU chunk runner.
- `run_mineru_selected_pages.py`: rerun selected pages, useful for formula-heavy VLM overlays.
- `merge_mineru_chunks.py`: merge MinerU `*_content_list.json` chunks into page-marked Markdown.
- `overlay_markdown_pages.py`: replace selected page blocks with VLM-enhanced output.
- `export_pdf_text_images.py`: extract PDF text/images/captions for separate image-reference workflows.

## Quality Checks

Always spot-check against the source PDF:

- Front matter and table of contents.
- A text-heavy page.
- A table page.
- A formula-heavy page.
- A figure/caption page.
- A scanned or low-contrast page if present.
- Final pages or index.

For formulas, keep page markers and image references when possible so questionable variables/subscripts can be checked against the original PDF.
