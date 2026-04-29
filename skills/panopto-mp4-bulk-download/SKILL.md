---
name: panopto-mp4-bulk-download
description: Extract real downloadable mp4 URLs from Panopto and similar HLS lecture players, then batch-download all lectures with manifests and retry logic. Use when users ask to download many class videos from a logged-in Panopto folder, to automate IDM-style URL discovery, or to derive fragmented.mp4 links from Viewer pages.
---

# Panopto MP4 Bulk Download

## Use This Workflow

1. Ensure the user is already logged into Panopto in `agent-browser`.
2. Use a headed persistent session (`~/.agent-browser-session`).
3. Pass the folder list URL to the bundled script.

## Run The Bundled Script

```bash
scripts/panopto_bulk_mp4.sh "<panopto-folder-list-url>" "<output-dir>" "<manifest-dir>"
```

Example:

```bash
scripts/panopto_bulk_mp4.sh \
  "https://scs.hosted.panopto.com/Panopto/Pages/Sessions/List.aspx?...#folderID=%22...%22" \
  "downloads/panopto_mp4" \
  "downloads/panopto_manifests"
```

## What The Script Does

1. Open the folder list page in `agent-browser`.
2. Extract all lecture `Viewer.aspx?id=...` links.
3. Open each lecture page and click Play.
4. Read browser `performance` entries to capture media URLs.
5. Prefer `/fragmented.mp4`; if absent, derive it from `/index.m3u8`.
6. Download all videos with `curl -L` retries.
7. Write manifests and failure reports.

## Required Behavior During Manual Automation

1. For every `agent-browser open`, always use `--headed --session <name>`.
2. If `open` fails, immediately run:

```bash
agent-browser --session <name> close
agent-browser --headed --session <name> open <url>
```

## Outputs

- `lecture_mp4_manifest.tsv`: lecture metadata and extracted mp4 URLs
- `extract_failed.txt`: lecture pages where URL extraction failed
- `download_failed.txt`: downloads that failed after retries

## References

- URL patterns and quick JS snippets: `references/url-patterns.md`
