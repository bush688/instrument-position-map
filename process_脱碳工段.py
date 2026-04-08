import os
import glob
import pdfplumber
import re
from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium

os.chdir(r"E:\opencode\位置图处理\仪表位置图OCR")

try:
    FONT = ImageFont.truetype("simsun.ttc", 26)
except:
    FONT = ImageFont.load_default()

SCALE = 3.0


def extract_table(text):
    """从OCR文本提取表格数据 - 支持多种位号格式"""
    table_order = []
    lines = (text or "").splitlines()
    for line in lines:
        # 匹配: 数字 + 空格 + 位号
        # 格式1: 04PT-04001 (前缀2位数字)
        # 格式2: PT-04001 (无前缀)
        # 格式3: LP-04P0802A (字母-数字-字母)
        match = re.search(r"^(\d+)\s+([A-Z]{1,4}[A-Z0-9]*-[\d]+[A-Z]?)", line)
        if match:
            try:
                n = int(match.group(1))
                tag = match.group(2)
                table_order.append((n, tag))
            except:
                pass
    return table_order


def process_drawing(drawing_name, pattern):
    files = glob.glob(pattern)
    if not files:
        print(f"No files for {pattern}")
        return 0
    orig_file = [f for f in files if "_OCR" not in f][0]
    ocr_file = [f for f in files if "_OCR" in f][0]

    OUTPUT_ROOT = f"E:\\opencode\\位置图处理\\output\\{drawing_name}"
    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    print(f"\n=== {drawing_name} ===")

    with pdfplumber.open(orig_file) as pdf:
        num_pages = len(pdf.pages)
    print(f"  Pages: {num_pages}")

    total = 0

    for page_idx in range(num_pages):
        # 提取位置图序号
        with pdfplumber.open(orig_file) as pdf:
            if page_idx >= len(pdf.pages):
                break
            words = pdf.pages[page_idx].extract_words()

        positions = []
        for w in words:
            text = w["text"].strip()
            if text.isdigit() and len(text) <= 2:
                x, y = w["x0"], w["top"]
                if 100 < x < 900 and 100 < y < 1300:
                    try:
                        n = int(text)
                        if 1 <= n <= 100:
                            positions.append({"num": text, "x": x, "y": y})
                    except:
                        pass

        positions.sort(key=lambda p: (p["y"], p["x"]))

        if not positions:
            continue

        # 提取表格
        with pdfplumber.open(ocr_file) as pdf:
            if page_idx >= len(pdf.pages):
                continue
            text = pdf.pages[page_idx].extract_text()

        table_order = extract_table(text)

        print(f"  Page {page_idx + 1}: {len(positions)} pos, {len(table_order)} table")

        if not table_order:
            continue

        # 映射
        first_index_of = {num: idx for idx, (num, _) in enumerate(table_order)}
        tag_map = {}
        last_tag = None

        for p in positions:
            n = int(p["num"])
            if n in first_index_of:
                tag = table_order[first_index_of[n]][1]
                last_tag = tag
            else:
                tag = last_tag if last_tag else ""
            tag_map[p["num"]] = tag

        # 生成图片
        pdf_doc = pdfium.PdfDocument(orig_file)
        base = pdf_doc[page_idx].render(scale=SCALE).to_pil()

        for p in positions:
            num = p["num"]
            tag = tag_map.get(num, "")
            if not tag:
                continue

            img = base.copy()
            draw = ImageDraw.Draw(img)
            x = p["x"] * SCALE
            y = p["y"] * SCALE
            r = 32
            draw.ellipse([x - r, y - r, x + r, y + r], outline="red", width=3)
            draw.text((x - 6, y - 45), num, fill="red", font=FONT)
            draw.text((x + 36, y - 12), tag, fill="red", font=FONT)

            out_name = f"{drawing_name}_page{page_idx + 1}_{num}_{tag}.png"
            img.save(os.path.join(OUTPUT_ROOT, out_name), "PNG")
            total += 1

    print(f"  Total: {total}")
    return total


# 只处理脱碳工段
grand_total = process_drawing("脱碳工段_21216-040800-IN40", "*040800*")
print(f"\n=== TOTAL: {grand_total} ===")
