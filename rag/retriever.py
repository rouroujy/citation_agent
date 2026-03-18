def get_retriever():

    knowledge_base = [
        "Deep learning is widely used in computer vision.",
        "Transformers are powerful models for NLP tasks.",
        "CNN is effective for image classification.",
        "RNN is used for sequence modeling."
    ]

    def retrieve(query: str):
        # 简化：直接返回全部
        return knowledge_base

    return retrieve