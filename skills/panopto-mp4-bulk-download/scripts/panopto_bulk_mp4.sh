#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/panopto_bulk_mp4.sh "<panopto-folder-list-url>" [output-dir] [manifest-dir]

Example:
  scripts/panopto_bulk_mp4.sh \
    "https://scs.hosted.panopto.com/Panopto/Pages/Sessions/List.aspx?...#folderID=%22...%22" \
    downloads/panopto_mp4 \
    downloads/panopto_manifests
USAGE
}

if ! command -v agent-browser >/dev/null 2>&1; then
  echo "agent-browser is required but not installed." >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required but not installed." >&2
  exit 1
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required but not installed." >&2
  exit 1
fi

FOLDER_URL="${1:-}"
OUT_DIR="${2:-downloads/panopto_mp4}"
MANIFEST_DIR="${3:-downloads/panopto_manifests}"

if [[ -z "$FOLDER_URL" ]]; then
  usage
  exit 1
fi

SESSION_FILE="${SESSION_FILE:-$HOME/.agent-browser-session}"
DEFAULT_SESSION="visual"
if [[ ! -f "$SESSION_FILE" ]]; then
  printf '%s\n' "$DEFAULT_SESSION" > "$SESSION_FILE"
fi
SESSION="$(tr -d '[:space:]' < "$SESSION_FILE")"
if [[ -z "$SESSION" ]]; then
  SESSION="$DEFAULT_SESSION"
fi

mkdir -p "$OUT_DIR" "$MANIFEST_DIR"

LECTURES_RAW="$MANIFEST_DIR/lectures_raw.json"
LECTURES_JSON="$MANIFEST_DIR/lectures.json"
MANIFEST_TSV="$MANIFEST_DIR/lecture_mp4_manifest.tsv"
EXTRACT_FAILS="$MANIFEST_DIR/extract_failed.txt"
DOWNLOAD_FAILS="$MANIFEST_DIR/download_failed.txt"

open_page() {
  local url="$1"

  if agent-browser --headed --session "$SESSION" open "$url" >/dev/null 2>&1; then
    return 0
  fi

  # Required fallback when open fails.
  agent-browser --session "$SESSION" close >/dev/null 2>&1 || true
  agent-browser --headed --session "$SESSION" open "$url" >/dev/null
}

extract_mp4_url() {
  local raw="" parsed=""

  agent-browser --session "$SESSION" eval '(()=>{const sels=["button[aria-label=\"Play\"]","button[title=\"Play\"]","button.vjs-play-control","button[aria-label*=\"Play\"]"];for(const s of sels){const b=document.querySelector(s);if(b){b.click();return "clicked";}}return "no-play-button";})()' >/dev/null 2>&1 || true
  agent-browser --session "$SESSION" wait 4500 >/dev/null || true

  raw="$(agent-browser --session "$SESSION" eval --stdin <<'EVALEOF'
(() => {
  const names = performance.getEntriesByType('resource').map(e => e.name);
  const mp4 = [...new Set(names.filter(u => /\/fragmented\.mp4(\?|$)/i.test(u)))];
  if (mp4.length) return mp4[0];

  const m3u8 = [...new Set(names.filter(u => /\/index\.m3u8(\?|$)/i.test(u)))];
  if (m3u8.length) return m3u8[0].replace(/\/index\.m3u8(\?.*)?$/i, '/fragmented.mp4');

  return "";
})()
EVALEOF
)" || true

  parsed="$(printf '%s' "$raw" | jq -r . 2>/dev/null || true)"
  if [[ "$parsed" == "null" ]]; then
    parsed=""
  fi

  printf '%s' "$parsed"
}

echo "Using session: $SESSION"
echo "Folder URL: $FOLDER_URL"

open_page "$FOLDER_URL"
agent-browser --session "$SESSION" wait 4000 >/dev/null || true

agent-browser --session "$SESSION" eval --stdin <<'EVALEOF' > "$LECTURES_RAW"
(() => {
  const rows = [...document.querySelectorAll('a.detail-title[href*="Viewer.aspx?id="]')]
    .map(a => ({
      title: (a.textContent || '').trim().replace(/\s+/g, ' '),
      viewer: a.href,
      id: (a.href.match(/[?&]id=([0-9a-f-]+)/i) || [])[1] || null
    }))
    .filter(x => /^Lecture\s+\d+/i.test(x.title));

  const uniq = [];
  const seen = new Set();
  for (const row of rows) {
    if (!row.id || seen.has(row.id)) continue;
    seen.add(row.id);
    uniq.push(row);
  }

  uniq.sort((a, b) => {
    const na = parseInt((a.title.match(/^Lecture\s+(\d+)/i) || [])[1] || '0', 10);
    const nb = parseInt((b.title.match(/^Lecture\s+(\d+)/i) || [])[1] || '0', 10);
    return na - nb;
  });

  return JSON.stringify(uniq, null, 2);
})()
EVALEOF

jq -r . "$LECTURES_RAW" > "$LECTURES_JSON"
TOTAL="$(jq 'length' "$LECTURES_JSON")"

if [[ "$TOTAL" -eq 0 ]]; then
  echo "No lecture rows found." >&2
  exit 2
fi

printf 'index\ttitle\tid\tviewer\tmp4\tfile\n' > "$MANIFEST_TSV"
: > "$EXTRACT_FAILS"
: > "$DOWNLOAD_FAILS"

for ((i=0; i<TOTAL; i++)); do
  title="$(jq -r ".[$i].title" "$LECTURES_JSON")"
  viewer="$(jq -r ".[$i].viewer" "$LECTURES_JSON")"
  id="$(jq -r ".[$i].id" "$LECTURES_JSON")"

  printf '[%d/%d] Extracting: %s\n' "$((i+1))" "$TOTAL" "$title"

  open_page "$viewer"
  agent-browser --session "$SESSION" wait 3500 >/dev/null || true

  mp4_url="$(extract_mp4_url)"
  if [[ -z "$mp4_url" ]]; then
    agent-browser --session "$SESSION" wait 3000 >/dev/null || true
    mp4_url="$(extract_mp4_url)"
  fi

  safe_title="$(printf '%s' "$title" | sed 's#[/:*?"<>|]#_#g; s/[[:space:]]\+/ /g')"
  out_file="$OUT_DIR/${safe_title}.mp4"

  if [[ -z "$mp4_url" ]]; then
    printf '%s\t%s\t%s\n' "$id" "$title" "$viewer" >> "$EXTRACT_FAILS"
    printf '[%d/%d] FAIL extract: %s\n' "$((i+1))" "$TOTAL" "$title"
    continue
  fi

  printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$((i+1))" "$title" "$id" "$viewer" "$mp4_url" "$out_file" >> "$MANIFEST_TSV"
done

FOUND="$(($(wc -l < "$MANIFEST_TSV") - 1))"
echo "Extraction complete: $FOUND/$TOTAL URLs found"

if [[ "$FOUND" -eq 0 ]]; then
  echo "No mp4 URLs extracted." >&2
  exit 3
fi

ok=0
fail=0
while IFS=$'\t' read -r idx title id viewer mp4_url out_file; do
  if [[ "$idx" == "index" ]]; then
    continue
  fi

  if [[ -s "$out_file" ]]; then
    printf '[%s/%s] SKIP existing: %s\n' "$idx" "$FOUND" "$out_file"
    ok=$((ok + 1))
    continue
  fi

  mkdir -p "$(dirname "$out_file")"
  printf '[%s/%s] Downloading: %s\n' "$idx" "$FOUND" "$title"

  if curl -L --retry 4 --retry-delay 2 --connect-timeout 20 --max-time 0 -o "$out_file" "$mp4_url"; then
    ok=$((ok + 1))
  else
    rm -f "$out_file"
    printf '%s\t%s\t%s\n' "$title" "$mp4_url" "$out_file" >> "$DOWNLOAD_FAILS"
    fail=$((fail + 1))
  fi
done < "$MANIFEST_TSV"

echo "Done. Success=$ok Failed=$fail"
echo "Output: $OUT_DIR"
echo "Manifest: $MANIFEST_TSV"
echo "Extract fails: $EXTRACT_FAILS"
echo "Download fails: $DOWNLOAD_FAILS"

if [[ "$fail" -gt 0 ]]; then
  exit 4
fi
