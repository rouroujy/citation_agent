'''
tools/rag_search_tool.py
RAG接口
'''

# from rag.retriever import get_retriever

# retriver = get_retriever()

# def rag_search(query: str):
#     docs = retriver(query)
#     return "\n".join(
#         [
#             doc.page_content for doc in docs
#         ]
#     )


def rag_search(query: str):

    knowledge_base = [
        "Two-stream CNN 用于视频动作识别",
        "LSTM 可以建模时间序列信息",
        "红外传感器可以用于人体动作识别",
        "深度学习方法优于传统方法",
    ]

    results = []

    for doc in knowledge_base:
        if any(word in doc for word in query.split()):
            results.append(doc)

    # ✅ 直接返回字符串拼接
    return "\n".join(results)