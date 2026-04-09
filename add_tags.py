import pdfplumber
from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium
import os

# PDF路径 - 使用OCR版本
pdf_path = r"E:\opencode\位置图处理\甲醇罐区21216-400300-IN40 仪表位置图_批量 OCR.pdf"
output_dir = r"E:\opencode\位置图处理\output"
os.makedirs(output_dir, exist_ok=True)

# 提取的位号数据
tag_mapping = {
    "1": "40FT-03001",
    "2": "40XZV-03002",
    "3": "40XZV-03001",
    "4": "40LV-03003",
    "5": "40FV-03001",
    "6": "40PT-03055",
    "7": "40TE-03055",
    "8": "40PT-03001",
    "9": "40PV-03001",
    "10": "40PDT-03009",
    "11": "40LT-03003",
    "12": "40LT-03004",
    "13": "40PT-03008",
    "14": "40FT-03003",
    "15": "40PT-03010",
    "16": "40PT-03054",
    "17": "40TE-03054",
    "18": "40PT-03056",
    "19": "40FT-03056",
    "20": "40TE-03056",
    "21": "40FT-03051",
    "22": "40PT-03051",
    "23": "40PT-03052",
    "24": "40PT-03053",
    "25": "40TE-03053",
    "26": "40FT-03002",
    "27": "40LT-03001",
    "28": "40LZT-03002",
    "29": "40TE-03001",
    "30": "40LT-03006",
}

# 转换PDF为图片
pdf = pdfium.PdfDocument(pdf_path)
page = pdf[0]
pil_img = page.render(scale=2.0).to_pil()
img_path = os.path.join(output_dir, "original_ocr.png")
pil_img.save(img_path)

# 提取所有数字
all_numbers = []
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()
    for w in words:
        text = w["text"].strip()
        if text.isdigit() and len(text) <= 2:
            x, y = w["x0"], w["top"]
            if 120 < x < 700 and 1280 < y < 1950:
                all_numbers.append({"num": text, "x": x, "y": y})

# 按y分组
all_numbers.sort(key=lambda p: p["y"])

# 分析每行的y值，找到所有行的位置
rows_y = []
last_y = -1000
for n in all_numbers:
    if abs(n["y"] - last_y) > 30:
        rows_y.append(n["y"])
        last_y = n["y"]

print(f"Found {len(rows_y)} rows at y positions:")
for i, y in enumerate(rows_y):
    print(f"  Row {i + 1}: y={y:.0f}")

# 根据OCR结果，手动创建位置映射表
# 基于OCR文本和行位置，对应关系为：
# 行1: 左=1, 右=15
# 行2: 左=2, 右=16
# 行3: (子项), 右=17
# 行4: (子项), 右=18
# 行5: (子项), 右=19
# 行6: 左=3, 右=20
# 行7: (子项), 右=21
# 行8: (子项), 右=22
# 行9: (子项), 右=23
# 行10: 左=4, 右=24
# 行11: 左=5, 右=25
# 行12: 左=6, 右=26
# 行13: 左=7, 右=27
# 行14: 左=8, 右=28
# 行15: 左=9, 右=29
# 行16: 左=10, 右=30

# 按x分组（左右两列）
left_col = []
right_col = []
for n in all_numbers:
    if n["x"] < 400:
        left_col.append(n)
    else:
        right_col.append(n)

left_col.sort(key=lambda p: p["y"])
right_col.sort(key=lambda p: p["y"])

print(f"\nLeft column ({len(left_col)}): {[n['num'] for n in left_col]}")
print(f"Right column ({len(right_col)}): {[n['num'] for n in right_col]}")

# 创建位置到标签的映射
position_numbers = left_col + right_col
position_numbers.sort(key=lambda p: (p["y"], p["x"]))

print(f"\nTotal: {len(position_numbers)} positions")

# 标记
img = Image.open(img_path)
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("simsun.ttc", 16)
except:
    font = ImageFont.load_default()

scale = 2

for p in position_numbers:
    x, y = p["x"] * scale, p["y"] * scale
    num = p["num"]
    tag = tag_mapping.get(num, f"IN{num}")

    draw.ellipse([x - 15, y - 15, x + 15, y + 15], outline="red", width=2)
    draw.text((x + 2, y - 20), f"{num}", fill="red", font=font)
    draw.text((x + 20, y - 5), tag, fill="blue", font=font)

output_img_path = os.path.join(output_dir, "marked_with_tags.png")
img.save(output_img_path)
print(f"\nSaved to {output_img_path}")
