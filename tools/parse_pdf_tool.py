'''
tools/parse_pdf_tool.py
PDF解析
'''
from pypdf import PdfReader

def parse_pdf(file_path:str):
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        text += page.extract_text() + "\n"

    return text