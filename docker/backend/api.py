"""
仪表位置图查询系统 — 后端 API
环境变量:
  DATA_DIR   图片数据目录 (默认 /data)
  PORT       监听端口     (默认 8000)
"""

import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# ── Config ───────────────────────────────────────────────
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
PORT = int(os.environ.get("PORT", 8000))

app = Flask(__name__)
CORS(app)   # allow the Nginx frontend to call the API

# ── Data model ───────────────────────────────────────────

@dataclass(frozen=True)
class ImageRecord:
    tag: str
    drawing_label: str
    drawing_dir: str
    page: int | None
    seq: int | None
    filename: str


_PAGE_RE = re.compile(r'_page(\d+)_(\d+)_(.+)\.png$', re.IGNORECASE)


def _drawing_label(dir_name: str) -> str:
    first = dir_name.split('_')[0]
    m = re.match(r'^(\D+)', first)
    return m.group(1) if m else first


def _parse_file(dir_name: str, filename: str) -> ImageRecord | None:
    m = _PAGE_RE.search(filename)
    if m:
        page, seq, tag = int(m.group(1)), int(m.group(2)), m.group(3)
    else:
        parts = filename[:-4].split('_')
        tag, page, seq = parts[-1], None, None
    return ImageRecord(
        tag=tag,
        drawing_label=_drawing_label(dir_name),
        drawing_dir=dir_name,
        page=page,
        seq=seq,
        filename=filename,
    )


# ── Index ────────────────────────────────────────────────

INDEX: list[ImageRecord] = []
DRAWING_LABELS: list[str] = []


def _build_index() -> None:
    global INDEX, DRAWING_LABELS
    records: list[ImageRecord] = []
    if not DATA_DIR.is_dir():
        print(f"[WARN] DATA_DIR {DATA_DIR} does not exist")
        INDEX, DRAWING_LABELS = [], []
        return
    for d in sorted(DATA_DIR.iterdir()):
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.suffix.lower() != '.png':
                continue
            rec = _parse_file(d.name, f.name)
            if rec:
                records.append(rec)
    INDEX = records
    DRAWING_LABELS = sorted({r.drawing_label for r in records})
    print(f"[INDEX] {len(INDEX)} images | {len(DRAWING_LABELS)} drawings | data={DATA_DIR}")


def _sort_key(r: ImageRecord) -> tuple:
    return (
        r.drawing_label,
        r.page if r.page is not None else 9999,
        r.seq  if r.seq  is not None else 9999,
        r.tag,
    )


# ── API routes ───────────────────────────────────────────

@app.get("/api/stats")
def stats():
    counts = Counter(r.drawing_label for r in INDEX)
    return jsonify({
        "total":    len(INDEX),
        "drawings": dict(sorted(counts.items())),
    })


@app.get("/api/drawings")
def drawings():
    return jsonify(DRAWING_LABELS)


@app.get("/api/search")
def search():
    q       = request.args.get("q", "").strip().upper()
    drawing = request.args.get("drawing", "").strip()
    if not q:
        return jsonify({"results": [], "count": 0, "truncated": False})

    pool = [r for r in INDEX if r.drawing_label == drawing] if drawing else INDEX
    matched = sorted([r for r in pool if q in r.tag.upper()], key=_sort_key)

    LIMIT = 200
    return jsonify({
        "results":   _to_json(matched[:LIMIT]),
        "count":     len(matched),
        "truncated": len(matched) > LIMIT,
    })


@app.get("/api/search_all")
def search_all():
    drawing = request.args.get("drawing", "").strip()
    pool = sorted(
        [r for r in INDEX if r.drawing_label == drawing] if drawing else INDEX,
        key=_sort_key,
    )
    LIMIT = 200
    return jsonify({
        "results":   _to_json(pool[:LIMIT]),
        "count":     len(pool),
        "truncated": len(pool) > LIMIT,
    })


@app.post("/api/rebuild")
def rebuild():
    _build_index()
    return jsonify({"status": "ok", "count": len(INDEX)})


@app.get("/images/<path:filepath>")
def serve_image(filepath: str):
    return send_from_directory(DATA_DIR, filepath, max_age=86400)


@app.get("/api/download/excel")
def download_excel():
    """汇总表 Excel 下载（如存在于 DATA_DIR 上一级）"""
    xlsx = DATA_DIR.parent / "仪表位置图汇总表.xlsx"
    if not xlsx.exists():
        xlsx = DATA_DIR / "仪表位置图汇总表.xlsx"
    if not xlsx.exists():
        return jsonify({"error": "file not found"}), 404
    return send_from_directory(xlsx.parent, xlsx.name, as_attachment=True)


def _to_json(records: list[ImageRecord]) -> list[dict]:
    return [
        {
            "tag":           r.tag,
            "drawing_label": r.drawing_label,
            "drawing_dir":   r.drawing_dir,
            "page":          r.page,
            "seq":           r.seq,
            "image_url":     f"/images/{r.drawing_dir}/{r.filename}",
        }
        for r in records
    ]


if __name__ == "__main__":
    _build_index()
    app.run(host="0.0.0.0", port=PORT, debug=False)
