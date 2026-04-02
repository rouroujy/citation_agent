# Citation Agent：RAG 与 LangChain / LangGraph 学习笔记

本文档基于仓库源码，按**逻辑顺序**拆解 RAG 流水线，并单独说明 **LangChain**、**LangGraph** 在本项目中的实际用法（与官方完整能力对比）。

---

## 一、RAG 在业务中的位置（端到端）

引用验证主链路在 `agent/agent_graph.py` 的 `verify_node` 中：

1. 用**正文引用上下文**（`extract_citation_context`）作为 **RAG 的 query**；
2. `rag_search(citation_context)` 从向量库取回若干文本块，拼成 **【检索证据】**；
3. `verify_citation` 把 **【引用文献】+【检索证据】+ 引用类型** 交给 LLM 做判别。

因此：本项目的 RAG **不是**“整篇论文问一句”，而是**每条参考文献、用其引用点附近的上下文去检索证据**。

---

## 二、RAG 模块拆解（按数据流）

### 1. 文档从哪里来：如何“读文档”

| 环节 | 文件 | 做法 |
|------|------|------|
| **建索引时读 PDF** | `rag/build_index.py` | 调用 `tools.parse_pdf_tool.parse_pdf("data/papers/tests.pdf")`，路径写死在 `build()` 里。 |
| **PDF 如何变成字符串** | `tools/parse_pdf_tool.py` | 使用 `pypdf.PdfReader`，逐页 `extract_text()` 拼接，页间加换行。 |

要点：

- **没有**使用 LangChain 的 `PyPDFLoader`、`DirectoryLoader` 等；读文档与 RAG 索引构建是**手工调用** `parse_pdf`。
- 提取的是**纯文本**，不保留页码、表格结构等（`pypdf` 的局限即本项目的局限）。

### 2. 建索引前的文本清洗

| 文件 | 逻辑 |
|------|------|
| `rag/build_index.py` | 在全文里查找 `"参考文献"`，若找到则 **`text = text[:ref_start]`**，即**丢弃参考文献段落及之后内容**。 |

目的：避免把参考文献列表本身切块进向量库，减少噪声；**前提**是论文用中文“参考文献”作为小节标题。

### 3. “语义单元”如何切分：是否语义切分？

**结论：没有使用基于语义/嵌入的切分；使用的是固定字符窗口 + 重叠的滑窗切分。**

| 文件 | 函数 | 行为 |
|------|------|------|
| `rag/build_index.py` | `chunk_text(text, chunk_size=300, overlap=50)` | 从 `start=0` 开始，每次取 `[start, start+300)` 字符；`start` 每次前进 `300-50=250`，直到覆盖全文。 |

- **不是** `RecursiveCharacterTextSplitter`、**不是**按段落/标题结构切分，**也不是** LangChain 的语义切分（semantic chunking）。
- 每个 chunk 前会拼一行前缀：`[chunk_id={i}]\n`，便于人工/debug 时区分块，**不参与**向量化时的特殊处理（仍整块进 `Document`）。

### 4. 向量化与向量库

| 文件 | 内容 |
|------|------|
| `rag/build_index.py` | `Document(page_content=chunk)` → `HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")` → `FAISS.from_documents(docs, embedding)` → `save_local("rag/index")`。 |
| `rag/retriever.py` | `FAISS.load_local("rag/index", embedding_model, allow_dangerous_deserialization=True)`。 |

- **Embedding 模型**：`sentence-transformers` 生态下的 `all-MiniLM-L6-v2`（通过 `langchain_huggingface.HuggingFaceEmbeddings` 封装）。
- **建索引**与**在线加载**时，embedding 配置**不完全一致**：建索引未指定 `cache_folder`，加载时在 `retriever` 里指定了 `cache_folder`（见 `BASE_MODEL_DIR`），部署时需注意路径一致性与缓存。

### 5. 检索阶段：是否 Top-K？是否 Rerank？

**Top-K（最终返回文档条数）：有。**

在 `rag/retriever.py`：

```python
return vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 3}
)
```

- **`k=3`**：每次检索最终返回 **3 条** `Document`（在 `tools/rag_search_tool.py` 里再拼成一段字符串）。

**是否 Rerank：没有独立的 Rerank 模块。**

- 代码中**没有** Cross-Encoder、Cohere Rerank、`langchain` 的 `EnsembleRetriever` 二次排序等。
- **MMR（Maximal Marginal Relevance）** 本身是在“相似度 vs 多样性”之间做**内置选择**，可理解为向量检索后的**多样性筛选**，但**不是**业界常说的“两阶段检索 + 精排 Rerank 模型”。

**MMR 在 LangChain 中的典型含义（与本项目相关）：**

- `search_type="mmr"` 时，LangChain 会先从向量库取出 **`fetch_k` 条**候选（若未在 `search_kwargs` 中指定，通常有**库内默认值**，例如常见默认 `fetch_k=20`），再在候选上用 MMR 选出 **`k` 条**。
- 本项目**只显式传了 `k=3`**，未传 `fetch_k`、`lambda_mult`，因此后两者走 **LangChain/FAISS 集成层的默认值**（若需可控，应在 `search_kwargs` 里写明）。

### 6. 查询（Query）是什么

| 文件 | 行为 |
|------|------|
| `tools/rag_search_tool.py` | `retriever.invoke(query)`，`query` 来自 `agent/agent_graph.py` 的 **`citation_context`**（引用符号 `[n]` 附近窗口文本），不是用户自然语言问题。 |

### 7. 检索结果如何进入 LLM

| 文件 | 行为 |
|------|------|
| `tools/rag_search_tool.py` | 将 3 个 `doc.page_content` 用 `"\n\n"` 拼接成一个大字符串返回。 |
| `tools/verify_citation_tool.py` | 该字符串作为 prompt 中的 **【检索证据】**，与 **【引用文献】** 一起交给 `call_llm`。 |

**没有**使用 LangChain 的 `create_retrieval_chain`、`StuffDocumentsChain` 等；RAG 的“组装 prompt”在自写 Python 里完成。

---

## 三、RAG 小结表（对照常见问题）

| 问题 | 本项目实际情况 |
|------|----------------|
| 文档读取 | `pypdf` 手工读 PDF，非 LangChain Loader |
| 切分方式 | **字符滑窗** 300 / overlap 50，**非**语义切块 |
| 向量库 | FAISS，持久化目录 `rag/index` |
| Embedding | `all-MiniLM-L6-v2`（HuggingFaceEmbeddings） |
| Top-K | **有**，`k=3` |
| MMR | **有**，`search_type="mmr"` |
| Rerank（精排） | **无** |
| 查询构造 | 引用上下文字符串（非独立 QA 问题） |

---

## 四、LangChain 在本项目中的使用拆解

下面只列出**实际被 import/调用**的部分，避免与 LangChain 全家桶混淆。

### 1. `langchain_core`

| 符号 | 用途 |
|------|------|
| `Document` | 建索引时把每个文本块包装成 `Document(page_content=...)`，再交给 FAISS。 |

### 2. `langchain_huggingface`

| 符号 | 用途 |
|------|------|
| `HuggingFaceEmbeddings` | 统一封装本地/缓存的句向量模型，供 `FAISS.from_documents` 与 `FAISS.load_local` 使用。 |

### 3. `langchain_community`

| 符号 | 用途 |
|------|------|
| `FAISS` | 向量存储：建索引、保存、加载、`as_retriever()`。 |

### 4. 未在本项目中使用的 LangChain 典型能力（便于学习对照）

- **Chains / LCEL**：无 `Runnable`、`prompt | llm | output_parser` 管道。
- **Text splitters**：无 `RecursiveCharacterTextSplitter` 等，切块自写 `chunk_text`。
- **Retrieval 封装**：无 `create_retrieval_chain`、`ConversationalRetrievalChain`。
- **Rerankers**：无。

**结论**：LangChain 在这里主要扮演 **Embedding + VectorStore + Retriever（MMR）** 的胶水层，**业务编排在外部 Python（Graph 节点与 tools）里**。

---

## 五、LangGraph 在本项目中的使用拆解

### 1. 实际用到的 API

| API | 位置 | 作用 |
|-----|------|------|
| `StateGraph(dict)` | `agent/agent_graph.py` | 状态类型为普通 `dict`，无 TypedDict schema。 |
| `add_node(name, fn)` | 同上 | 注册 `parse`、`verify` 两个节点函数。 |
| `set_entry_point("parse")` | 同上 | 入口节点。 |
| `add_edge("parse", "verify")` | 同上 | 单向边：parse → verify。 |
| `compile()` | 同上 | 得到可 `invoke` 的可运行图。 |

### 2. 状态如何在节点间传递

- `parse_node` 返回：`{"text", "references"}`（与 state 合并）。
- `verify_node` 读取：`state["text"]`、`state["references"]`，写出：`{"text", "references", "result"}`。

### 3. 未使用的 LangGraph 能力

- **条件边**（`add_conditional_edges`）：无分支。
- **Checkpoint / 持久化 / 人机中断**：无。
- **预置 ReAct Agent / ToolNode**：无；工具是**普通函数**，在节点里直接调用，不是 Graph 的 tool-calling 循环。

**结论**：LangGraph 在本项目中等价于**两步骤流水线**（parse → verify），价值是**结构清晰、后续可扩展分支/循环**；当前**没有**用到 LangGraph 的高级编排特性。

---

## 六、与 LLM 的关系（非 LangChain）

| 文件 | 作用 |
|------|------|
| `llm/dashscope_llm.py` | 直接 `dashscope.Generation.call`，模型 `qwen-plus`，**不经过** LangChain 的 `ChatModel` 封装。 |
| `tools/verify_citation_tool.py` | 拼 prompt、解析 JSON，**自管** RAG 输出与引用条目的结合。 |

---

## 七、延伸阅读（若要增强本项目 RAG）

以下为**仓库外**的常见改进方向，与当前代码无直接对应：

1. **切分**：`RecursiveCharacterTextSplitter` 或按章节标题切分；长论文可考虑语义切块。
2. **检索**：显式设置 `fetch_k`、`lambda_mult`；或 hybrid（BM25 + 向量）。
3. **Rerank**：Cross-Encoder 或对 top 候选再排序。
4. **索引源**：多 PDF、增量更新、元数据（文件名、页码）写入 `Document.metadata`。
5. **LangChain 化**：用 LCEL 把 retriever + prompt + LLM 串成可观测、可替换的 Runnable（可选）。

---

## 八、源码索引（便于对照阅读）

| 主题 | 路径 |
|------|------|
| PDF 读取 | `tools/parse_pdf_tool.py` |
| 切块与建索引 | `rag/build_index.py` |
| 加载索引与 Retriever | `rag/retriever.py` |
| RAG 调用封装 | `tools/rag_search_tool.py` |
| 工作流编排 | `agent/agent_graph.py` |
| LLM 判别 | `tools/verify_citation_tool.py`、`llm/dashscope_llm.py` |

---

*文档生成依据：仓库内 Python 源码；LangChain MMR 的 `fetch_k` / `lambda_mult` 默认行为以你本地安装的 `langchain_community` / `langchain_core` 版本为准，若升级依赖请以官方文档与源码为准。*

## 九、LangChain 补充：本项目没用到但常见的能力

下面按“RAG 通常怎么搭”来讲本项目没覆盖的点，便于你后续做增强时直接套用。

### 1. 文档加载（Document Loader）

本项目用的是 `tools/parse_pdf_tool.py` 手写 `pypdf` 解析，并没有走 LangChain Loader。

常见替代/增强：

- `PyPDFLoader`：LangChain 官方风格的 PDF loader，通常会产生 `Document` 列表（带页码 metadata）。
- `DirectoryLoader`：批量加载文件夹下的文档。
- 不同 loader 适配不同格式：PDF/HTML/Markdown/Word 等。

为什么有价值：有了 `Document.metadata`（比如 `page`、`source`），后续你可以做“证据定位更精确”和“过滤召回候选”。

### 2. 文本切分（Text Splitters）

本项目切分是自写字符滑窗（`chunk_size=300`, `overlap=50`），没有使用 LangChain splitter。

常见切分器思路：

- `RecursiveCharacterTextSplitter`：优先按较自然的边界切（段落/句子/换行），再退回字符级。
- `TokenTextSplitter`：按 token 数量控制 chunk，避免 embedding 成本失控。
- `MarkdownHeaderTextSplitter`：按 Markdown 标题层级切分（适合论文的结构化文本）。

为什么有价值：当前滑窗可能把“方法描述/公式附近的关键句”切碎，影响 embedding 与检索证据质量。

### 3. 检索链路封装（Chains / LCEL）

本项目没有用到 LangChain 的 Retrieval Chain，而是直接在 `tools/` 中拼 prompt。

常见写法（概念）：

- 把 `retriever` 与 `prompt` 与 `llm` 用 LCEL（`Runnable`）串起来。
- 用 `OutputParser` 把模型输出解析成结构化 JSON/Pydantic。

典型收益：

- 更易替换组件（换模型/换 retriever/换 prompt）
- 更容易做可观测性与单元测试（每步输入输出都更清晰）

### 4. 输出解析（Output Parsers）

本项目在 `verify_citation_tool` 里是 `json.loads(response)`，失败就返回 `verdict="error"`。

LangChain 的常见增强：

- `JsonOutputParser`：约束模型必须输出合法 JSON。
- `PydanticOutputParser`：让输出严格符合 Pydantic schema（字段类型/必填更稳）。

为什么有价值：减少 LLM 输出格式漂移导致的 JSON 解析失败。

### 5. 二阶段检索：Rerank / Compression

本项目只用 `search_type="mmr"` 做多样性选择，但没有“二次精排”。

常见两阶段增强：

- 先向量召回 top-n
- 再用 Cross-Encoder reranker（或其他重排器）对候选重打分
- 只保留重排后的 top-k

在 LangChain 里常见是“压缩检索”思路：`ContextualCompressionRetriever`（概念上）或组合 reranker。

为什么有价值：对于“证据支持/方法匹配”这种判别任务，单纯 embedding 相似度常不足以区分细粒度支持程度。

### 6. Hybrid 检索（向量 + 关键词）

本项目是纯向量 FAISS。

常见增强：

- BM25（关键词）检索 + 向量检索融合（例如 `EnsembleRetriever`）
- 这样可以对短查询/专有名词更稳（比如引用中的术语、缩写、方法名）。

### 7. 更细粒度的元数据过滤

本项目 `Document.page_content` 是唯一内容，没有使用 metadata 做过滤。

增强方式：

- 在建索引阶段写入 metadata（例如 `chunk_id`、`source_doc`、`page`、`section`）
- 在检索时根据 metadata 做 filter（例如只在“方法相关区域”检索）

## 十、LangGraph 补充：本项目没用到的常见编排能力

本项目 `StateGraph` 只做了线性两步 `parse -> verify`，没有用到 LangGraph 的强大编排特性。下面是典型能力点。

### 1. 条件边与循环（把“每个引用逐条处理”做成图逻辑）

当前是：`verify_node` 内部用 Python `for ref in references` 循环。

LangGraph 里你可以改成：

- 用条件边决定下一步处理哪个引用（或何时停止）
- 用循环结构让图更“可视化、可控”

适合你要做：

- 限制最大引用数
- 根据中间结果决定是否需要更深检索

### 2. Typed State / Schema 化状态

当前使用的是 `StateGraph(dict)`，状态没有 schema 约束。

LangGraph 常见做法：

- 使用 `TypedDict` 或 dataclass 定义 state 结构
- 让每个节点输入输出更严格，减少键名拼写错误与缺失字段风险

### 3. Checkpoint / 持久化与可恢复

本项目没有 checkpoint。

LangGraph 常见能力：

- 保存每一步执行的状态
- 允许失败后从中断点恢复

适合长任务：

- 论文引用很多、每条都要多次检索/推理

### 4. ToolNode / 与工具系统集成的图式调用（如果你要做 tool-calling）

本项目的工具是普通函数直接在节点里调用。

LangGraph 的预置能力（概念）：

- 把工具调用当作图节点
- 便于统一管理工具输入输出、观测与错误处理

### 5. 人机中断（Human-in-the-loop）与审批流

当你希望：

- 对低置信度结果进行人工复核
- 或在某些步骤需要用户确认后再继续

LangGraph 可以用“中断/恢复”的方式把人工流程嵌入图。

### 6. 流式执行与并行分支（提高吞吐）

当前是同步顺序执行。

LangGraph 可用于：

- 并行处理不同引用（如果你希望加速）
- 或并行做多路检索/多种证据策略

这些能力和你本项目“逐条引用验证”天然契合。

