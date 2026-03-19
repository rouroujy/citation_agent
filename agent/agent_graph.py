'''
agent/graph.py
'''

from langgraph.graph import StateGraph
from tools.search_reference_tool import extract_references
from tools.rag_search_tool import rag_search
from tools.verify_citation_tool import verify_citation

from tools.extract_citation_context_tool import extract_citation_context

def build_graph():

    print("========开始build graph========")
    def parse_node(state):
        text = state["text"]
        refs = extract_references(text)
        print("提取到引用:", refs)
        return {"references": refs}
    
    def verify_node(state):
        results = []

        full_text = state["text"]

        for ref in state["references"]:

            # Step1：找到引用上下文
            citation_context = extract_citation_context(
                full_text,
                ref["id"]
            )

            print("\n📌 引用上下文：")
            print(citation_context[:300])

            # Step2：用上下文做RAG
            rag_context = rag_search(citation_context)

            # Step3：再做判别
            result = verify_citation(
                ref["text"],
                rag_context
            )

            results.append({
                "ref": ref["text"],
                "result": result
            })

        return {"result": results}
    
    graph = StateGraph(dict)

    graph.add_node("parse",parse_node)
    graph.add_node("verify",verify_node)

    graph.set_entry_point("parse")
    graph.add_edge("parse","verify")

    return graph.compile()