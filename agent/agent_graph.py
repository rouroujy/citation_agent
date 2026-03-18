'''
agent/graph.py
'''

from langgraph.graph import StateGraph
from tools.search_reference_tool import extract_references
from tools.rag_search_tool import rag_search
from tools.verify_citation_tool import verify_citation

def build_graph():
    def parse_node(state):
        text = state["text"]
        refs = extract_references(text)
        print("提取到引用:", refs)
        return {"references": refs}
    
    def verify_node(state):
        results = []

        for ref in state["references"]:
            context = rag_search(ref["text"])
            result = verify_citation(ref["text"], context)
            print("调用结果",result)
            results.append(
                {
                    "ref": ref["text"],
                    "result": result
                }
            )

        return {"result": results}
    
    graph = StateGraph(dict)

    graph.add_node("parse",parse_node)
    graph.add_node("verify",verify_node)

    graph.set_entry_point("parse")
    graph.add_edge("parse","verify")

    return graph.compile()