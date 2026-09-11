"""先把PDF转图片，再OCR"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os

import fitz
pdf_path = r'D:\CUMCM2026Problems\E题.pdf'
doc = fitz.open(pdf_path)
print(f'pdf pages: {len(doc)}', flush=True)
out_dir = r'D:\CUMCM2026Problems\e_images'
os.makedirs(out_dir, exist_ok=True)

for i in range(len(doc)):
    page = doc[i]
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
    out = os.path.join(out_dir, f'page_{i+1}.png')
    pix.save(out)
    print(f'  page {i+1}: {out} ({pix.width}x{pix.height})', flush=True)

doc.close()
