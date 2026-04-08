import os
import pdfplumber
import re

os.chdir(r"E:\opencode\位置图处理\仪表位置图OCR")

# First file: 氨合成_21216-040500
f = "氨合成_21216-040500-IN40 仪表位置图_OCR.pdf"
print(f"=== {f} ===")

with pdfplumber.open(f) as pdf:
    page = pdf.pages[0]
    text = page.extract_text()

# Extract tag numbers and tags
lines = text.split("\n")
for i, line in enumerate(lines[:100]):
    print(f"{i}: {line}")
