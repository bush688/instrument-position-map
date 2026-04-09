import os
import pdfplumber
import re
from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium

os.chdir(r"E:\opencode\位置图处理\仪表位置图OCR")

OUTPUT_ROOT = r"E:\opencode\位置图处理\output\变换_21216-040100-IN40"
os.makedirs(OUTPUT_ROOT, exist_ok=True)

orig_file = "变换_21216-040100-IN40 仪表位置图.pdf"

for f in os.listdir("."):
    if "040100" in f and "_OCR" in f:
        ocr_file = f
        break

print(f"OCR: {ocr_file}")

try:
    FONT = ImageFont.truetype("simsun.ttc", 26)
except:
    FONT = ImageFont.load_default()

SCALE = 3.0

# 需要处理的页面配对 (位置图页, OCR表页)
# 根据前面的分析：
# Page1: 位置图+表
# Page2: 位置图+表
# Page3: 位置图+表
# Page4: 位置图+表
# Page5: 纯图例，跳过
# Page6: 位置图+表
# Page7: 位置图+表
# Page8: 位置图+表
pairs = [(0, 0), (1, 1), (2, 2), (3, 3), (5, 5), (6, 6), (7, 7)]

total = 0

for pos_page, table_page in pairs:
    print(f"\n--- Processing Page {pos_page + 1} ---")

    # 提取位置图序号
    with pdfplumber.open(orig_file) as pdf:
        if pos_page >= len(pdf.pages):
            continue
        words = pdf.pages[pos_page].extract_words()

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
    print(f"  Positions: {len(positions)}")

    # 提取表格
    with pdfplumber.open(ocr_file) as pdf:
        if table_page >= len(pdf.pages):
            continue
        text = pdf.pages[table_page].extract_text()

    table_order = []
    for line in (text or "").splitlines():
        for num_str, tag in re.findall(r"(\d+)\s+(04[A-Z]{1,3}[-\d]+[A-Z]?)", line):
            try:
                n = int(num_str)
                table_order.append((n, tag))
            except:
                pass

    print(f"  Table items: {len(table_order)}")

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
    if pos_page >= len(pdf_doc):
        continue

    base = pdf_doc[pos_page].render(scale=SCALE).to_pil()
    count = 0

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

        out_name = f"变换_21216-040100-IN40_page{pos_page + 1}_{num}_{tag}.png"
        img.save(os.path.join(OUTPUT_ROOT, out_name), "PNG")
        count += 1

    print(f"  Generated: {count}")
    total += count

print(f"\n=== DONE! Total: {total} images ===")
