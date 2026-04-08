import os
import pdfplumber
import re
from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium

os.chdir(r"E:\opencode\位置图处理\仪表位置图OCR")

OUTPUT_ROOT = r"E:\opencode\位置图处理\output\压缩机_21216-400200-IN40"
os.makedirs(OUTPUT_ROOT, exist_ok=True)

# 先查看文件结构
files = [f for f in os.listdir(".") if "400200" in f and f.endswith(".pdf")]
print("Files:", files)

orig_file = (
    files[0]
    if "仪表位置图.pdf" in files[0]
    else [f for f in files if "仪表位置图.pdf" in f][0]
)
ocr_file = [f for f in files if "_OCR.pdf" in f][0]

print(f"Original: {orig_file}")
print(f"OCR: {ocr_file}")

# 先检查PDF结构
with pdfplumber.open(orig_file) as pdf:
    print(f"PDF pages: {len(pdf.pages)}")

with pdfplumber.open(ocr_file) as pdf:
    for i in range(len(pdf.pages)):
        text = pdf.pages[i].extract_text()
        items = re.findall(r"(\d+)\s+(40[A-Z]{1,3}[-\d]+[A-Z]?)", text or "")
        print(f"Page {i + 1}: {len(items)} table items")

# 继续处理 - 需要先了解每页的结构
