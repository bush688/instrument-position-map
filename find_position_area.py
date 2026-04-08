import pdfplumber
from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium
import os

# PDF路径 - 使用OCR版本
pdf_path = r"E:\opencode\位置图处理\甲醇罐区21216-400300-IN40 仪表位置图_批量 OCR.pdf"
output_dir = r"E:\opencode\位置图处理\output"

# 位号映射
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

# 转换为图片
pdf = pdfium.PdfDocument(pdf_path)
page = pdf[0]
pil_img = page.render(scale=2.0).to_pil()
img_path = os.path.join(output_dir, "original_ocr.png")
pil_img.save(img_path)

# 查找位置图上的序号 - 需要找到y在300-1200区域
# 先查看所有数字的位置分布
all_numbers = []
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()

    for w in words:
        text = w["text"].strip()
        if text.isdigit() and len(text) <= 2:
            x, y = w["x0"], w["top"]
            all_numbers.append({"num": text, "x": x, "y": y})

# 打印y坐标分布，找出位置图区域
print("=== 数字位置分布 (按y坐标) ===")
y_groups = {}
for n in all_numbers:
    y_key = int(n["y"] / 50) * 50  # 按50分组
    if y_key not in y_groups:
        y_groups[y_key] = []
    y_groups[y_key].append(n["num"])

for y in sorted(y_groups.keys()):
    nums = y_groups[y]
    print(f"y={y}-{y + 50}: {nums}")
