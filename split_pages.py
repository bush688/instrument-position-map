import os
import pypdf

os.chdir(r"E:\opencode\位置图处理\仪表位置图OCR")

files = [f for f in os.listdir(".") if "040500" in f]
orig_file = [f for f in files if not f.endswith("_OCR.pdf")][0]

reader = pypdf.PdfReader(orig_file)
print(f"Splitting into {len(reader.pages)} pages")

for page_idx in range(len(reader.pages)):
    writer = pypdf.PdfWriter()
    writer.add_page(reader.pages[page_idx])

    output_name = f"氨合成_page{page_idx + 1}.pdf"
    with open(output_name, "wb") as f:
        writer.write(f)
    print(f"Created: {output_name}")
