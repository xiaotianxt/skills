---
name: edstem-course-materials
description: Download and incrementally update downloadable files from an authenticated EdStem course's Lessons and Resources pages. Use when the user wants a local archive or refresh of EdStem slides, PDFs, attachments, or other course materials; do not use for discussions, submissions, or lesson completion.
---

# EdStem Course Materials

Run the bundled sync script:

```bash
python3 scripts/sync_edstem.py "<course URL or ID>" "<destination>"
```

The browser must be logged into EdStem and connected through bro. Authentication stays in memory; the script uses read-only lesson endpoints and closes its tab.

Rerun the command to update. `.edstem-manifest.json` skips unchanged files; the script never deletes local files.

## Completion Check

- Require a zero exit status and `failed: 0` before calling the file sync complete.
- Inspect `.edstem-manifest.json`: `files` are local; `links` still need handling.
- For **all** materials, pass that manifest to `$panopto-mp4-bulk-download`, then report any remaining protected links.
- Do not append `view=1` to lesson API calls: it can alter lesson progress.
- Do not scrape discussions or download submissions unless the user separately asks for them.

Run the local check after changing the script:

```bash
python3 scripts/sync_edstem.py --self-test
```
