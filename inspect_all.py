import pdfplumber
import os
import glob

# Get all OCR files
ocr_files = glob.glob("仪表位置图OCR/*_OCR.pdf")
print(f"Found {len(ocr_files)} OCR files")

output = []

for ocr_path in ocr_files:
    # Get corresponding original file
    base_name = ocr_path.replace("_OCR.pdf", "").replace("仪表位置图OCR\\", "")

    # Find original file
    orig_files = glob.glob(f"仪表位置图OCR/{base_name} 仪表位置图.pdf")

    line = f"\n{'=' * 50}\n"
    line += f"OCR: {ocr_path}\n"
    if orig_files:
        line += f"Orig: {orig_files[0]}\n"
    else:
        line += "Orig: NOT FOUND\n"
    line += f"{'=' * 50}\n"
    output.append(line)

    try:
        with pdfplumber.open(ocr_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                line = f"--- Page {i + 1} ---\n"
                if text:
                    try:
                        line += text[:1500] + "\n"
                    except:
                        line += "[Text has encoding issues]\n"
                else:
                    line += "No text\n"
                output.append(line)
    except Exception as e:
        output.append(f"Error: {e}\n")

with open("inspect_output.txt", "w", encoding="utf-8") as f:
    f.write("".join(output))
