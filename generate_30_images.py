import pdfplumber
from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium
import os

pdf_path = r"E:\opencode\位置图处理\甲醇罐区21216-400300-IN40 仪表位置图.pdf"
output_dir = r"E:\opencode\位置图处理\output\30份"
os.makedirs(output_dir, exist_ok=True)

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

# 表格位号位置 (继续向下偏移)
table_positions = {
    "40FT-03001": {"x": 260, "y": 1325},
    "40XZV-03002": {"x": 260, "y": 1353},
    "40XZV-03001": {"x": 260, "y": 1381},
    "40LV-03003": {"x": 260, "y": 1409},
    "40FV-03001": {"x": 260, "y": 1437},
    "40PT-03055": {"x": 260, "y": 1465},
    "40TE-03055": {"x": 260, "y": 1493},
    "40PT-03001": {"x": 260, "y": 1521},
    "40PV-03001": {"x": 260, "y": 1549},
    "40PDT-03009": {"x": 260, "y": 1577},
    "40LT-03003": {"x": 260, "y": 1605},
    "40LT-03004": {"x": 260, "y": 1633},
    "40PT-03008": {"x": 260, "y": 1661},
    "40FT-03003": {"x": 260, "y": 1689},
    "40PT-03010": {"x": 740, "y": 1325},
    "40PT-03054": {"x": 740, "y": 1353},
    "40TE-03054": {"x": 740, "y": 1381},
    "40PT-03056": {"x": 740, "y": 1409},
    "40FT-03056": {"x": 740, "y": 1437},
    "40TE-03056": {"x": 740, "y": 1465},
    "40FT-03051": {"x": 740, "y": 1493},
    "40PT-03051": {"x": 740, "y": 1521},
    "40PT-03052": {"x": 740, "y": 1549},
    "40PT-03053": {"x": 740, "y": 1577},
    "40TE-03053": {"x": 740, "y": 1605},
    "40FT-03002": {"x": 740, "y": 1633},
    "40LT-03001": {"x": 740, "y": 1661},
    "40LZT-03002": {"x": 740, "y": 1689},
    "40TE-03001": {"x": 740, "y": 1717},
    "40LT-03006": {"x": 740, "y": 1745},
}

# 转换为图片
pdf = pdfium.PdfDocument(pdf_path)
page = pdf[0]
pil_img = page.render(scale=3.0).to_pil()

# 提取位置图序号
position_numbers = []
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()
    for w in words:
        text = w["text"].strip()
        if text.isdigit() and len(text) <= 2:
            x, y = w["x0"], w["top"]
            if 200 < x < 900 and 300 < y < 1200:
                position_numbers.append({"num": text, "x": x, "y": y})

position_numbers.sort(key=lambda p: (p["y"], p["x"]))

# 字体
try:
    font = ImageFont.truetype("simsun.ttc", 32)
except:
    font = ImageFont.load_default()

scale = 3.0

for p in position_numbers:
    num = p["num"]
    tag = tag_mapping.get(num, "")

    img = pil_img.copy()
    draw = ImageDraw.Draw(img)

    # 1. 位置图标记
    x, y = p["x"] * scale, p["y"] * scale
    radius = 38
    draw.ellipse(
        [x - radius, y - radius, x + radius, y + radius], outline="red", width=4
    )
    draw.text((x - 10, y - 55), f"{num}", fill="red", font=font)
    draw.text((x + 48, y - 15), tag, fill="red", font=font)

    # 2. 表格区域 - 红色方框
    if tag in table_positions:
        tp = table_positions[tag]
        tx, ty = tp["x"] * scale, tp["y"] * scale
        draw.rectangle([tx - 15, ty - 5, tx + 220, ty + 40], outline="red", width=4)

    # 保存为PNG
    output_name = f"甲醇罐区21216-400300-IN40_{tag}.png"
    output_path = os.path.join(output_dir, output_name)
    img.save(output_path, "PNG")
    print(f"已生成: {output_name}")

print(f"\n完成！")
