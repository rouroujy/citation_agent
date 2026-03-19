'''
agent/graph.py
'''

from langgraph.graph import StateGraph
from tools.search_reference_tool import extract_references
from tools.rag_search_tool import rag_search
from tools.verify_citation_tool import verify_citation
from tools.extract_citation_context_tool import extract_citation_context


# ✅ 新增：citation类型分类函数
def classify_citation(context: str) -> str:
    context = context.lower()

    # 🟢 背景引用
    if any(k in context for k in [
        "近年来", "随着", "目前", "已经成为",
        "人口老龄化", "问题", "风险", "挑战"
    ]):
        return "background"

    # 🟡 相关工作
    if any(k in context for k in [
        "已有研究", "相关研究", "已有方法",
        "研究表明", "文献", "已有工作"
    ]):
        return "related_work"

    # 🔴 默认：方法引用
    return "method"


def build_graph():

    print("========开始build graph========")

    def parse_node(state):
        text = state["text"]
        refs = extract_references(text)

        return {
            "text": text,
            "references": refs
        }


    def verify_node(state):
        results = []

        full_text = state["text"]

        for ref in state["references"]:

            # ========================
            # Step1：找到引用上下文
            # ========================
            citation_context = extract_citation_context(
                full_text,
                ref["id"]
            )

            print("\n📌 引用上下文：")
            print(citation_context[:300])

            # ========================
            # ✅ Step1.5：分类 citation 类型（新增🔥）
            # ========================
            citation_type = classify_citation(citation_context)
            print("📊 citation类型：", citation_type)

            # ========================
            # Step2：RAG检索
            # ========================
            rag_context = rag_search(citation_context)

            # ========================
            # Step3：判别（传入类型🔥）
            # ========================
            result = verify_citation(
                ref["text"],
                rag_context,
                citation_type   # ✅ 新增参数
            )

            results.append({
                "ref": ref["text"],
                "citation_context": citation_context[:200],
                "type": citation_type,   # ✅ 保存类型
                **result
            })

        return {
            "text": full_text,
            "references": state["references"],
            "result": results
        }


    graph = StateGraph(dict)

    graph.add_node("parse", parse_node)
    graph.add_node("verify", verify_node)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "verify")

    return graph.compile()