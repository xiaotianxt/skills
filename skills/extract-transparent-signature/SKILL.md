---
name: extract-transparent-signature
description: Extract handwritten signatures from photos or scans into clean transparent PNG stamps for PDF signing, form filling, document annotation, or reuse. Use when the user provides an image path or image attachment containing dark ink on paper/background and asks to remove the background, make the signature transparent, create a PDF-ready signature stamp, split multiple signatures, or clean up photographed signature artifacts.
---

# Extract Transparent Signature

## Workflow

Use the bundled script first. It reads HEIC/JPG/PNG through `ffmpeg`, extracts dark ink, removes small specks and edge shadows, trims transparent padding, and writes RGBA PNG output without requiring Pillow or OpenCV.

Run from any working directory:

```bash
python3 /Users/yupeit/.codex/skills/extract-transparent-signature/scripts/extract_signature.py INPUT_IMAGE OUTPUT_PNG --solid
```

For photos with more than one signature, add `--split`:

```bash
python3 /Users/yupeit/.codex/skills/extract-transparent-signature/scripts/extract_signature.py INPUT_IMAGE OUTPUT_PNG --split --solid
```

The base output contains all detected ink. Split outputs are named like `OUTPUT-1.png`, `OUTPUT-2.png`, sorted from top to bottom.

## Parameter Guidance

- Start with `--solid` for PDF stamps; it keeps the transparent background but makes detected ink fully opaque black.
- Use `--threshold 100` to `--threshold 125` when paper shadows or background texture are being captured. Lower values remove more background.
- Use `--threshold 130` or higher when faint pen strokes are being dropped.
- Use `--min-area N` to remove specks; phone photos often work with `300` to `600`.
- Use `--margin N` to control transparent padding around the crop.
- Use `--keep-border` only when the actual signature touches the source image edge. By default, edge-touching dark components are treated as photo border/shadow artifacts.
- Use `--preserve-color` only when the original ink color matters; otherwise keep black output for document legibility.

## Validation

After generating output, verify that files are RGBA PNGs:

```bash
file OUTPUT_PNG
```

For visual inspection, composite over white or open the PNG in an image viewer. Transparent viewers may show the empty background as black or checkerboard; that is display behavior, not necessarily image content.
