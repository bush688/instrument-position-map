"""
仪表位置图查询系统
用法: python web_query.py
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from flask import Flask, jsonify, render_template, request, send_from_directory

OUTPUT_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent / "output"))

# ──────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────

@dataclass(frozen=True)
class ImageRecord:
    tag: str            # 位号, e.g. "04FT-03001"
    drawing_label: str  # 中文标签, e.g. "气化"
    drawing_dir: str    # 目录名, e.g. "气化_21216-030000-IN40"
    page: int | None    # 页码 (None for 甲醇罐区 pattern)
    seq: int | None     # 序号
    filename: str       # PNG 文件名


# ──────────────────────────────────────────────
# Filename parsing
# ──────────────────────────────────────────────

# Pattern A: {drawing}_page{N}_{seq}_{tag}.png
_PAGE_RE = re.compile(r'_page(\d+)_(\d+)_(.+)\.png$', re.IGNORECASE)

def _drawing_label(dir_name: str) -> str:
    """从目录名提取中文标签: '气化_21216-...' → '气化'"""
    # 取第一个下划线前的部分；若无下划线则取汉字前缀
    first = dir_name.split('_')[0]
    # 去掉尾部数字（应对 "甲醇罐区21216-..." 无下划线情况）
    m = re.match(r'^(\D+)', first)
    return m.group(1) if m else first


def _parse_file(dir_name: str, filename: str) -> ImageRecord | None:
    stem = filename[:-4]  # remove .png
    m = _PAGE_RE.search(filename)
    if m:
        page = int(m.group(1))
        seq  = int(m.group(2))
        tag  = m.group(3)
    else:
        # Pattern B: {drawing}_{tag}.png — tag is last _-segment
        parts = stem.split('_')
        tag  = parts[-1]
        page = None
        seq  = None
    return ImageRecord(
        tag=tag,
        drawing_label=_drawing_label(dir_name),
        drawing_dir=dir_name,
        page=page,
        seq=seq,
        filename=filename,
    )


# ──────────────────────────────────────────────
# Index
# ──────────────────────────────────────────────

def build_index(output_dir: Path) -> tuple[list[ImageRecord], list[str]]:
    records: list[ImageRecord] = []
    for d in sorted(output_dir.iterdir()):
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.suffix.lower() != '.png':
                continue
            rec = _parse_file(d.name, f.name)
            if rec:
                records.append(rec)
    labels = sorted({r.drawing_label for r in records})
    return records, labels


INDEX: list[ImageRecord] = []
DRAWING_LABELS: list[str] = []

def _load_index():
    global INDEX, DRAWING_LABELS
    INDEX, DRAWING_LABELS = build_index(OUTPUT_DIR)
    print(f"索引加载完成: {len(INDEX)} 张图片, {len(DRAWING_LABELS)} 个图纸")


# ──────────────────────────────────────────────
# Flask app
# ──────────────────────────────────────────────

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", drawings=DRAWING_LABELS)


@app.route("/api/search")
def search():
    q       = request.args.get("q", "").strip().upper()
    drawing = request.args.get("drawing", "").strip()
    if not q:
        return jsonify({"results": [], "count": 0, "truncated": False})

    pool = INDEX
    if drawing:
        pool = [r for r in pool if r.drawing_label == drawing]

    matched = [r for r in pool if q in r.tag.upper()]

    # Sort: drawing label, page (None → last), seq (None → last), tag
    matched.sort(key=lambda r: (
        r.drawing_label,
        r.page  if r.page  is not None else 9999,
        r.seq   if r.seq   is not None else 9999,
        r.tag,
    ))

    LIMIT = 200
    truncated = len(matched) > LIMIT
    results = [
        {
            "tag":          r.tag,
            "drawing_label": r.drawing_label,
            "drawing_dir":  r.drawing_dir,
            "page":         r.page,
            "seq":          r.seq,
            "image_url":    f"/images/{r.drawing_dir}/{r.filename}",
        }
        for r in matched[:LIMIT]
    ]
    return jsonify({"results": results, "count": len(matched), "truncated": truncated})


@app.route("/api/search_all")
def search_all():
    """Return all images for a drawing (used by stat-card click)."""
    drawing = request.args.get("drawing", "").strip()
    pool = [r for r in INDEX if r.drawing_label == drawing] if drawing else INDEX
    pool = sorted(pool, key=lambda r: (
        r.drawing_label,
        r.page if r.page is not None else 9999,
        r.seq  if r.seq  is not None else 9999,
        r.tag,
    ))
    LIMIT = 200
    truncated = len(pool) > LIMIT
    results = [
        {
            "tag":           r.tag,
            "drawing_label": r.drawing_label,
            "drawing_dir":   r.drawing_dir,
            "page":          r.page,
            "seq":           r.seq,
            "image_url":     f"/images/{r.drawing_dir}/{r.filename}",
        }
        for r in pool[:LIMIT]
    ]
    return jsonify({"results": results, "count": len(pool), "truncated": truncated})


@app.route("/api/stats")
def stats():
    from collections import Counter
    counts = Counter(r.drawing_label for r in INDEX)
    return jsonify({
        "total": len(INDEX),
        "drawings": dict(sorted(counts.items())),
    })


@app.route("/api/rebuild", methods=["POST"])
def rebuild():
    _load_index()
    return jsonify({"status": "ok", "count": len(INDEX)})


@app.route("/images/<path:filepath>")
def serve_image(filepath):
    # Security: Flask's send_from_directory prevents path traversal
    return send_from_directory(OUTPUT_DIR, filepath,
                               max_age=86400)


if __name__ == "__main__":
    _load_index()
    print("启动查询系统: http://127.0.0.1:5000")
    app.run(debug=False, host="127.0.0.1", port=5000)
