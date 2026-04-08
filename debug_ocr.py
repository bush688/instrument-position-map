import os, glob, pdfplumber, re

os.chdir(r"E:\opencode\位置图处理\仪表位置图OCR")
files = glob.glob("*040300*")
ocr = [f for f in files if "_OCR" in f][0]

with pdfplumber.open(ocr) as pdf:
    text = pdf.pages[0].extract_text()

# 打印前50行看格式
lines = (text or "").splitlines()
output = []
for i, line in enumerate(lines[:50]):
    output.append(f"{i}: {line}\n")

with open("debug_output.txt", "w", encoding="utf-8") as f:
    f.writelines(output)

# 尝试匹配
table_order = []
for line in lines:
    # 更宽松的匹配: 数字 + 字母数字-字母数字-字母数字
    match = re.search(r"^(\d+)\s+(\d{2}[A-Za-z]+-[A-Za-z0-9]+)", line)
    if match:
        try:
            n = int(match.group(1))
            tag = match.group(2)
            table_order.append((n, tag))
        except:
            pass

print(f"Found {len(table_order)} items")
with open("debug_output.txt", "a", encoding="utf-8") as f:
    for i, (n, tag) in enumerate(table_order[:20]):
        f.write(f"  {n}: {tag}\n")
