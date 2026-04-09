import os
import pdfplumber
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont
import re

os.chdir(r"E:\opencode\位置图处理\仪表位置图OCR")

output_dir = r"E:\opencode\位置图处理\output\氨合成_21216-040500-IN40"

# Find OCR file
ocr_files = [f for f in os.listdir(".") if "040500" in f and "_OCR" in f]
if not ocr_files:
    print("No OCR file")
    exit()

ocr_file = ocr_files[0]
print(f"Using OCR: {ocr_file}")

# Process each page split
for page_num in range(1, 8):
    orig_file = f"氨合成_page{page_num}.pdf"

    if not os.path.exists(orig_file):
        continue

    print(f"\n=== {orig_file} ===")

    # Get position numbers
    with pdfplumber.open(orig_file) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()

    position_numbers = []
    for w in words:
        text = w["text"].strip()
        if text.isdigit() and len(text) <= 3:
            x, y = w["x0"], w["top"]
            if 100 < x < 900 and 150 < y < 1200:
                position_numbers.append({"num": text, "x": x, "y": y})

    position_numbers.sort(key=lambda p: int(p["num"]) if p["num"].isdigit() else 999)

    if not position_numbers:
        print("No position numbers")
        continue

    print(f"Position numbers: {len(position_numbers)}")

    # Get tags from OCR page
    with pdfplumber.open(ocr_file) as pdf:
        ocr_page = pdf.pages[page_num - 1]
        ocr_text = ocr_page.extract_text()

    # Extract ALL tags from text (more flexible pattern)
    pattern = r"(\d+)\s+(04[A-Z]{1,3}[-\d]+)"
    matches = re.findall(pattern, ocr_text)

    # Remove duplicates by number
    unique_tags = {}
    for num, tag in matches:
        if num not in unique_tags:
            unique_tags[int(num)] = tag

    # Sort by number
    table_tags = sorted(unique_tags.items(), key=lambda x: x[0])
    print(f"Tags from table: {len(table_tags)}")

    # Map: match by position in list (not by number)
    tag_mapping = {}
    for i, p in enumerate(position_numbers):
        if i < len(table_tags):
            tag_mapping[p["num"]] = table_tags[i][1]

    # Print mapping sample
    print("Sample mapping:")
    for p in position_numbers[:5]:
        tag = tag_mapping.get(p["num"], "MISSING")
        print(f"  {p['num']} -> {tag}")
