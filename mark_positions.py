import pdfplumber
from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium
import os

# PDF路径
pdf_path = r"E:\opencode\位置图处理\甲醇罐区21216-400300-IN40 仪表位置图.pdf"
output_dir = r"E:\opencode\位置图处理\output"
os.makedirs(output_dir, exist_ok=True)

# 转换PDF为图片 (2x缩放)
pdf = pdfium.PdfDocument(pdf_path)
page = pdf[0]
pil_img = page.render(scale=2.0).to_pil()
img_path = os.path.join(output_dir, "original.png")
pil_img.save(img_path)

# 提取位置图上的序号
position_numbers = []
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()

    for w in words:
        text = w["text"].strip()
        if text.isdigit() and len(text) <= 2:
            x, y = w["x0"], w["top"]
            # 位置图区域 (根据之前的分析)
            if 200 < x < 900 and 300 < y < 1200:
                position_numbers.append({"num": text, "x": x, "y": y})

# 按位置排序
position_numbers.sort(key=lambda p: (p["y"], p["x"]))

# 在图片上标记序号位置
img = Image.open(img_path)
draw = ImageDraw.Draw(img)

# 2x缩放因子
scale = 2

# 绘制红色圆圈和序号
for i, p in enumerate(position_numbers):
    x = p["x"] * scale
    y = p["y"] * scale
    num = p["num"]

    # 绘制红色圆圈
    radius = 30
    draw.ellipse(
        [x - radius, y - radius, x + radius, y + radius], outline="red", width=3
    )

    # 绘制序号 (红色)
    draw.text((x + 35, y - 15), f"{num}", fill="red")

print(f"标记了 {len(position_numbers)} 个序号")
print("位置图序号:", [p["num"] for p in position_numbers])

# 保存标记后的图片
output_img_path = os.path.join(output_dir, "marked_position_map.png")
img.save(output_img_path)
print(f"已保存到: {output_img_path}")
