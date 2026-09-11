"""用 pymupdf 读取 E 题 PDF，输出带页码"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import fitz

pdf_path = r'D:\CUMCM2026Problems\E题.pdf'
doc = fitz.open(pdf_path)
print(f'页数: {len(doc)}')
for i in range(min(2, len(doc))):
    print(f'\n========== 第 {i+1} 页 ==========')
    print(doc[i].get_text())
doc.close()
