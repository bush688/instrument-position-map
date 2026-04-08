import os
import random

output_dir = r"E:\opencode\位置图处理\output\氨合成_21216-040500-IN40"
files = [f for f in os.listdir(output_dir) if f.endswith(".png")]
print(f"Total: {len(files)}")

# Count pages
page_counts = {}
for f in files:
    if "page1" in f:
        page_counts["page1"] = page_counts.get("page1", 0) + 1
    elif "page2" in f:
        page_counts["page2"] = page_counts.get("page2", 0) + 1
    elif "page3" in f:
        page_counts["page3"] = page_counts.get("page3", 0) + 1
    elif "page4" in f:
        page_counts["page4"] = page_counts.get("page4", 0) + 1
    elif "page5" in f:
        page_counts["page5"] = page_counts.get("page5", 0) + 1
    elif "page6" in f:
        page_counts["page6"] = page_counts.get("page6", 0) + 1
    elif "page7" in f:
        page_counts["page7"] = page_counts.get("page7", 0) + 1

for k, v in sorted(page_counts.items()):
    print(f"  {k}: {v}")

print("\nSamples:")
for f in random.sample(files, 5):
    print(f"  {f}")
