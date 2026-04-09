import os
import pdfplumber

os.chdir(r"E:\opencode\位置图处理\仪表位置图OCR")

files = [f for f in os.listdir(".") if "040500" in f]
orig_file = [f for f in files if not f.endswith("_OCR.pdf")][0]

with pdfplumber.open(orig_file) as pdf:
    print(f"Total pages: {len(pdf.pages)}")

    for page_idx in range(len(pdf.pages)):
        page = pdf.pages[page_idx]
        words = page.extract_words()

        # Find numbers in position map area (left side)
        position_numbers = []
        for w in words:
            text = w["text"].strip()
            if text.isdigit() and len(text) <= 3:
                x, y = w["x0"], w["top"]
                if 100 < x < 900 and 150 < y < 1200:
                    position_numbers.append({"num": text, "x": x, "y": y})

        print(f"\nPage {page_idx + 1}: {len(position_numbers)} position numbers")
        if position_numbers:
            position_numbers.sort(key=lambda p: (p["y"], p["x"]))
            for p in position_numbers[:20]:
                print(f"  {p['num']}: x={p['x']:.1f}, y={p['y']:.1f}")
            if len(position_numbers) > 20:
                print(f"  ... and {len(position_numbers) - 20} more")
