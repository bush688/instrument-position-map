import pdfplumber
from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium
import os

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
img_path = os.path.join(output_dir, "debug_orig.png")
pil_img.save(img_path)

# 查看图片内容：位置图在图片的上半部分 (y < 1200)
# 位置图上的数字应该在 y=200-1100 区域
# 根据之前的分析，在位置图区域(x=300-800, y=200-1100)应该有仪表位置编号

# 由于PDF文字提取找不到位置图数字，我们需要查看图片
# 图片大约3368x4768，位置图应该在 y=400-2200 区域

# 让我查看y在100-1200之间的所有文字
print("=== 位置图区域文字 (y=100-1200) ===")
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()

    for w in words:
        text = w["text"].strip()
        if text and 100 < w["top"] < 1200:
            print(f"{text} at x={w['x0']:.0f}, y={w['top']:.0f}")
