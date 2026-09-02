---
name: panopto-mp4-bulk-download
description: Download Panopto lecture recordings from authenticated Viewer links, including links recorded in an EdStem materials manifest. Use for local lecture-video archives or incremental Panopto downloads; do not use for uploading, sharing, or changing recordings.
---

# Panopto MP4 Download

Run the bundled downloader with one or more Viewer URLs or an EdStem `.edstem-manifest.json`:

```bash
python3 scripts/panopto_download.py <source>... --output-dir <directory>
```

The user must already be logged into Panopto in the browser connected to bro. Media discovery briefly uses a foreground tab because Panopto does not load delivery data reliably in background tabs; the script closes every tab it creates.

Require a zero exit status and verify the MP4 before declaring success. Reruns skip files recorded in `.panopto-manifest.json`; interrupted downloads resume from `.part` files.

Never print or persist temporary signed media URLs. The manifest stores only Viewer URLs, local paths, sizes, and hashes.

After changing the script, run:

```bash
python3 scripts/panopto_download.py --self-test
```
