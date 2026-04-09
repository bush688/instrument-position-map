import pypdfium2 as pdfium
import re

pdf_path = r"E:\opencode\位置图处理\甲醇罐区21216-400300-IN40 仪表位置图.pdf"

pdf = pdfium.PdfDocument(pdf_path)
page = pdf[0]

# Get textpage
textpage = page.get_textpage()

# Get text with correct API
text = textpage.get_text_range()
lines = text.split("\n")

# Find lines with IN pattern (仪表位号)
print("=== Lines with IN pattern ===")
for line in lines:
    if "IN" in line.upper() and not line.strip().startswith("21216"):
        # Check if line has both number and IN
        if re.search(r"\d+.*IN", line, re.IGNORECASE):
            print(line[:120])

print("\n=== Looking for table section ===")
# Find where the table data starts
for i, line in enumerate(lines):
    if "仪表位号" in line or "序号" in line:
        print(f"{i}: {line}")
