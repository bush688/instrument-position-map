import pdfplumber
from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium
import os

# 原始PDF (位置图)
pdf_path_orig = r"E:\opencode\位置图处理\甲醇罐区21216-400300-IN40 仪表位置图.pdf"
# OCR版本PDF (提取位号数据)
pdf_path_ocr = (
    r"E:\opencode\位置图处理\甲醇罐区21216-400300-IN40 仪表位置图_批量 OCR.pdf"
)
output_dir = r"E:\opencode\位置图处理\output"

# 位号映射 (从OCR版本提取)
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

# 用原始PDF转换为图片
pdf = pdfium.PdfDocument(pdf_path_orig)
page = pdf[0]
pil_img = page.render(scale=2.0).to_pil()
img_path = os.path.join(output_dir, "original_orig.png")
pil_img.save(img_path)

# 从原始PDF提取位置图上的序号位置
position_numbers = []
with pdfplumber.open(pdf_path_orig) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()

    for w in words:
        text = w["text"].strip()
        if text.isdigit() and len(text) <= 2:
            x, y = w["x0"], w["top"]
            # 位置图区域 (原始PDF的坐标)
            if 200 < x < 900 and 300 < y < 1200:
                position_numbers.append({"num": text, "x": x, "y": y})

# 按位置排序 (从上到下，从左到右)
position_numbers.sort(key=lambda p: (p["y"], p["x"]))

print(f"找到 {len(position_numbers)} 个位置图序号:")
for p in position_numbers[:10]:
    print(f"  {p['num']} at x={p['x']:.0f}, y={p['y']:.0f}")
print("  ...")

# 在图片上标记
img = Image.open(img_path)
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("simsun.ttc", 24)
except:
    font = ImageFont.load_default()

scale = 2

for p in position_numbers:
    x = p["x"] * scale
    y = p["y"] * scale
    num = p["num"]
    tag = tag_mapping.get(num, f"IN{num}")

    # 绘制红色圆圈
    radius = 25
    draw.ellipse(
        [x - radius, y - radius, x + radius, y + radius], outline="red", width=3
    )

    # 绘制序号 (红色)
    draw.text((x - 8, y - 40), f"{num}", fill="red", font=font)

    # 绘制位号 (蓝色)
    draw.text((x + 35, y - 15), tag, fill="blue", font=font)

print(f"\n已标记 {len(position_numbers)} 个序号和位号")

output_img_path = os.path.join(output_dir, "marked_final.png")
img.save(output_img_path)
print(f"已保存到: {output_img_path}")
