import os
import pdfplumber

os.chdir(r"E:\opencode\位置图处理\仪表位置图OCR")

# Get all position numbers from page 1
with pdfplumber.open("氨合成_page1.pdf") as pdf:
    page = pdf.pages[0]
    words = page.extract_words()

position_numbers = []
for w in words:
    text = w["text"].strip()
    if text.isdigit() and len(text) <= 3:
        x, y = w["x0"], w["top"]
        if 100 < x < 900 and 150 < y < 1200:
            position_numbers.append({"num": text, "x": x, "y": y})

# Deduplicate
seen = set()
unique_pos = []
for p in position_numbers:
    key = (p["num"], int(p["y"]))
    if key not in seen:
        seen.add(key)
        unique_pos.append(p)

unique_pos.sort(key=lambda p: (p["y"], p["x"]))

# Get unique numbers
unique_nums = sorted(set(int(p["num"]) for p in unique_pos))

print(f"Total position points: {len(unique_pos)}")
print(f"Unique numbers: {len(unique_nums)}")
print(f"\nAll unique numbers: {unique_nums}")

# Check which ones are missing from table (seq 1-5 not in table)
print(f"\nNumbers 1-28 (first column range):")
for n in unique_nums:
    if 1 <= n <= 28:
        print(f"  {n}")
