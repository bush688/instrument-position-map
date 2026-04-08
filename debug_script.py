import os
import pdfplumber
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont
import re

os.chdir(r"E:\opencode\位置图处理\仪表位置图OCR")

output_dir = r"E:\opencode\位置图处理\output\氨合成_21216-040500-IN40"
os.makedirs(output_dir, exist_ok=True)

print("Starting...")

# Clear existing
for f in os.listdir(output_dir):
    if f.endswith(".png"):
        os.remove(os.path.join(output_dir, f))

ocr_files = [f for f in os.listdir(".") if "040500" in f and "_OCR" in f]
print(f"OCR files: {ocr_files}")
ocr_file = ocr_files[0]

try:
    font = ImageFont.truetype("simsun.ttc", 32)
    print("Font loaded")
except Exception as e:
    print(f"Font error: {e}")
    font = ImageFont.load_default()

scale = 3.0

# === PAGE 1 ===
print("\n=== Page 1 ===")
orig_file = "氨合成_page1.pdf"
print(f"Opening: {orig_file}")

with pdfplumber.open(orig_file) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()

print(f"Words: {len(words)}")

position_numbers = []
for w in words:
    text = w["text"].strip()
    if text.isdigit() and len(text) <= 3:
        x, y = w["x0"], w["top"]
        if 100 < x < 900 and 150 < y < 1200:
            position_numbers.append({"num": text, "x": x, "y": y})

print(f"Raw positions: {len(position_numbers)}")

seen = set()
unique_pos = []
for p in position_numbers:
    key = (p["num"], int(p["y"]))
    if key not in seen:
        seen.add(key)
        unique_pos.append(p)

unique_pos.sort(key=lambda p: (p["y"], p["x"]))
position_numbers = unique_pos
print(f"Unique positions: {len(position_numbers)}")

if not position_numbers:
    print("No positions found!")
else:
    print("First 5:", [p["num"] for p in position_numbers[:5]])
