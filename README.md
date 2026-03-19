# Citation Agent: 基于 RAG 的论文引用合理性检测系统

一个用于**自动分析论文引用是否合理**的智能 Agent 系统，结合 **RAG（Retrieval-Augmented Generation）+ 引用类型建模 + LLM审稿推理**，实现对学术论文中引用的自动验证与错误检测。

------

## 项目特点

本项目实现了一个接近“审稿人思维”的引用检测流程：

###  核心能力

- **自动解析 PDF 论文**
- **提取参考文献列表（结构化）**
- **定位引用在正文中的上下文**
- **基于上下文进行 RAG 检索**
- **引用类型自动分类（关键创新）**
- **LLM 审稿式推理判断引用合理性**
- **检测 hallucination / 错误引用 / 张冠李戴**

------

## 系统整体流程

```text
PDF论文
   ↓
解析文本
   ↓
提取参考文献
   ↓
逐条处理引用：
    Step1: 找到引用位置（[1]）
    Step2: 提取上下文（前后window）
    Step3: 分类引用类型（background / related / method）
    Step4: RAG检索相关证据
    Step5: LLM判断引用是否合理
   ↓
输出审稿结果
```

------

##  项目结构

```bash
citation_agent/
│
├── main.py                         # 主入口
│
├── agent/
│   └── agent_graph.py             # LangGraph工作流
│
├── tools/
│   ├── parse_pdf_tool.py          # PDF解析
│   ├── search_reference_tool.py   # 参考文献提取
│   ├── extract_citation_context_tool.py  # 引用上下文提取
│   ├── rag_search_tool.py         # RAG检索
│   └── verify_citation_tool.py    # 引用判别（LLM）
│
├── rag/
│   ├── build_index.py             # 构建向量库
│   └── retriever.py               # 检索器
│
├── data/
│   └── papers/
│       └── tests.pdf              # 测试论文
│
└── rag/index/                    # FAISS索引
```

------

## 环境依赖

```bash
pip install langchain langchain-community langchain-huggingface
pip install faiss-cpu
pip install pypdf
pip install transformers sentence-transformers
```

推荐配置：

- Python 3.10+
- GPU（可选）
- 本地 embedding 模型缓存路径（已支持离线）

------

## 使用方法

### 构建向量库（只需一次）

```bash
python -m rag.build_index
```

------

### 运行引用检测

```bash
python main.py
```

------

###  输出示例

```json
{
  "ref": "...",
  "citation_context": "...",
  "type": "background",
  "verdict": "valid",
  "reason": "...",
  "confidence": 0.95
}
```

------

## 引用类型建模（核心创新）

系统自动将引用分为三类：

| 类型         | 含义          | 判定标准     |
| ------------ | ------------- | ------------ |
| background   | 背景引用      | 只需领域相关 |
| related_work | 相关工作      | 同类任务即可 |
| method       | 方法/证据引用 | 必须严格支持 |

不同类型使用**不同判别策略（prompt）**

------

## RAG 检索策略

本项目采用：

- Embedding：`all-MiniLM-L6-v2`
- 向量库：FAISS
- 检索方式：MMR（多样性优化）

```python
search_type="mmr"
k=3
```

------

## LLM 判别策略

根据 citation 类型动态构造 prompt：

### 背景引用（宽松）

- 是否属于同一研究领域

### 相关工作（中等）

- 是否同类任务

### 方法引用（严格）

- 是否真实支持
- 是否存在 hallucination

------

## 已支持错误检测类型

系统可以识别：

- 虚假引用（hallucination）
- 张冠李戴（wrong reference）
- 方法不匹配（method mismatch）
- 引用错位（context mismatch）
- 弱支持（weak support）

------

## 当前能力评估

该系统已具备：

- Context-aware Citation Verification
- Type-aware Citation Reasoning
- RAG Grounded Evidence Checking

------

## 如果你觉得有帮助

欢迎 ⭐ Star & Fork！

