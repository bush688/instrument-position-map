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


def process_drawing(drawing_name, pattern):
    files = glob.glob(pattern)
    orig_file = [f for f in files if "_OCR" not in f][0]
    ocr_file = [f for f in files if "_OCR" in f][0]

    OUTPUT_ROOT = f"E:\\opencode\\位置图处理\\output\\{drawing_name}"
    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    print(f"\n=== Processing {drawing_name} ===")

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

        # 提取表格 - 使用更通用的模式
        with pdfplumber.open(ocr_file) as pdf:
            if page_idx >= len(pdf.pages):
                continue
            text = pdf.pages[page_idx].extract_text()

        # 匹配各种格式的位号
        table_order = []
        for line in (text or "").splitlines():
            # 匹配: 数字 + 位号(字母-字母-数字)
            matches = re.findall(
                r"(\d+)\s+([A-Z]{2,}[A-Z0-9]*-[A-Z0-9]+-[A-Z0-9]+)", line
            )
            for num_str, tag in matches:
                try:
                    n = int(num_str)
                    table_order.append((n, tag))
                except:
                    pass

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

    print(f"  Total: {total} images")
    return total


# 批量处理
remaining = [
    ("循环水场_21216-210000-IN40", "*210000*"),
    ("变换气_21216-040300-IN40", "*040300*"),
    ("原料_21216-030000-IN40", "*030000*"),
    ("备煤_21216-400100-IN40", "*400100*"),
    ("渣油_21216-040900-IN40", "*040900*"),
    ("储运_21216-400400-IN40", "*400400*"),
    ("脱硫_21216-040200-IN40", "*040200*"),
    ("脱碳工段_21216-040800-IN40", "*040800*"),
]

grand_total = 0
for name, pattern in remaining:
    try:
        grand_total += process_drawing(name, pattern)
    except Exception as e:
        print(f"Error: {e}")

print(f"\n=== GRAND TOTAL: {grand_total} images ===")
