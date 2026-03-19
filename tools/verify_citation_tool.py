'''
tools/verify_tool.py
判别任务
'''

import json
from llm.dashscope_llm import call_llm


def verify_citation(reference, context, citation_type="method"):

    # ========================
    # ✅ 根据类型构造不同prompt
    # ========================

    base_prompt = f"""
你是一个严谨的论文审稿人。

【引用文献】
{reference}

【检索证据】
{context}
"""

    # 🟢 背景引用（宽松）
    if citation_type == "background":
        prompt = base_prompt + """
该引用属于【背景引用】：
- 只需判断是否属于同一研究领域
- 不要求严格实验或数据支撑

请输出JSON：
{
  "verdict": "valid 或 invalid",
  "reason": "...",
  "confidence": 0-1
}
"""

    # 🟡 相关工作（中等）
    elif citation_type == "related_work":
        prompt = base_prompt + """
该引用属于【相关工作引用】：
- 只需判断是否属于同类任务或问题
- 不要求方法完全一致

请输出JSON：
{
  "verdict": "valid 或 invalid",
  "reason": "...",
  "confidence": 0-1
}
"""

    # 🔴 方法引用（严格）
    else:
        prompt = base_prompt + """
该引用属于【方法/证据引用】：
- 必须判断是否真正支持该论述
- 是否存在 hallucination（虚假引用）

请输出JSON：
{
  "verdict": "valid 或 invalid",
  "reason": "...",
  "evidence": "...",
  "confidence": 0-1
}
"""

    # ========================
    # 调用LLM
    # ========================
    response = call_llm(prompt)

    try:
        return json.loads(response)
    except:
        print("⚠️ JSON解析失败，原始输出：", response)
        return {
            "verdict": "error",
            "reason": response,
            "evidence": "",
            "confidence": 0
        }