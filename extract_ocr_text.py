import pdfplumber
import os

pdf_path = r"E:\opencode\位置图处理\甲醇罐区21216-400300-IN40 仪表位置图_批量 OCR.pdf"
output_txt = r"E:\opencode\位置图处理\output\extracted_text.txt"

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    text = page.extract_text()

with open(output_txt, "w", encoding="utf-8") as f:
    f.write(text)

print(f"Extracted text saved to {output_txt}")
print(f"Text length: {len(text)} characters")
