'''
rag/build_index.py

'''


from tools.parse_pdf_tool import parse_pdf
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

import os

def chunk_text(text, chunk_size=300, overlap=50):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap

    return chunks


def build():

    print("读取PDF...")
    text = parse_pdf("data/papers/tests.pdf")
    # 关键：截断参考文献
    ref_start = text.find("参考文献")
    if ref_start != -1:
        text = text[:ref_start]

    print("切分文本...")
    # chunks = chunk_text(text)
    chunks = []

    for i, chunk in enumerate(chunk_text(text)):
        chunks.append(f"[chunk_id={i}]\n{chunk}")

    docs = [Document(page_content=c) for c in chunks]

    print("加载embedding模型...")
    embedding = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

    print("构建向量库...")
    vectorstore = FAISS.from_documents(docs, embedding)

    os.makedirs("rag/index", exist_ok=True)

    print("保存索引...")
    vectorstore.save_local("rag/index")

    print("index构建完成！")


if __name__ == "__main__":
    build()