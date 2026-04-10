"""
export_table.py  ——  将所有仪表位置图的对照表导出为 Excel 文档。

输出列：图纸名称 | 图纸编号 | 页码 | 序号 | 仪表位号 | 标高 | 区域

运行方式：
    python export_table.py
生成：output/仪表位置图汇总表.xlsx
"""
import os
import re
import glob
import pdfplumber
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── 路径配置 ──────────────────────────────────────────────
OCR_DIR  = r"E:\opencode\位置图处理\仪表位置图OCR"
OUT_FILE = r"E:\opencode\位置图处理\output\仪表位置图汇总表.xlsx"

# ── 正则 ──────────────────────────────────────────────────
TAG_RE  = re.compile(r'^(?:[0-9]{2})?[A-Z]{2,6}-[0-9][0-9A-Z]*$')
AREA_RE = re.compile(r'^[A-Z]{1,2}\d{1,2}$')       # 区域：如 F6, D5, G3, AA1
EL_RE   = re.compile(r'^EL[+\-]?\d', re.IGNORECASE)
NUM_RE  = re.compile(r'^\d{1,3}$')

# OCR 常见标点误识别（逗号→句点）
def clean_elevation(s: str) -> str:
    return s.replace(',', '.').strip()


# ── 单页提取 ──────────────────────────────────────────────

def extract_page_rows(page) -> list[dict]:
    """
    提取一页中的所有仪表行：
      [(seq, tag, elevation, area), ...]
    支持多列布局、EL 被 OCR 拆分为多词的情况。
    """
    words = page.extract_words()
    if not words:
        return []

    # 1. 按 y 分桶（桶高 14pt），每桶为一视觉行
    BUCKET = 14
    rows: dict[int, list] = {}
    for w in words:
        b = round(w['top'] / BUCKET)
        rows.setdefault(b, []).append(w)

    result: list[dict] = []
    # 记录上一个拥有完整信息（elevation）的行，用于子条目继承
    _last_full: dict = {}

    for _b, row_words in sorted(rows.items()):
        row_words = sorted(row_words, key=lambda w: w['x0'])

        # 收集本行的各类 token
        seqs:   list[tuple[float, int]]  = []   # (x, int)
        tags:   list[tuple[float, str]]  = []   # (x, tag)
        el_toks: list[tuple[float, str]] = []   # (x, text) — EL 相关碎片
        areas:  list[tuple[float, str]]  = []   # (x, area_code)

        i = 0
        while i < len(row_words):
            w = row_words[i]
            t = w['text'].strip()
            x = w['x0']

            if NUM_RE.match(t) and 1 <= int(t) <= 300:
                seqs.append((x, int(t)))

            elif TAG_RE.match(t):
                tags.append((x, t))

            elif EL_RE.match(t) or t.upper() == 'EL':
                # 贪婪合并：OCR 常把 EL+0.55 拆成多个 token，如：
                #   'EL+0.' + '55'  或  'EL' + '+' + '0.' + '55'
                # 策略：从当前位置向右，把 x 相邻（<60pt）的数字/符号/小数碎片合并进来
                merged = t
                j = i + 1
                while j < len(row_words):
                    nw = row_words[j]
                    gap = nw['x0'] - (x + len(merged) * 5.5)
                    nt = nw['text'].strip()
                    # 接受：纯符号(+/-)、纯数字、小数点结尾的数字（如"0."）或纯小数部分（如"55"）
                    is_fragment = (
                        gap < 60 and (
                            nt in ('+', '-') or
                            re.match(r'^\d[\d.]*$', nt) or
                            re.match(r'^[+\-]?\d[\d.]*$', nt)
                        )
                    )
                    if is_fragment:
                        merged += nt
                        j += 1
                    else:
                        break
                el_toks.append((x, merged))
                i = j - 1  # 外层 i += 1 补上最后一步

            elif AREA_RE.match(t) and not TAG_RE.match(t):
                areas.append((x, t))

            i += 1

        if not tags:
            continue

        # 2. el_toks 已在扫描阶段贪婪合并，直接使用
        el_groups = el_toks  # list of (x, merged_el_str)

        # 3. 为每个 tag 找最近的 seq（左侧）、elevation（右侧最近）、area（elevation 右侧）
        for tx, tag in tags:
            # seq：tag 左侧最近
            seq = None
            best_dx = float('inf')
            for sx, sv in seqs:
                dx = tx - sx
                if 5 <= dx <= 600 and dx < best_dx:
                    best_dx = dx
                    seq = sv

            # elevation：tag 右侧最近的 EL 段
            elev = ''
            elev_x = None
            best_dx = float('inf')
            for ex, et in el_groups:
                dx = ex - tx
                if 0 < dx <= 400 and dx < best_dx:
                    best_dx = dx
                    elev = et
                    elev_x = ex

            # area：elevation 右侧最近的区域码（AREA_RE）
            area = ''
            search_from = elev_x + 1 if elev_x is not None else tx
            best_dx = float('inf')
            for ax, av in areas:
                dx = ax - search_from
                if 0 < dx <= 300 and dx < best_dx:
                    best_dx = dx
                    area = av

            row_data = {
                'seq':       seq,
                'tag':       tag,
                'elevation': clean_elevation(elev),
                'area':      area,
            }
            # 子条目（无 elevation）继承最近父行的 elevation/area
            if not elev and _last_full:
                row_data['elevation'] = _last_full.get('elevation', '')
                row_data['area']      = _last_full.get('area', '')
            elif elev:
                _last_full = row_data
            result.append(row_data)

    return result


# ── 发现图纸 ──────────────────────────────────────────────

def discover_drawings():
    drawings = []
    for ocr_path in sorted(glob.glob(os.path.join(OCR_DIR, "* 仪表位置图_OCR.pdf"))):
        basename = os.path.basename(ocr_path)
        drawing_name = basename.replace(' 仪表位置图_OCR.pdf', '')
        # 分离图纸名称和编号（格式：名称_编号）
        parts = drawing_name.split('_', 1)
        title = parts[0]
        number = parts[1] if len(parts) > 1 else ''
        drawings.append((drawing_name, title, number, ocr_path))
    return drawings


# ── 全量提取 ──────────────────────────────────────────────

def extract_all() -> list[dict]:
    rows = []
    for drawing_name, title, number, ocr_path in discover_drawings():
        print(f"  {drawing_name} ...", end='', flush=True)
        try:
            with pdfplumber.open(ocr_path) as pdf:
                n = len(pdf.pages)
            for pi in range(n):
                with pdfplumber.open(ocr_path) as pdf:
                    page_rows = extract_page_rows(pdf.pages[pi])
                for r in page_rows:
                    rows.append({
                        '图纸名称': title,
                        '图纸编号': number,
                        '页码':     pi + 1,
                        '序号':     r['seq'] if r['seq'] is not None else '',
                        '仪表位号': r['tag'],
                        '标高':     r['elevation'],
                        '区域':     r['area'],
                    })
            print(f" {n} pages, {sum(1 for r in rows if r['图纸名称'] == title)} rows")
        except Exception as e:
            print(f" ERROR: {e}")
    return rows


# ── Excel 输出 ────────────────────────────────────────────

COLS = ['图纸名称', '图纸编号', '页码', '序号', '仪表位号', '标高', '区域']
COL_WIDTHS = [14, 22, 6, 6, 18, 12, 8]

HDR_FILL  = PatternFill("solid", fgColor="1F4E79")
HDR_FONT  = Font(name="微软雅黑", bold=True, color="FFFFFF", size=10)
ROW_FONT  = Font(name="微软雅黑", size=9)
ALT_FILL  = PatternFill("solid", fgColor="EBF3FB")

thin = Side(style='thin', color='B0C4DE')
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

CENTER = Alignment(horizontal='center', vertical='center', wrap_text=False)
LEFT   = Alignment(horizontal='left',   vertical='center', wrap_text=False)


def write_excel(rows: list[dict], out_path: str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "仪表位置图汇总"

    # 标题行
    for ci, (col, width) in enumerate(zip(COLS, COL_WIDTHS), 1):
        cell = ws.cell(row=1, column=ci, value=col)
        cell.font = HDR_FONT
        cell.fill = HDR_FILL
        cell.border = BORDER
        cell.alignment = CENTER
        ws.column_dimensions[get_column_letter(ci)].width = width
    ws.row_dimensions[1].height = 20
    ws.freeze_panes = 'A2'

    # 数据行
    prev_drawing = None
    alt = False
    for ri, row in enumerate(rows, 2):
        if row['图纸名称'] != prev_drawing:
            alt = not alt
            prev_drawing = row['图纸名称']
        fill = ALT_FILL if alt else PatternFill()

        for ci, col in enumerate(COLS, 1):
            val = row[col]
            cell = ws.cell(row=ri, column=ci, value=val)
            cell.font = ROW_FONT
            cell.fill = fill
            cell.border = BORDER
            cell.alignment = CENTER if ci in (3, 4) else LEFT

    # 自动筛选
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLS))}{len(rows)+1}"

    wb.save(out_path)
    print(f"\n已保存：{out_path}")
    print(f"共 {len(rows)} 行数据")


# ── 入口 ─────────────────────────────────────────────────

if __name__ == '__main__':
    print("正在提取仪表对照表数据...\n")
    rows = extract_all()

    # 去重：同一图纸/页码/位号只保留一条（多列表格可能重复提取）
    seen = set()
    deduped = []
    for r in rows:
        key = (r['图纸名称'], r['页码'], r['仪表位号'])
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    print(f"\n提取完成，共 {len(deduped)} 条（去重后）")

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    write_excel(deduped, OUT_FILE)
