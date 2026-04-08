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
            # 位置图区域
            if 200 < x < 900 and 300 < y < 1200:
                position_numbers.append({"num": text, "x": x, "y": y})

# 按位置排序 (从上到下，从左到右)
position_numbers.sort(key=lambda p: (p["y"], p["x"]))

# 在图片上标记序号和临时位号
img = Image.open(img_path)
draw = ImageDraw.Draw(img)

# 尝试加载字体，如果失败则使用默认字体
try:
    font = ImageFont.truetype("simsun.ttc", 32)
except:
    font = ImageFont.load_default()

scale = 2

# 生成临时位号 (IN01, IN02, ...)
for i, p in enumerate(position_numbers):
    x = p["x"] * scale
    y = p["y"] * scale
    num = p["num"]

    # 临时位号 (用序号作为IN后面的数字)
    temp_tag = f"IN{int(num):02d}" if num.isdigit() else f"IN{num}"

    # 绘制红色圆圈
    radius = 25
    draw.ellipse(
        [x - radius, y - radius, x + radius, y + radius], outline="red", width=3
    )

    # 绘制序号 (红色)
    draw.text((x - 8, y - 40), f"{num}", fill="red", font=font)

    # 绘制临时位号 (蓝色，在序号右边)
    draw.text((x + 35, y - 15), temp_tag, fill="blue", font=font)

print(f"已标记 {len(position_numbers)} 个序号")
for i, p in enumerate(position_numbers):
    temp_tag = f"IN{int(p['num']):02d}" if p["num"].isdigit() else f"IN{p['num']}"
    print(f"  {p['num']} -> {temp_tag}")

# 保存标记后的图片
output_img_path = os.path.join(output_dir, "marked_with_temp_tags.png")
img.save(output_img_path)
print(f"\n已保存到: {output_img_path}")
print("提示：这是临时版本，位号格式为 IN01, IN02...")
print("请提供正确的位号列表后，可以生成最终版本")
