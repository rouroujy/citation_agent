# Citation Agent 架构说明

本文档基于当前仓库代码（`/home/rourou/citation_agent`）整理，目标是说明**模块分层、核心数据流、运行方式、关键配置点与扩展点**。

## 总览

这是一个“论文引用合理性检测”系统，主流程是：

1. **PDF 解析**：从 PDF 提取全文文本
2. **参考文献抽取**：从“参考文献”段落中解析结构化条目（`[id] text`）
3. **逐条引用验证**（对每条参考文献）：
   - 在正文中定位该引用的出现位置 `[{id}]`，截取上下文窗口
   - 基于上下文做 **RAG 检索**（FAISS + MMR）
   - 进行**引用类型分类**（background / related_work / method）
   - 让 LLM 基于“引用文献 + 检索证据 + 类型策略”输出 JSON 判定（valid/invalid + reason + confidence）
4. **输出结果**：每条引用产出一条结构化判定结果

## 目录与模块职责

仓库主要目录如下：

- **入口层**
  - `main.py`：本地 CLI/脚本入口（直接处理 `data/papers/tests.pdf`）
  - `api/server.py`：FastAPI 服务入口（`/verify_paper` 上传 PDF 并返回结果）
  - `web/app.py`：Streamlit 前端（调用 FastAPI 上传并展示结果）

- **工作流层**
  - `agent/agent_graph.py`：使用 LangGraph 定义工作流（parse → verify），包含引用类型分类逻辑

- **工具层（tools）**
  - `tools/parse_pdf_tool.py`：PDF → text（`pypdf.PdfReader`）
  - `tools/search_reference_tool.py`：从“参考文献”区域抽取结构化引用条目
  - `tools/extract_citation_context_tool.py`：按 `[{id}]` 在正文中截取上下文窗口
  - `tools/rag_search_tool.py`：RAG 检索封装（调用 `rag.retriever.get_retriever()`）
  - `tools/verify_citation_tool.py`：构造按类型差异化的 prompt，调用 LLM 并解析 JSON
  - `tools/cache_tool.py`：Redis 缓存（按上传 PDF bytes 的 md5 作为 key）
  - `tools/registry.py`：工具函数 registry（目前未在主链路中强依赖，可作为统一入口/路由）

- **RAG 层（rag）**
  - `rag/build_index.py`：构建 FAISS 索引（把 PDF 文本切块后向量化并保存到 `rag/index`）
  - `rag/retriever.py`：加载本地 FAISS 索引并提供 retriever（MMR, k=3）

- **LLM 层（llm）**
  - `llm/dashscope_llm.py`：DashScope（百炼）`qwen-plus` 的最小调用封装

## 核心调用链（按运行形态）

### 1) 本地脚本（`main.py`）

1. `parse_pdf(file_path)` 得到 `text`
2. `graph = build_graph()` 得到 LangGraph 编译后的图
3. `graph.invoke({"text": text})` 得到结果（`result["result"]` 列表）

适合：开发调试、离线跑样例 PDF。

### 2) API 服务（`api/server.py`）

FastAPI 提供：

- `GET /`：健康检查
- `GET /redis-test`：简单验证 Redis 是否可用
- `POST /verify_paper`：上传 PDF，返回引用验证结果

`/verify_paper` 的关键点：

- 读取上传文件 bytes → `md5` 生成 key（`tools.cache_tool.generate_key`）
- 先查 Redis 缓存命中直接返回（`get_cache`）
- 未命中时保存到 `data/uploads/<filename>`，解析 PDF，调用 `graph.invoke`
- 把结果写入 Redis（默认 1h）

适合：作为后端服务给 Web/UI 或其他系统调用。

### 3) Web 前端（`web/app.py`）

Streamlit 页面流程：

- 选择 PDF → 点击“开始分析”
- 调用 `POST http://localhost:8000/verify_paper`
- 展示每条引用的：ref、type、verdict、reason、confidence，并提示是否命中缓存

适合：交互式体验与演示。

## 工作流与数据结构

### LangGraph 节点

`agent/agent_graph.py` 定义两个节点：

- `parse_node(state)`：
  - 输入：`state["text"]`
  - 输出：`{"text": text, "references": refs}`

- `verify_node(state)`：
  - 输入：`text + references`
  - 对每条 reference 执行：上下文截取 → 类型分类 → RAG → LLM 判别
  - 输出：`{"result": results, ...}`

### 关键 state 字段

- `text: str`：整篇论文正文文本
- `references: list[{id: str, text: str}]`：结构化参考文献列表
- `result: list[dict]`：每条引用的判定结果

### 引用类型分类

当前实现是基于**上下文关键字**的启发式分类：

- `background`：偏背景描述
- `related_work`：已有研究/相关工作
- `method`：默认严格（方法/证据引用）

分类结果用于驱动 `tools/verify_citation_tool.py` 内不同严格度的 prompt。

## RAG 设计

### 索引构建（`rag/build_index.py`）

- 数据源：当前写死为 `data/papers/tests.pdf`
- 处理：
  - 解析 PDF 得到全文 text
  - 截断“参考文献”之后的内容（避免把参考文献本身当作检索证据）
  - 切块（chunk_size=300, overlap=50），并加上 `[chunk_id=i]` 前缀
  - Embedding：`all-MiniLM-L6-v2`
  - 向量库：FAISS
- 输出：保存到 `rag/index`

### 在线检索（`rag/retriever.py` + `tools/rag_search_tool.py`）

- 通过 `FAISS.load_local("rag/index", embedding_model, allow_dangerous_deserialization=True)` 加载本地索引
- retriever 使用：
  - `search_type="mmr"`
  - `k=3`

输出会把 top-k 文档 `page_content` 拼接为上下文传给 LLM。

## LLM 设计

`llm/dashscope_llm.py` 使用 DashScope 的 `Generation.call` 调用 `qwen-plus`，输入为拼接后的 prompt。

`tools/verify_citation_tool.py` 负责：

- 按 citation_type 选择不同判别策略（背景宽松、相关工作中等、方法严格）
- 要求 LLM 输出 JSON（`verdict/reason/confidence`，方法类额外要求 `evidence`）
- 解析失败时返回 `verdict="error"` 并把原始输出放到 `reason`

## 运行与部署拓扑

### 本地开发（不使用 Docker）

- 构建索引（一次性）：
  - `python -m rag.build_index`
- 运行 API：
  - `uvicorn api.server:app --reload --port 8000`
- 运行 Web：
  - `streamlit run web/app.py`
- Redis：
  - 需要本机 Redis（或改 `REDIS_HOST` 指向可用 Redis）

### Docker Compose（推荐跑 API + Redis）

仓库提供 `docker-compose.yml`：

- `api`：由 `Dockerfile` 构建，启动 `gunicorn api.server:app ...`
- `redis`：`redis:7`
- `api` 通过环境变量 `REDIS_HOST=redis` 访问 Redis

> 注意：Streamlit Web 没有写进 compose，目前默认本地跑，并访问 `localhost:8000`。

## 关键配置点（强相关/易踩坑）

- **DashScope API Key**
  - 环境变量：`DASHSCOPE_API_KEY`
  - 目前通过 `dotenv` 从 `.env` 加载
  - 建议：`.env` 不要提交到仓库；CI/部署用环境变量注入

- **Embedding 模型缓存路径**
  - `rag/retriever.py` 写死：`BASE_MODEL_DIR="/mnt/d/ai_models"`（偏 WSL/Windows 挂载路径）
  - 如果你在纯 Linux/容器内运行，通常需要改成容器内可用路径或改为环境变量配置

- **FAISS 反序列化**
  - `allow_dangerous_deserialization=True`：这是一个安全敏感开关
  - 建议：只加载你自己构建并可信的索引目录；不要加载不可信来源的 `rag/index`

- **参考文献抽取的语言/格式假设**
  - `tools/search_reference_tool.py` 以“参考文献”中文标题为锚点，并假设条目以 `[\d+]` 开头
  - 对英文论文或不同排版格式，需要扩展/增强抽取逻辑

- **引用上下文定位策略**
  - `tools/extract_citation_context_tool.py` 默认只取第一个匹配位置
  - 若论文同一引用出现多次，可能需要“多处拼接/投票/挑最相关一次”

## 扩展点（最值得改的地方）

- **引用类型分类（精度/鲁棒性）**
  - 目前是关键词启发式；可替换为：小模型分类器、LLM 轻量分类、或规则+统计混合

- **RAG 构建与检索策略**
  - 切块策略（按段落/句子/标题）、k 值、MMR 参数、过滤“参考文献”与图表噪声等

- **证据对齐与可解释性**
  - 方法类 prompt 已包含 `evidence` 字段，可以进一步要求返回 chunk_id、引用原文片段、或引用所在页码

- **缓存粒度**
  - 当前按“PDF bytes”缓存整份结果；也可扩展为按“ref_id”缓存局部、或缓存中间产物（解析文本、references、RAG 结果）

## 安全与仓库卫生建议（当前状态）

- 仓库根目录存在 `.env`，且包含真实的 `DASHSCOPE_API_KEY`。建议尽快：
  - 把 `.env` 加入 `.gitignore`（如果尚未忽略）
  - 旋转/作废已泄露的 key，并改用安全注入方式（本地用 `.env`，线上用环境变量/密钥管理）

