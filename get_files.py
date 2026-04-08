import os
import glob

os.chdir(r"E:\opencode\位置图处理\仪表位置图OCR")

# 找到所有400200相关的文件
files = glob.glob("*400200*.pdf")
print("Found files:", files)

orig_file = [f for f in files if "_OCR" not in f][0]
ocr_file = [f for f in files if "_OCR" in f][0]

print(f"Original: {orig_file}")
print(f"OCR: {ocr_file}")

# 保存供后续使用
with open("files_400200.txt", "w") as f:
    f.write(f"orig={orig_file}\n")
    f.write(f"ocr={ocr_file}\n")
