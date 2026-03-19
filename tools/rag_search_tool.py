'''
tools/rag_search_tool.py
RAG接口
'''
from rag.retriever import get_retriever

retriever = get_retriever()

def rag_search(query: str):

    docs = retriever.invoke(query)

    # 拼接上下文
    context = "\n\n".join(
        [doc.page_content for doc in docs]
    )

    print("\n🔍 RAG检索结果：")
    print(context[:500])

    return context

