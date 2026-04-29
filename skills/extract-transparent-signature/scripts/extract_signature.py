#!/usr/bin/env python3
"""
Extract dark ink from a photographed signature into a transparent PNG.

Requires ffmpeg on PATH. No Python image libraries are needed.
"""

from __future__ import annotations

import argparse
import os
import struct
import subprocess
import sys
import zlib
from collections import deque
from pathlib import Path


def read_ppm(path: str) -> tuple[int, int, bytes]:
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        path,
        "-frames:v",
        "1",
        "-f",
        "image2pipe",
        "-vcodec",
        "ppm",
        "-",
    ]
    data = subprocess.check_output(cmd)

    pos = 0

    def token() -> bytes:
        nonlocal pos
        while pos < len(data) and data[pos] in b" \t\r\n":
            pos += 1
        if pos < len(data) and data[pos] == ord("#"):
            while pos < len(data) and data[pos] not in b"\r\n":
                pos += 1
            return token()
        start = pos
        while pos < len(data) and data[pos] not in b" \t\r\n":
            pos += 1
        return data[start:pos]

    magic = token()
    if magic != b"P6":
        raise ValueError("ffmpeg did not produce a binary PPM image")

    width = int(token())
    height = int(token())
    maxval = int(token())
    if maxval != 255:
        raise ValueError(f"unsupported PPM max value: {maxval}")

    while pos < len(data) and data[pos] in b" \t\r\n":
        pos += 1

    pixels = data[pos:]
    expected = width * height * 3
    if len(pixels) < expected:
        raise ValueError("truncated image data from ffmpeg")

    return width, height, pixels[:expected]


def percentile(hist: list[int], pct: float, total: int) -> int:
    target = max(1, int(total * pct))
    seen = 0
    for i, count in enumerate(hist):
        seen += count
        if seen >= target:
            return i
    return 255


def otsu_threshold(hist: list[int], total: int) -> int:
    weighted_total = sum(i * count for i, count in enumerate(hist))
    background_count = 0
    background_sum = 0
    best_threshold = 100
    best_score = -1.0

    for threshold, count in enumerate(hist):
        background_count += count
        if background_count == 0:
            continue

        foreground_count = total - background_count
        if foreground_count == 0:
            break

        background_sum += threshold * count
        foreground_sum = weighted_total - background_sum

        background_mean = background_sum / background_count
        foreground_mean = foreground_sum / foreground_count
        score = background_count * foreground_count * (background_mean - foreground_mean) ** 2
        if score > best_score:
            best_score = score
            best_threshold = threshold

    return best_threshold


def build_luma(pixels: bytes) -> tuple[bytearray, list[int]]:
    luma = bytearray(len(pixels) // 3)
    hist = [0] * 256
    out = 0
    for i in range(0, len(pixels), 3):
        r, g, b = pixels[i], pixels[i + 1], pixels[i + 2]
        y = (77 * r + 150 * g + 29 * b) >> 8
        luma[out] = y
        hist[y] += 1
        out += 1
    return luma, hist


def connected_ink_mask(
    luma: bytearray,
    width: int,
    height: int,
    threshold: int,
    min_area: int,
    drop_border: bool,
) -> bytearray:
    mask = bytearray(1 if y < threshold else 0 for y in luma)
    keep = bytearray(len(mask))
    q: deque[int] = deque()

    for start, value in enumerate(mask):
        if not value:
            continue

        mask[start] = 0
        q.append(start)
        component: list[int] = []
        min_x = max_x = start % width
        min_y = max_y = start // width

        while q:
            idx = q.popleft()
            component.append(idx)
            x = idx % width
            y = idx // width
            if x < min_x:
                min_x = x
            if x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            if y > max_y:
                max_y = y

            for n in (idx - width, idx + width):
                if 0 <= n < len(mask) and mask[n]:
                    mask[n] = 0
                    q.append(n)

            if x > 0:
                n = idx - 1
                if mask[n]:
                    mask[n] = 0
                    q.append(n)
            if x + 1 < width:
                n = idx + 1
                if mask[n]:
                    mask[n] = 0
                    q.append(n)

        touches_border = min_x == 0 or min_y == 0 or max_x == width - 1 or max_y == height - 1
        if len(component) >= min_area and not (drop_border and touches_border):
            for idx in component:
                keep[idx] = 1

    return keep


def ink_bounds(mask: bytearray, width: int, height: int) -> tuple[int, int, int, int] | None:
    left, top = width, height
    right, bottom = -1, -1
    for idx, value in enumerate(mask):
        if not value:
            continue
        y, x = divmod(idx, width)
        if x < left:
            left = x
        if x > right:
            right = x
        if y < top:
            top = y
        if y > bottom:
            bottom = y

    if right < left or bottom < top:
        return None
    return left, top, right, bottom


def expand_bounds(
    bounds: tuple[int, int, int, int],
    width: int,
    height: int,
    margin: int,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = bounds
    return (
        max(0, left - margin),
        max(0, top - margin),
        min(width - 1, right + margin),
        min(height - 1, bottom + margin),
    )


def row_groups(mask: bytearray, width: int, height: int, max_gap: int) -> list[tuple[int, int]]:
    rows = [0] * height
    for idx, value in enumerate(mask):
        if value:
            rows[idx // width] += 1

    groups: list[tuple[int, int]] = []
    start: int | None = None
    last = -1

    for y, count in enumerate(rows):
        if count == 0:
            continue
        if start is None:
            start = y
        elif y - last > max_gap:
            groups.append((start, last))
            start = y
        last = y

    if start is not None:
        groups.append((start, last))

    return groups


def write_png(path: Path, width: int, height: int, rgba: bytes) -> None:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    rows = bytearray()
    stride = width * 4
    for y in range(height):
        rows.append(0)
        start = y * stride
        rows.extend(rgba[start : start + stride])

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(rows), level=9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def parse_hex_color(value: str) -> tuple[int, int, int]:
    color = value.strip().lstrip("#")
    if len(color) != 6:
        raise argparse.ArgumentTypeError("ink color must look like #000000")
    try:
        return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ink color must look like #000000") from exc


def render_crop(
    pixels: bytes,
    luma: bytearray,
    mask: bytearray,
    source_width: int,
    bounds: tuple[int, int, int, int],
    threshold: int,
    softness: int,
    ink: tuple[int, int, int] | None,
    solid: bool,
) -> tuple[int, int, bytes]:
    left, top, right, bottom = bounds
    out_width = right - left + 1
    out_height = bottom - top + 1
    rgba = bytearray(out_width * out_height * 4)
    out = 0

    solid_at = max(0, threshold - softness)
    ramp = max(1, threshold - solid_at)

    for y in range(top, bottom + 1):
        row = y * source_width
        for x in range(left, right + 1):
            idx = row + x
            if mask[idx]:
                if solid:
                    alpha = 255
                else:
                    alpha = 255 if luma[idx] <= solid_at else (threshold - luma[idx]) * 255 // ramp
                    alpha = max(0, min(255, alpha))
                if ink is None:
                    p = idx * 3
                    rgba[out : out + 4] = bytes((pixels[p], pixels[p + 1], pixels[p + 2], alpha))
                else:
                    rgba[out : out + 4] = bytes((ink[0], ink[1], ink[2], alpha))
            else:
                rgba[out : out + 4] = b"\x00\x00\x00\x00"
            out += 4

    return out_width, out_height, bytes(rgba)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="source image, including HEIC/JPG/PNG")
    parser.add_argument("output", help="transparent PNG output path")
    parser.add_argument("--threshold", type=int, help="darkness cutoff; lower removes more background")
    parser.add_argument("--softness", type=int, default=55, help="edge softness in luma levels")
    parser.add_argument("--min-area", type=int, help="drop tiny dark specks below this area")
    parser.add_argument("--margin", type=int, default=28, help="transparent padding around detected ink")
    parser.add_argument("--ink", type=parse_hex_color, default=parse_hex_color("#050505"))
    parser.add_argument("--solid", action="store_true", help="make detected ink fully opaque")
    parser.add_argument("--keep-border", action="store_true", help="keep dark components touching source image edges")
    parser.add_argument("--preserve-color", action="store_true", help="keep original ink color instead of black")
    parser.add_argument("--split", action="store_true", help="also write one cropped PNG per separated signature row group")
    parser.add_argument("--split-gap", type=int, default=260, help="vertical gap used by --split")
    args = parser.parse_args()

    width, height, pixels = read_ppm(args.input)
    luma, hist = build_luma(pixels)
    total = width * height

    if args.threshold is None:
        otsu = otsu_threshold(hist, total)
        dark_tail = percentile(hist, 0.04, total)
        threshold = max(72, min(132, max(otsu, dark_tail + 26)))
    else:
        threshold = args.threshold

    min_area = args.min_area if args.min_area is not None else max(35, total // 24000)
    mask = connected_ink_mask(luma, width, height, threshold, min_area, not args.keep_border)
    bounds = ink_bounds(mask, width, height)
    if bounds is None:
        raise SystemExit("no signature ink detected; try a higher --threshold")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    bounds = expand_bounds(bounds, width, height, args.margin)
    ink = None if args.preserve_color else args.ink
    out_width, out_height, rgba = render_crop(
        pixels,
        luma,
        mask,
        width,
        bounds,
        threshold,
        args.softness,
        ink,
        args.solid,
    )
    write_png(output, out_width, out_height, rgba)

    print(f"wrote {output} ({out_width}x{out_height}, threshold={threshold})")

    if args.split:
        stem = output.with_suffix("")
        suffix = output.suffix or ".png"
        groups = row_groups(mask, width, height, args.split_gap)
        for i, (top, bottom) in enumerate(groups, start=1):
            group_mask = bytearray(len(mask))
            for y in range(top, bottom + 1):
                start = y * width
                end = start + width
                group_mask[start:end] = mask[start:end]

            group_bounds = ink_bounds(group_mask, width, height)
            if group_bounds is None:
                continue
            group_bounds = expand_bounds(group_bounds, width, height, args.margin)
            group_width, group_height, group_rgba = render_crop(
                pixels,
                luma,
                group_mask,
                width,
                group_bounds,
                threshold,
                args.softness,
                ink,
                args.solid,
            )
            group_output = Path(f"{stem}-{i}{suffix}")
            write_png(group_output, group_width, group_height, group_rgba)
            print(f"wrote {group_output} ({group_width}x{group_height})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
