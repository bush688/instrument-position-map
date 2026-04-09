"""
综合处理脚本 v2 - 修复所有仪表位置图标注
处理规则：
1. 位置图和表格成对出现
2. 如果某页只有对照表（无位置图），该表与上一页位置图配对
3. 多列表格按行从左到右平铺为有序列表
4. 序号在表格中找不到时，继承最近合法序号的位号
5. 输出命名: {图纸名称}_page{页号}_{序号}_{位号}.png

修复内容 v2：
- dy 阈值改为 10pt（避免子条目误匹配）
- 位置图区域通过"表格序号坐标"邻近性过滤（不依赖固定 x 边界）
- 多列表格按 Y 分桶后按 X 排序展开
"""
import os
import re
import glob
import pdfplumber
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont

OCR_DIR  = r"E:\opencode\位置图处理\仪表位置图OCR"
OUT_ROOT = r"E:\opencode\位置图处理\output"
SCALE    = 3.0

try:
    FONT = ImageFont.truetype("simsun.ttc", 26)
except Exception:
    FONT = ImageFont.load_default()

# 仪表位号正则（匹配如 04XZV-01003 / 40FT-03001 / XMV-040802C / PT-040854 等）
# 可选的两位数字前缀 + 2-6位大写字母 + 连字符 + 以数字开头的编号
TAG_RE = re.compile(r'^(?:[0-9]{2})?[A-Z]{2,6}-[0-9][0-9A-Z]*$')

# ─────────────────────────────────────────────
# 表格提取（基于坐标，支持多列，dy ≤ 10pt）
# ─────────────────────────────────────────────

def extract_table_coords(page):
    """
    从 OCR PDF 页面提取 (seq_int, tag_str, seq_x, seq_y) 列表。
    dy ≤ 10pt：只匹配同行的序号-位号，过滤子条目。
    多列按 Y 分桶后按 X 排序，实现"逐行从左到右"展开。
    """
    words = page.extract_words()

    tag_words = [(w['x0'], w['top'], w['text'])
                 for w in words if TAG_RE.match(w['text'])]
    if not tag_words:
        return []

    seq_words = []
    for w in words:
        t = w['text'].strip()
        if re.match(r'^\d{1,3}$', t):
            n = int(t)
            if 1 <= n <= 300:
                seq_words.append((w['x0'], w['top'], n))

    # 为每个 tag 找同行（dy≤10）最近的序号（在其左侧，dx<600）
    raw_pairs = []
    unmatched_tags = []  # 有 tag 但找不到同行 seq 的条目
    for tx, ty, tag in tag_words:
        best = None
        best_score = float('inf')
        for sx, sy, seq in seq_words:
            dy = abs(sy - ty)
            dx = tx - sx
            if dy > 10 or dx < 5 or dx > 600:
                continue
            score = dx + 4 * dy
            if score < best_score:
                best_score = score
                best = (sx, sy, seq)
        if best is not None:
            raw_pairs.append((best[0], best[1], best[2], tx, ty, tag))
        else:
            unmatched_tags.append((tx, ty, tag))

    if not raw_pairs:
        return []

    # 去重：同一 seq 保留最小 dx 的匹配（最近的序号）
    seen = {}
    for p in raw_pairs:
        seq = p[2]
        dx = p[3] - p[0]
        if seq not in seen or dx < (seen[seq][3] - seen[seq][0]):
            seen[seq] = p

    # ── 间隙填补：补充 seq 序号缺失的条目 ────────────────────────
    # 某些页面中部分行的序号是矢量图形，pdfplumber 无法提取文本。
    # 策略：找到两个相邻 seq 之间的孤立 tag，按 y 坐标顺序分配缺失的序号。
    gap_filled: set[int] = set()
    if unmatched_tags:
        # 已配对的 seq 按 y 排序
        known = sorted(seen.values(), key=lambda p: p[1])   # sorted by sy
        # 用来获取第一列 x 坐标的近似值（seq 列的 x）
        seq_col_x = known[0][0] if known else 0

        for tx, ty, tag in sorted(unmatched_tags, key=lambda t: t[1]):
            # 找紧邻的 prev_seq（y < ty）和 next_seq（y > ty）
            before = [(p[2], p[1]) for p in known if p[1] < ty]
            after  = [(p[2], p[1]) for p in known if p[1] > ty]
            if not before or not after:
                continue
            prev_seq = max(before, key=lambda x: x[1])[0]
            next_seq = min(after,  key=lambda x: x[1])[0]
            gap = next_seq - prev_seq  # e.g. 25 - 23 = 2

            # 统计同一区间内还有多少 unmatched tag
            peers = [(ux, uy, ut) for ux, uy, ut in unmatched_tags
                     if uy > min(p[1] for p in known if p[2] == prev_seq)
                     and uy < min(p[1] for p in known if p[2] == next_seq)]
            peers_sorted = sorted(peers, key=lambda t: t[1])
            if gap - 1 > 5:
                # 间隙过大（>5 个缺失序号），大概率是子条目而非缺号，跳过
                continue
            if len(peers_sorted) != gap - 1:
                # 孤立 tag 数量与 seq 空缺数量不一致，跳过（避免误配）
                continue

            idx = peers_sorted.index((tx, ty, tag))
            inferred_seq = prev_seq + 1 + idx
            if inferred_seq not in seen:
                # 用 seq_col_x 作为假序号列坐标，ty 作为行 y
                seen[inferred_seq] = (seq_col_x, ty, inferred_seq, tx, ty, tag)
                gap_filled.add(inferred_seq)

    # ── 子条目关联：将剩余未匹配的 tag 关联到最近的上级 seq ────────────
    # 阀门附件（XZSO/XZSC/XVY/XZVY/PVY/PZVY 等）在表格中没有独立序号，
    # 它们与上一行的主仪表共享同一位置圆圈。
    # 将这些 tag 关联到最近的前驱 seq，使查询系统能通过附件 tag 找到位置。
    # 限制：若 tag 距父级超过 200pt（大约 9 行），视为图框/说明文字，跳过。
    MAX_SUB_DIST = 200  # pt
    sub_entries: list[tuple] = []  # 额外的 (sx, sy, seq, tx, ty, tag) 条目
    gap_filled_tags = {seen[s][5] for s in gap_filled}
    for tx, ty, tag in unmatched_tags:
        if tag in gap_filled_tags:
            continue  # 已通过间隙填补处理
        # 找 y 坐标小于 ty 的最近已匹配 seq
        before = [(p[2], p[1], p[0]) for p in seen.values() if p[1] < ty]
        if not before:
            continue
        parent_seq, parent_sy, parent_sx = max(before, key=lambda x: x[1])
        if ty - parent_sy > MAX_SUB_DIST:
            # 距父级过远，大概率是图框/修订栏中的说明文字，跳过
            continue
        # 以父级的序号列坐标作为此子条目的位置标识
        sub_entries.append((parent_sx, parent_sy, parent_seq, tx, ty, tag))

    # 按 Y 分桶（桶高 35pt）再按 X 排序，实现"逐行从左到右"展开
    ROW_H = 35
    main_entries = sorted(seen.values(), key=lambda p: (round(p[1] / ROW_H), p[0]))
    all_entries = main_entries + sub_entries  # 子条目追加到末尾（同序号排在主条目后）

    # 返回 (seq_int, tag_str, seq_x, seq_y)
    return [(p[2], p[5], p[0], p[1]) for p in all_entries]


# ─────────────────────────────────────────────
# 位置图序号提取（原始 PDF）
# ─────────────────────────────────────────────

def extract_map_numbers(orig_page, table_entries):
    """
    从原始 PDF 页面提取位置图序号。
    排除规则：
    1. 排除页面顶部/底部 5% 区域（图框）
    2. 排除与表格序号坐标距离很近的数字（x误差<200pt, y误差<25pt）
    """
    h = orig_page.height
    y_lo = 0.05 * h
    y_hi = 0.95 * h

    # 表格序号坐标集
    tbl_seq_pos = [(sx, sy) for (_, _, sx, sy) in table_entries]

    words = orig_page.extract_words()
    nums = []
    for w in words:
        t = w['text'].strip()
        if not re.match(r'^\d{1,2}$', t):
            continue
        n = int(t)
        if n < 1 or n > 150:
            continue
        x, y = w['x0'], w['top']
        if y < y_lo or y > y_hi:
            continue

        # 排除靠近表格序号坐标的数字
        near_table = False
        for tx, ty in tbl_seq_pos:
            if abs(x - tx) < 200 and abs(y - ty) < 25:
                near_table = True
                break
        if near_table:
            continue

        nums.append({'num': str(n), 'x': x, 'y': y})

    # 去重①：坐标误差 5pt 内视为同一点
    unique = []
    for p in nums:
        dup = any(q['num'] == p['num']
                  and abs(q['x'] - p['x']) < 5
                  and abs(q['y'] - p['y']) < 5
                  for q in unique)
        if not dup:
            unique.append(p)

    unique.sort(key=lambda p: (p['y'], p['x']))

    # 去重②：每个序号只保留一个实例（防止同号多处出现导致文件名重复覆盖）
    seen_nums: set = set()
    deduped = []
    for p in unique:
        if p['num'] not in seen_nums:
            seen_nums.add(p['num'])
            deduped.append(p)
    return deduped


# ─────────────────────────────────────────────
# 映射 + 继承逻辑
# ─────────────────────────────────────────────

def build_tag_map(position_numbers, table_entries):
    """
    将位置图序号映射到位号列表（含继承逻辑，支持每个序号多个位号）。
    table_entries: [(seq_int, tag_str, sx, sy), ...]  已按正确顺序排列
    同一 seq 的多条记录（主仪表 + 附件）会合并为一个列表。
    """
    # seq → [tag, ...] （保持插入顺序，主仪表在前，附件在后）
    seq_tags: dict[int, list[str]] = {}
    for seq, tag, sx, sy in table_entries:
        if seq not in seq_tags:
            seq_tags[seq] = []
        if tag not in seq_tags[seq]:
            seq_tags[seq].append(tag)

    tag_map: dict[str, list[str]] = {}
    last_tags: list[str] = []
    for p in position_numbers:
        n = int(p['num'])
        if n in seq_tags:
            last_tags = seq_tags[n]
        tag_map[p['num']] = last_tags
    return tag_map


# ─────────────────────────────────────────────
# 图片生成
# ─────────────────────────────────────────────

def render_images(orig_pdf_path, page_idx, positions, tag_map, drawing_name, out_dir):
    """在原始 PDF 页面上标注序号→位号，每个（序号, 位号）生成一张图片。
    同一序号有多个位号（主仪表 + 附件）时，每个位号各生成一张图片，
    标注内容相同（同一圆圈位置），文件名中的位号不同。
    """
    pdf_doc = pdfium.PdfDocument(orig_pdf_path)
    if page_idx >= len(pdf_doc):
        return 0
    base_img = pdf_doc[page_idx].render(scale=SCALE).to_pil()

    page_prefix = f"{drawing_name}_page{page_idx + 1}_"
    expected_fnames: set[str] = set()
    count = 0

    for p in positions:
        num = p['num']
        tags = tag_map.get(num, [])
        if not tags:
            continue
        img = base_img.copy()
        draw = ImageDraw.Draw(img)
        x = p['x'] * SCALE
        y = p['y'] * SCALE
        r = 32
        # 标注第一个（主）位号；所有子图共用同一标注图
        main_tag = tags[0]
        draw.ellipse([x - r, y - r, x + r, y + r], outline='red', width=3)
        draw.text((x - 6, y - 45), num, fill='red', font=FONT)
        draw.text((x + 36, y - 12), main_tag, fill='red', font=FONT)

        for tag in tags:
            fname = f"{page_prefix}{num}_{tag}.png"
            expected_fnames.add(fname)
            img.save(os.path.join(out_dir, fname), 'PNG')
            count += 1

    # 删除本页中已不再需要的旧文件（同页前缀，但不在本次期望集中）
    for old in os.listdir(out_dir):
        if old.startswith(page_prefix) and old not in expected_fnames:
            os.remove(os.path.join(out_dir, old))

    return count


# ─────────────────────────────────────────────
# 页面结构分析与配对
# ─────────────────────────────────────────────

MIN_MAP_POSITIONS = 5  # 少于此数视为表格页（排除边框误检）

def analyze_pages(orig_pdf_path, ocr_pdf_path):
    """
    分析每一页，返回：
    [{'has_map': bool, 'has_table': bool,
      'table': [(seq,tag,sx,sy),...], 'positions': [...]}]

    逐页打开 PDF（每页独立 open/close）以避免 pdfminer 在大型 PDF
    上缓存全部页面内容导致内存爆炸。
    """
    # 先获取页数
    with pdfplumber.open(orig_pdf_path) as f:
        n_orig = len(f.pages)
    with pdfplumber.open(ocr_pdf_path) as f:
        n_ocr = len(f.pages)
    n_pages = max(n_orig, n_ocr)

    pages = []
    for pi in range(n_pages):
        info = {'has_map': False, 'has_table': False, 'table': [], 'positions': []}

        # ── 表格（来自 OCR PDF）— 每页独立 open 避免内存累积
        if pi < n_ocr:
            with pdfplumber.open(ocr_pdf_path) as ocr_pdf:
                table = extract_table_coords(ocr_pdf.pages[pi])
        else:
            table = []

        if table:
            info['has_table'] = True
            info['table'] = table

        # ── 位置图序号（来自原始 PDF）
        if pi < n_orig:
            with pdfplumber.open(orig_pdf_path) as orig_pdf:
                pos = extract_map_numbers(orig_pdf.pages[pi], table)
                # 少于阈值时忽略（边框/标题栏误检），该页视为纯表格页
                if len(pos) >= MIN_MAP_POSITIONS:
                    info['has_map'] = True
                    info['positions'] = pos

        pages.append(info)
        print(f"    analyzed page {pi+1}/{n_pages}", flush=True)

    return pages


def pair_pages(pages):
    """
    将位置图页与表格页配对。
    规则：
    - 当前页同时有位置图和表格 → 直接配对
      - 若有等待中的位置图页（pending），先用当前表格配对 pending 位置图，
        再将当前位置图作为新的 pending（或形成自己的对）
    - 当前页只有位置图 → 存为 pending，等待后续表格页
    - 当前页只有表格 → 追加到 pending 位置图的表格
    返回：[(pos_page_idx, combined_table_entries), ...]
    """
    pairs = []
    pending_map_idx = None
    pending_table = []

    for i, p in enumerate(pages):
        if p['has_map'] and p['has_table']:
            if pending_map_idx is not None:
                # 有等待中的位置图：用当前页表格为其收尾，然后当前页自成一对
                combined = pending_table + p['table']
                if combined:
                    pairs.append((pending_map_idx, combined))
                pending_map_idx = None
                pending_table = []
            # 当前页自成一对
            pairs.append((i, p['table']))

        elif p['has_map'] and not p['has_table']:
            # 保存上一个等待中的位置图（若已有表格）
            if pending_map_idx is not None and pending_table:
                pairs.append((pending_map_idx, pending_table))
            pending_map_idx = i
            pending_table = []

        elif not p['has_map'] and p['has_table']:
            # 纯表格页 → 追加到 pending
            if pending_map_idx is not None:
                pending_table.extend(p['table'])

    # 收尾：还有等待中的位置图
    if pending_map_idx is not None and pending_table:
        pairs.append((pending_map_idx, pending_table))

    return pairs


# ─────────────────────────────────────────────
# 主处理函数
# ─────────────────────────────────────────────

def process_drawing(drawing_name, orig_pdf, ocr_pdf):
    out_dir = os.path.join(OUT_ROOT, drawing_name)
    os.makedirs(out_dir, exist_ok=True)
    print(f"\n{'='*60}")
    print(f"  {drawing_name}")

    pages = analyze_pages(orig_pdf, ocr_pdf)

    map_cnt = sum(1 for p in pages if p['has_map'])
    tbl_cnt = sum(1 for p in pages if p['has_table'])
    print(f"  pages: {len(pages)} total | {map_cnt} with map | {tbl_cnt} with table")

    pairs = pair_pages(pages)
    print(f"  pairs: {len(pairs)}")

    total = 0
    for pos_idx, table_entries in pairs:
        positions = pages[pos_idx]['positions']
        if not positions or not table_entries:
            print(f"    page{pos_idx+1}: SKIP (pos={len(positions)}, tbl={len(table_entries)})")
            continue

        tag_map = build_tag_map(positions, table_entries)
        n = render_images(orig_pdf, pos_idx, positions, tag_map, drawing_name, out_dir)
        total += n
        covered = sum(1 for p in positions if tag_map.get(p['num']))
        # 统计主条目数（每 seq 只计一次）vs 含附件的总图片数
        unique_seqs = len({seq for seq, tag, sx, sy in table_entries})
        print(f"    page{pos_idx+1}: {len(positions)} pos | "
              f"{unique_seqs} tbl seqs ({len(table_entries)} w/ sub-entries) | "
              f"{covered} mapped | {n} images")

    print(f"  TOTAL: {total} images")
    return total


# ─────────────────────────────────────────────
# 自动发现图纸对
# ─────────────────────────────────────────────

def discover_drawings():
    """发现 OCR_DIR 中的所有图纸对（原始 PDF + OCR PDF）"""
    drawings = []
    orig_pdfs = sorted(glob.glob(os.path.join(OCR_DIR, "* 仪表位置图.pdf")))
    for orig in orig_pdfs:
        basename = os.path.basename(orig)
        drawing_name = basename.replace(' 仪表位置图.pdf', '')
        ocr = orig.replace(' 仪表位置图.pdf', ' 仪表位置图_OCR.pdf')
        if not os.path.exists(ocr):
            print(f"  [警告] 找不到 OCR 文件: {ocr}")
            continue
        drawings.append((drawing_name, orig, ocr))
    return drawings


# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    drawings = discover_drawings()
    print(f"发现 {len(drawings)} 个图纸:")
    for name, orig, ocr in drawings:
        print(f"  {name}")

    grand_total = 0
    for drawing_name, orig_pdf, ocr_pdf in drawings:
        try:
            grand_total += process_drawing(drawing_name, orig_pdf, ocr_pdf)
        except Exception as e:
            import traceback
            print(f"\n[ERROR] {drawing_name}: {e}")
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"  全部完成！共生成 {grand_total} 张图片")
