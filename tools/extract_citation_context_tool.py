'''
tools/extract_citation_context_tool.py
'''

import re

def extract_citation_context(text: str, ref_id: str, window: int = 200):
    """
    根据引用编号（如 "1"）找到正文中的 [1] 并截取上下文
    """

    pattern = rf"\[{ref_id}\]"

    matches = list(re.finditer(pattern, text))

    if not matches:
        return ""
    

    m = matches[0]  #只取第一个

    start = max(0, m.start() - window)
    end = min(len(text), m.end() + window)

    return text[start:end]

    # 多个引用位置拼接
    # contexts = []

    # for m in matches:
    #     start = max(0, m.start() - window)
    #     end = min(len(text), m.end() + window)

    #     context = text[start:end]
    #     contexts.append(context)

    # # 👉 多个引用位置，拼接（或你也可以只取第一个）
    # return "\n\n".join(contexts)