'''
tools/verify_tool.py
判别任务
'''

from llm.dashscope_llm import call_llm

def verify_citation(reference, context):
    print("\n=====================")
    print("\n开始判别引用是否合理\n")
    prompt = f"""
请判断以下引用是否合理：

引用：
{reference}

上下文：
{context}

请输出：
valid / invalid +i理由

"""
    
    return call_llm(prompt)


