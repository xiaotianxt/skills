---
name: ocr
description: Extract text, Markdown, tables, formulas, and structured content from PDFs, scanned documents, screenshots, and images using the best available local or cloud OCR route. Use when Codex needs OCR, PDF text-layer extraction, MinerU local or official API parsing, VLM document parsing, table/formula extraction, scanned PDF handling, or when deciding whether a PDF should be read directly, OCRed, parsed by MinerU, or uploaded to a cloud API.
---

# OCR

Use this skill to choose and run the right document extraction path instead of defaulting to OCR for every PDF.

## Quick Start

Use the router first for PDFs and files where the best path is unclear:

```bash
ocr-doc /path/to/file.pdf --profile-only
```

The installed wrapper is:

```bash
/Users/yupeit/bin/ocr-doc
```

It runs:

```bash
/Users/yupeit/dev/skills/skills/ocr/scripts/ocr-router
```

The wrapper uses the skill-local virtualenv at `.venv/` when present. If the venv is missing, recreate it:

```bash
python3 -m venv /Users/yupeit/dev/skills/skills/ocr/.venv
/Users/yupeit/dev/skills/skills/ocr/.venv/bin/python -m pip install requests pymupdf pyyaml
```

## Decision Tree

1. For screenshots or single images, use the offline Apple Vision CLI:

```bash
ocr /path/to/image.png
ocr capture
ocr fullscreen
```

2. For a PDF with a strong text layer and no need for formulas/tables/layout JSON, use native text extraction:

```bash
ocr-doc file.pdf --engine native-text
```

Use `--show-profile` when you want the profile printed and extraction to continue. Use `--profile-only` when you only want the recommendation.

3. For PDFs where tables, formulas, layout, page markers, or image assets matter, prefer MinerU:

```bash
ocr-doc file.pdf --engine mineru-local --require-structure --need-formulas --need-tables
```

4. For non-confidential documents where local MinerU is too slow or unavailable, use the official MinerU API only after explicit upload permission:

```bash
ocr-doc file.pdf --engine mineru-api --allow-cloud --model-version vlm
```

5. For small non-confidential documents needing a quick agent-friendly Markdown result, use MinerU Agent API:

```bash
ocr-doc file.pdf --engine mineru-agent --allow-cloud
```

6. For images/PDFs where semantic visual understanding is more important than deterministic layout, use Gemini VLM:

```bash
ocr-doc file.pdf --engine gemini-vlm --allow-cloud
```

## Cloud Safety

Never upload confidential, private, school-restricted, client, credential-bearing, or unknown-sensitivity documents to cloud OCR.

The router refuses cloud upload unless either:

- The user interactively types `UPLOAD`.
- The caller passes `--allow-cloud`, which must only be used after the user explicitly allows cloud upload for that document.

Use `--no-cloud` when confidentiality is unknown:

```bash
ocr-doc file.pdf --no-cloud
```

MinerU official API credentials are read from `MINERU_API_TOKEN` / `MINERU_TOKEN`, then Keychain service `codex.mineru`, account `credential`. Never print the token.

## MinerU Local Lessons

For long technical books with a real PDF text layer, do not run full OCR blindly. Use MinerU `pipeline + txt` as the base when formulas/tables matter:

```bash
uvx 'mineru[all]' -p file.pdf -o out -b pipeline -m txt -l en -f true -t true --image-analysis false
```

For full textbooks or long technical PDFs, do not use a single `ocr-doc --engine mineru-local` whole-book run as the default. Use chunked local MinerU scripts or an equivalent chunked workflow:

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

Then merge `*_content_list.json` chunks with the existing merge script. This is aligned with the prior John Hull textbook workflow: `pipeline + txt` for the whole book, then `vlm-auto-engine` only on selected formula-heavy pages for overlay.

For cloud MinerU on a non-confidential born-digital textbook, override the generic cloud defaults: start with `--model-version pipeline --no-is-ocr --enable-formula --enable-table`, then compare `vlm` on selected difficult pages. Do not default a full textbook to `vlm + OCR` without a cost/quality reason.

For large documents, chunk the run and keep logs; local MinerU may wait for the final result before writing the user-facing output. A previous 880-page technical book worked best with 64-page chunks and long timeouts.

For map-like or diagram-heavy pages, MinerU may output only an image reference. If visible labels are the goal, compare native text-layer extraction and Apple Vision OCR.

Apple Vision can fail inside a restricted Codex sandbox with a Foundation/Vision error. In that case rerun through the approved local entrypoint `/Users/yupeit/bin/ocr-doc` or `/Users/yupeit/bin/ocr` outside the sandbox.

Read [references/local-ocr-best-practices.md](references/local-ocr-best-practices.md) before doing long or quality-sensitive extraction.

## References

- Read [references/mineru-api.md](references/mineru-api.md) before changing MinerU official/agent API calls.
- Read [references/local-ocr-best-practices.md](references/local-ocr-best-practices.md) for local tool choices, PDF shape heuristics, and previous MinerU findings.
