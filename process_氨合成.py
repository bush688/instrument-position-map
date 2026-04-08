import os
import pdfplumber
import re
import math
from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium

os.chdir(r"E:\opencode\位置图处理\仪表位置图OCR")

# Output dir for this dataset
OUTPUT_ROOT = r"E:\opencode\位置图处理\output\氨合成_21216-040500-IN40"
os.makedirs(OUTPUT_ROOT, exist_ok=True)

# OCR source (all pages contain table data; we'll flatten per page as needed)
OCR_FILE = None
for f in os.listdir("."):
    if "040500" in f and "_OCR" in f:
        OCR_FILE = f
        break
if OCR_FILE is None:
    raise SystemExit("OCR file not found for 040500")

try:
    FONT = ImageFont.truetype("simsun.ttc", 32)
except Exception:
    FONT = ImageFont.load_default()

SCALE = 3.0


def flatten_table_order_from_text(text: str):
    # Read lines, extract all (num, tag) pairs per line, preserve line order
    order = []
    for line in (text or "").splitlines():
        for num_str, tag in re.findall(r"(\d+)\s+(04[A-Z]{1,3}[-\d]+)", line):
            try:
                n = int(num_str)
            except ValueError:
                continue
            order.append((n, tag))
    return order


def extract_position_numbers(orig_path: str):
    with pdfplumber.open(orig_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
    nums = []
    for w in words:
        text = w["text"].strip()
        if text.isdigit() and len(text) <= 3:
            x, y = w["x0"], w["top"]
            if 100 < x < 900 and 150 < y < 1500:
                nums.append({"num": text, "x": x, "y": y})
    seen = set()
    uniq = []
    for p in nums:
        key = (p["num"], int(p["y"]))
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    uniq.sort(key=lambda p: (p["y"], p["x"]))
    return uniq


def map_positions_to_tags(position_numbers, table_order):
    # table_order: list of (num, tag) in reading order
    first_index_of = {num: idx for idx, (num, _) in enumerate(table_order)}
    tag_by_index = [tag for (_n, tag) in table_order]
    mapped = {}
    last_tag = None
    for i, p in enumerate(position_numbers):
        n = int(p["num"])
        if n in first_index_of:
            tag = table_order[first_index_of[n]][1]
            last_tag = tag
        else:
            tag = (
                last_tag
                if last_tag is not None
                else (table_order[0][1] if table_order else "")
            )
        mapped[p["num"]] = tag
    return mapped


def render_images_for_mapping(orig_path, ocr_text, mapping, output_prefix):
    # Render using first page of orig_path
    pdf_doc = pdfium.PdfDocument(orig_path)
    page_img = pdf_doc[0].render(scale=SCALE).to_pil()
    img_out = Image.new("RGBA", page_img.size)
    img_out.paste(page_img, (0, 0))
    draw = ImageDraw.Draw(img_out)

    # For each position, annotate
    # We will reuse the positions from origin, but this function is a helper inside process loop
    return img_out


def process_pair(pos_page, table_page):
    orig_file = f"氨合成_page{pos_page}.pdf"
    if not os.path.exists(orig_file):
        return 0

    # Step 1: extract position numbers
    position_numbers = extract_position_numbers(orig_file)
    if not position_numbers:
        return 0

    # Step 2: get OCR table on table_page
    ocr_text = None
    with pdfplumber.open(OCR_FILE) as pdf:
        if table_page - 1 < len(pdf.pages):
            ocr_text = pdf.pages[table_page - 1].extract_text()
    if not ocr_text:
        return 0
    table_order = flatten_table_order_from_text(ocr_text)
    # Step 3: map by rule
    tag_map = map_positions_to_tags(position_numbers, table_order)

    # Step 4: render
    pdf_doc = pdfium.PdfDocument(orig_file)
    base = pdf_doc[0].render(scale=SCALE).to_pil()
    font = FONT
    count = 0
    for p in position_numbers:
        num = p["num"]
        tag = tag_map.get(num, "")
        img = base.copy()
        draw = ImageDraw.Draw(img)
        x = p["x"] * SCALE
        y = p["y"] * SCALE
        r = 38
        draw.ellipse([x - r, y - r, x + r, y + r], outline="red", width=4)
        draw.text((x - 10, y - 55), num, fill="red", font=font)
        draw.text((x + 48, y - 15), tag, fill="red", font=font)
        out_name = f"氨合成_21216-040500-IN40_p{pos_page}_{num}_{tag}.png"
        img.save(os.path.join(OUTPUT_ROOT, out_name), "PNG")
        count += 1
    return count


def main():
    # Page pairs: (pos_page, table_page)
    pairs = [
        (1, 2),  # composite first two pages
        (3, 3),
        (4, 4),
        (5, 5),
        (6, 6),
        (7, 7),
    ]
    total = 0
    for pos_page, table_page in pairs:
        total += process_pair(pos_page, table_page)
        print(f"  -> Completed Page {pos_page}, total so far: {total}")
    print(f"\nTotal images generated: {total}")


if __name__ == "__main__":
    main()
