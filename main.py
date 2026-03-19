'''
main.py
'''

from agent.agent_graph import build_graph
from tools.parse_pdf_tool import parse_pdf

print("===========开始main===========")

graph = build_graph()

file_path = "data/papers/tests.pdf"

text = parse_pdf(file_path)

state = {
    "text": text
}

result = graph.invoke(state)

print("\n最终结果：")
for item in result["result"]:
    print(item)
    print("-" * 50)