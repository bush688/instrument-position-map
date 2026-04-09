import os
import pdfplumber
import re
from PIL import Image, ImageDraw, ImageFont
import pypdfium2 as pdfium

os.chdir(r"E:\opencode\位置图处理\仪表位置图OCR")

OUTPUT_ROOT = r"E:\opencode\位置图处理\output\变换_21216-040100-IN40"
os.makedirs(OUTPUT_ROOT, exist_ok=True)

# Find OCR file
OCR_FILE = None
for f in os.listdir("."):
    if "040100" in f and "_OCR" in f:
        OCR_FILE = f
        break

print(f"OCR file: {OCR_FILE}")

try:
    FONT = ImageFont.truetype("simsun.ttc", 32)
except:
    FONT = ImageFont.load_default()

SCALE = 3.0


def flatten_table_order(text):
    order = []
    for line in (text or "").splitlines():
        for num_str, tag in re.findall(r"(\d+)\s+(04[A-Z]{1,3}[-\d]+[A-Z]?)", line):
            try:
                n = int(num_str)
            except:
                continue
            order.append((n, tag))
    return order


def extract_position_numbers(orig_path, page_idx):
    with pdfplumber.open(orig_path) as pdf:
        if page_idx >= len(pdf.pages):
            return []
        page = pdf.pages[page_idx]
        words = page.extract_words()

    nums = []
    for w in words:
        text = w["text"].strip()
        if text.isdigit() and len(text) <= 3:
            x, y = w["x0"], w["top"]
            # 调整区域以匹配实际位置图
            if 100 < x < 900 and 100 < y < 1300:
                try:
                    n = int(text)
                    if 1 <= n <= 500:
                        nums.append({"num": text, "x": x, "y": y})
                except:
                    pass

    # 去重并排序
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
    first_index_of = {num: idx for idx, (num, _) in enumerate(table_order)}
    mapped = {}
    last_tag = None
    for p in position_numbers:
        n = int(p["num"])
        if n in first_index_of:
            tag = table_order[first_index_of[n]][1]
            last_tag = tag
        else:
            tag = last_tag if last_tag else (table_order[0][1] if table_order else "")
        mapped[p["num"]] = tag
    return mapped


def process_pair(pos_page_idx, table_page_idx, all_pages_ocr):
    # 对应原始文件
    orig_file = "变换_21216-040100-IN40 仪表位置图.pdf"

    # Step 1: 提取位置图序号
    position_numbers = extract_position_numbers(orig_file, pos_page_idx)
    if not position_numbers:
        print(f"  No positions found on page {pos_page_idx + 1}")
        return 0

    # Step 2: 获取OCR表格
    if table_page_idx >= len(all_pages_ocr):
        print(f"  No OCR page {table_page_idx + 1}")
        return 0

    table_text = all_pages_ocr[table_page_idx]
    table_order = flatten_table_order(table_text)

    if not table_order:
        print(f"  No table data on page {table_page_idx + 1}")
        return 0

    print(f"  Positions: {len(position_numbers)}, Table items: {len(table_order)}")

    # Step 3: 映射
    tag_map = map_positions_to_tags(position_numbers, table_order)

    # Step 4: 渲染
    pdf_doc = pdfium.PdfDocument(orig_file)
    if pos_page_idx >= len(pdf_doc):
        return 0

    base = pdf_doc[pos_page_idx].render(scale=SCALE).to_pil()
    width, height = base.size
    count = 0

    for p in position_numbers:
        num = p["num"]
        tag = tag_map.get(num, "")
        if not tag:
            continue

        img = base.copy()
        draw = ImageDraw.Draw(img)
        x = p["x"] * SCALE
        y = p["y"] * SCALE
        r = 38
        draw.ellipse([x - r, y - r, x + r, y + r], outline="red", width=4)
        draw.text((x - 10, y - 55), num, fill="red", font=FONT)
        draw.text((x + 48, y - 15), tag, fill="red", font=FONT)

        # 表格区域
        idx = count
        table_y = height * 0.6 + idx * 35 * SCALE
        if table_y < height - 50:
            draw.rectangle([30, table_y - 8, 350, table_y + 28], outline="red", width=2)

        out_name = f"变换_21216-040100-IN40_page{pos_page_idx + 1}_{num}_{tag}.png"
        img.save(os.path.join(OUTPUT_ROOT, out_name), "PNG")
        count += 1

    return count


def main():
    # 读取所有OCR页面
    all_pages_ocr = []
    with pdfplumber.open(OCR_FILE) as pdf:
        for page in pdf.pages:
            all_pages_ocr.append(page.extract_text())

    print(f"Total OCR pages: {len(all_pages_ocr)}")

    # 根据实际结构定义页面配对
    # 变换图纸有8页，结构分析:
    # Pages 1-4: 位置图+对照表
    # Page 5: 只有图例(符号说明)
    # Pages 6-8: 位置图+对照表

    pairs = [
        (0, 0),  # Page1: 位置图+表
        (1, 1),  # Page2
        (2, 2),  # Page3
        (3, 3),  # Page4
        # (4, 4) is legend only, skip
        (5, 5),  # Page6
        (6, 6),  # Page7
        (7, 7),  # Page8
    ]

    total = 0
    for pos_idx, table_idx in pairs:
        print(f"Processing pair: pos_page={pos_idx + 1}, table_page={table_idx + 1}")
        cnt = process_pair(pos_idx, table_idx, all_pages_ocr)
        total += cnt
        print(f"  Generated {cnt} images, total: {total}")

    print(f"\nTotal: {total} images")


if __name__ == "__main__":
    main()
