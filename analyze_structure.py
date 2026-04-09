import pdfplumber
import os

pdf_path = r"E:\opencode\位置图处理\甲醇罐区21216-400300-IN40 仪表位置图_批量 OCR.pdf"

# 读取之前提取的文本
with open(
    r"E:\opencode\位置图处理\output\extracted_text.txt", "r", encoding="utf-8"
) as f:
    text = f.read()

# 分析结构
lines = text.split("\n")
print("=== OCR文本分析 ===")
for i, line in enumerate(lines):
    if "EL" in line or "平面" in line:
        print(f"{i}: {line}")

# 查找位置图区域
print("\n=== 位置图编号 ===")
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()

    # 找A, B, C, D, E列字母附近(y=0-1200)
    for w in words:
        text = w["text"].strip()
        if text in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
            x, y = w["x0"], w["top"]
            if y < 1200:
                print(f"{text} at x={x:.0f}, y={y:.0f}")
