from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

import os

BASE_MODEL_DIR = "/mnt/d/ai_models"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
CACHE_DIR = os.path.join(BASE_MODEL_DIR, "hf_cache")

_vectorstore = None


def load_vectorstore():
    global _vectorstore

    if _vectorstore is None:
        embedding_model = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL_NAME,
            cache_folder=CACHE_DIR
        )

        # 从本地加载（build_index保存）
        _vectorstore = FAISS.load_local(
            "rag/index",
            embedding_model,
            allow_dangerous_deserialization=True
        )

    return _vectorstore


def get_retriever():
    vectorstore = load_vectorstore()

    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 3}
    )