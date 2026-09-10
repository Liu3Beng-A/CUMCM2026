import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pdfminer.high_level import extract_text
import os

pdf_path = r'D:\CUMCM2026Problems\E题.pdf'
text = extract_text(pdf_path)
print(text)
