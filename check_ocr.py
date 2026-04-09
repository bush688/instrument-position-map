import pdfplumber

pdf_path = r"E:\opencode\位置图处理\甲醇罐区21216-400300-IN40 仪表位置图_批量 OCR.pdf"

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()

    print("=== All numbers in position map area ===")
    for w in words:
        text = w["text"].strip()
        if text.isdigit() and len(text) <= 2:
            x, y = w["x0"], w["top"]
            print(f"{text} at x={x:.0f}, y={y:.0f}")
            if 200 < x < 900 and 300 < y < 1200:
                print(f"  -> In position map area")
