# URL Patterns

## Panopto viewer page

- `https://<tenant>/Panopto/Pages/Viewer.aspx?id=<delivery-id>`

## Common media URLs discovered at runtime

- Master playlist:
  - `https://...cloudfront.net/sessions/<session-id>/<delivery-id>-<stream-guid>.hls/master.m3u8?...`
- Rendition playlist:
  - `https://...cloudfront.net/sessions/<session-id>/<delivery-id>-<stream-guid>.hls/<bitrate>/index.m3u8`
- Direct MP4 segment file (preferred for direct download):
  - `https://...cloudfront.net/sessions/<session-id>/<delivery-id>-<stream-guid>.hls/<bitrate>/fragmented.mp4`

## Runtime extraction snippet (in browser context)

```js
const names = performance.getEntriesByType('resource').map(e => e.name);
const mp4 = [...new Set(names.filter(u => /\/fragmented\.mp4(\?|$)/i.test(u)))];
const m3u8 = [...new Set(names.filter(u => /\/index\.m3u8(\?|$)/i.test(u)))];
```

If no direct mp4 is found but `index.m3u8` exists, derive:

- `.../index.m3u8` -> `.../fragmented.mp4`
