'''
tools/search_reference_tool.py
信息抽取
'''
import re

def extract_references(text: str):

    # 1️⃣ 找到“参考文献”位置
    ref_start = text.find("参考文献")

    if ref_start == -1:
        print("⚠️ 没找到参考文献部分")
        return []

    ref_text = text[ref_start:]

    # 2️⃣ 按行切分
    lines = ref_text.split("\n")

    refs = []
    current_ref = ""

    for line in lines:
        line = line.strip()

        # 3️⃣ 匹配 [1] 开头
        if re.match(r"^\[\d+\]", line):
            if current_ref:
                refs.append(current_ref.strip())

            current_ref = line
        else:
            # 4️⃣ 处理换行拼接（关键！）
            current_ref += " " + line

    if current_ref:
        refs.append(current_ref.strip())

    # 5️⃣ 结构化输出
    result = []
    for ref in refs:
        match = re.match(r"\[(\d+)\]\s*(.*)", ref)
        if match:
            result.append({
                "id": match.group(1),
                "text": match.group(2)
            })

    return result