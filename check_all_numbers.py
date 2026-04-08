import pdfplumber
import os

pdf_path = r"E:\opencode\位置图处理\甲醇罐区21216-400300-IN40 仪表位置图_批量 OCR.pdf"

# 查看所有单个和双位数字的位置
print("=== 所有数字位置 ===")
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()

    for w in words:
        text = w["text"].strip()
        if text.isdigit() and len(text) <= 2:
            x, y = w["x0"], w["top"]
            print(f"{text} at x={x:.0f}, y={y:.0f}")
