'''
tools/verify_tool.py
判别任务
'''

from llm.dashscope_llm import call_llm

def verify_citation(reference, context):
    print("\n=====================")
    print("\n开始判别引用是否合理\n")
    prompt = f"""
    你是一个严谨的论文审稿人。

    请判断引用是否被正确支持。

    【引用内容】
    {reference}

    【检索证据】
    {context}

    请输出JSON：
    {{
  "verdict": "valid / invalid",
  "reason": "...",
  "evidence": "...",
  "confidence": 0-1
    }}

    """
    
    return call_llm(prompt)


