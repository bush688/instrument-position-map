import os
import glob
import pdfplumber
import re
from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium

os.chdir(r"E:\opencode\位置图处理\仪表位置图OCR")

# 自动找到文件
files = glob.glob("*400200*.pdf")
orig_file = [f for f in files if "_OCR" not in f][0]
ocr_file = [f for f in files if "_OCR" in f][0]

drawing_name = "压缩机_21216-400200-IN40"
OUTPUT_ROOT = f"E:\\opencode\\位置图处理\\output\\{drawing_name}"
os.makedirs(OUTPUT_ROOT, exist_ok=True)

print(f"Processing: {orig_file}")

try:
    FONT = ImageFont.truetype("simsun.ttc", 26)
except:
    FONT = ImageFont.load_default()

SCALE = 3.0

# 只处理Page 0
page_idx = 0

# 提取位置图序号
with pdfplumber.open(orig_file) as pdf:
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
print(f"Positions: {len(positions)}")

# 提取表格
with pdfplumber.open(ocr_file) as pdf:
    text = pdf.pages[page_idx].extract_text()

table_order = []
for line in (text or "").splitlines():
    for num_str, tag in re.findall(r"(\d+)\s+(40[A-Z]{1,3}[-\d]+[A-Z]?)", line):
        try:
            n = int(num_str)
            table_order.append((n, tag))
        except:
            pass

print(f"Table items: {len(table_order)}")

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

    out_name = f"{drawing_name}_page1_{num}_{tag}.png"
    img.save(os.path.join(OUTPUT_ROOT, out_name), "PNG")
    count += 1

print(f"Done! Generated {count} images")
