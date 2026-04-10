# Phase 4.2: 长期记忆系统设计规格

> **日期**: 2026-04-10
> **前置**: Phase 7 高级协作 (v0.7.0) 已完成
> **范围**: 接入已有三层记忆系统 + FTS5 搜索升级 + 4 种自动化行为

---

## 设计背景：为什么需要三层记忆？

### 人类记忆的启示

认知心理学将人类记忆分为三种类型，每种服务于不同的认知需求：

**情景记忆（Episodic Memory）** — 记住"发生了什么"。
- 人：记得昨天和朋友的对话内容
- AI：记住用户上次问的问题和猫给的回答
- 价值：对话连续性。猫知道"我们之前讨论过 X"，避免重复回答或丢失上下文

**语义记忆（Semantic Memory）** — 记住"是什么"。
- 人：知道"Python 是一种编程语言"
- AI：知道"用户偏好 React 而非 Vue"、"项目使用 SQLite"
- 价值：知识积累。猫不需要每次重新了解用户偏好和项目约束

**程序记忆（Procedural Memory）** — 记住"怎么做"。
- 人：知道骑车不需要思考平衡
- AI：知道"头脑风暴模式在这个项目上成功率 80%"
- 价值：经验复用。猫基于过去的工作流经验做出更好的决策

### 为什么不用单一记忆？

单一记忆（如简单的 key-value 存储）有两种常见模式，都有明显缺陷：

**模式 1: 全文索引** — 把所有对话存入搜索库，需要时搜索。
- 缺陷：搜索结果是一堆对话片段，缺乏结构化知识。"用户喜欢 React" 散落在几十条对话中，每次都要重新提取。

**模式 2: 纯知识图谱** — 只存结构化实体和关系。
- 缺陷：丢失原始上下文。知道"用户喜欢 React"但不知道为什么、什么时候说的、在什么场景下。

三层记忆的设计哲学：**每种记忆解决一种认知需求，互补而非互斥**。对话检索用情景记忆，知识查询用语义记忆，经验指导用程序记忆。`MemoryService.build_context()` 融合三层的结果，猫看到的是完整上下文。

---

## 技术原理：FTS5 全文搜索

### 为什么升级搜索？

当前所有搜索使用 SQL `LIKE '%query%'`，三个致命问题：

1. **全表扫描** — `LIKE '%keyword%'` 无法使用索引，每条记录都要逐字匹配。100 条记忆无感，10000 条时延迟明显
2. **无分词** — "用户喜欢React框架" 搜 "React" 可以命中，但搜 "框架" 时 "React框架" 不算精确匹配
3. **无排序** — 结果按插入时间返回，而非相关性

### FTS5 是什么？

FTS5 (Full-Text Search 5) 是 SQLite 内置的全文搜索引擎，于 2015 年加入 SQLite 核心。不需要任何外部依赖——只要系统有 SQLite（Python 标准库自带），就有 FTS5。

**核心原理**：
1. **倒排索引** — FTS5 为每个词维护一个"哪些文档包含这个词"的索引表。搜索时直接查索引，O(1) 定位，不需要扫描全表
2. **分词器** — 将文本拆分为词（tokens），建立索引。默认 `unicode61` 分词器支持 Unicode，对中文做字符级分词
3. **BM25 排序** — 内置 BM25 排名算法，综合考虑词频（TF）和文档频率（IDF），自动将最相关的结果排在前面

**实际效果**：
```
-- LIKE 搜索（全表扫描）
SELECT * FROM episodic WHERE content LIKE '%React%'
-- 扫描 10000 行，耗时 ~50ms

-- FTS5 搜索（倒排索引）
SELECT * FROM episodic_fts WHERE episodic_fts MATCH 'React' ORDER BY rank
-- 查索引定位，耗时 ~1ms
```

50 倍加速，且数据量越大差距越明显。

### FTS5 的内容表模式

FTS5 使用"内容表模式"（`content=`），数据只存一份在原始表中，FTS5 虚拟表只存索引：

```sql
-- 原始表存数据
CREATE TABLE episodic (id INTEGER PRIMARY KEY, content TEXT, tags TEXT, ...);

-- FTS5 虚拟表只存索引
CREATE VIRTUAL TABLE episodic_fts USING fts5(
    content, tags,
    content='episodic',    -- 指向原始表
    content_rowid='rowid'  -- 用原始表的 rowid
);

-- 通过触发器自动同步
CREATE TRIGGER episodic_ai AFTER INSERT ON episodic BEGIN
    INSERT INTO episodic_fts(rowid, content, tags) VALUES (new.rowid, new.content, new.tags);
END;
```

优点：数据零冗余，插入/删除自动同步，存储开销仅为索引大小（通常原始数据的 10-30%）。

---

## 现有代码状态

### 已有但未接入的代码

`src/memory/__init__.py` (609 行) 包含完整的三层架构：

| 类 | 行数 | 职责 | 数据表 |
|----|------|------|--------|
| `MemoryDB` | 17-118 | SQLite 连接管理 + 建表 | 创建所有表 |
| `EpisodicMemory` | 125-224 | 对话片段存储 | `episodic` |
| `SemanticMemory` | 231-395 | 知识图谱 | `entities` + `relations` |
| `ProceduralMemory` | 402-500 | 工作流模式 | `procedures` |
| `MemoryService` | 507-609 | 统一检索服务 | 组合以上三层 |

**关键问题**: `MemoryService` 从未被任何模块导入或使用。它是孤立代码。

### 活跃但简单的记忆

`src/collaboration/mcp_memory.py` (101 行) 提供简单的 key-value 存储，通过 3 个 MCP 工具暴露：
- `save_memory` / `query_memory` / `search_knowledge`

猫必须主动调用这些工具才能存取记忆，没有自动化。

---

## 设计

### 第1节：接入 MemoryService + FTS5 升级

#### 1.1 MemoryService 单例化

将 `MemoryService` 挂载到 `app.state`，在 FastAPI lifespan 中初始化：

```python
# src/web/app.py lifespan
from src.memory import MemoryService
app.state.memory_service = MemoryService()
```

A2AController 通过构造函数接收：

```python
class A2AController:
    def __init__(self, agents, session_chain=None, memory_service=None, ...):
        self.memory_service = memory_service
```

#### 1.2 FTS5 虚拟表 + 同步触发器

在 `MemoryDB.__init__` 中创建 FTS5 虚拟表和触发器：

```sql
-- Episodic FTS
CREATE VIRTUAL TABLE IF NOT EXISTS episodic_fts USING fts5(
    content, tags, content='episodic', content_rowid='rowid'
);
CREATE TRIGGER IF NOT EXISTS episodic_ai AFTER INSERT ON episodic BEGIN
    INSERT INTO episodic_fts(rowid, content, tags) VALUES (new.rowid, new.content, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS episodic_ad AFTER DELETE ON episodic BEGIN
    INSERT INTO episodic_fts(episodic_fts, rowid, content, tags) VALUES('delete', old.rowid, old.content, old.tags);
END;

-- Entity FTS
CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
    name, description, content='entities', content_rowid='rowid'
);
-- (触发器类似)

-- Procedure FTS
CREATE VIRTUAL TABLE IF NOT EXISTS procedures_fts USING fts5(
    name, steps, content='procedures', content_rowid='rowid'
);
-- (触发器类似)
```

#### 1.3 搜索方法升级

`EpisodicMemory.search()` 从 LIKE 改为 FTS5：

```python
def search(self, query: str, limit: int = 10) -> List[dict]:
    cursor = self.db.conn.execute("""
        SELECT e.*, fts.rank
        FROM episodic_fts fts
        JOIN episodic e ON e.rowid = fts.rowid
        WHERE episodic_fts MATCH ?
        ORDER BY fts.rank
        LIMIT ?
    """, (query, limit))
    return [dict(row) for row in cursor.fetchall()]
```

SemanticMemory 和 ProceduralMemory 同理。

### 第2节：4 种自动化行为

#### 2.1 自动存储对话

**触发时机**: `_call_cat()` 返回 CatResponse 后
**实现位置**: A2AController._call_cat() 末尾

```python
if self.memory_service:
    # 存储用户消息
    self.memory_service.store_episode(
        thread_id=thread.id, role="user",
        content=message, importance=3
    )
    # 存储猫回复
    self.memory_service.store_episode(
        thread_id=thread.id, role="assistant",
        content=response.content, cat_id=breed_id,
        importance=5
    )
    # 存储思考过程（如果有）
    if response.thinking:
        self.memory_service.store_episode(
            thread_id=thread.id, role="thinking",
            content=response.thinking, cat_id=breed_id,
            importance=2
        )
```

**Importance 分级原理**:
- 用户消息 (3) — 中等重要性，提供上下文但不一定是结论
- 猫回复 (5) — 高重要性，包含分析结果、建议、决策
- 思考过程 (2) — 低重要性，中间推理过程

检索时 `build_context` 默认 `min_importance=3`，意味着思考过程不会出现在检索结果中（除非显式请求），避免噪声。

#### 2.2 自动检索注入

**触发时机**: `_call_cat()` 构建系统提示时
**实现位置**: A2AController._call_cat() 系统提示构建阶段

```python
if self.memory_service:
    memory_context = self.memory_service.build_context(
        query=message, thread_id=thread.id, max_items=5
    )
    if memory_context:
        system_prompt += f"\n\n## 相关记忆\n{memory_context}"
```

`build_context` 已有实现：分词 → 搜索三层 → 去重 → Markdown 格式化。返回格式：

```markdown
### 相关对话记忆
[orange (ep_42)] 用户上次问了关于 React 的问题...

### 相关知识
- 用户偏好: React (来源: 对话)

### 相关经验
- 头脑风暴模式在此项目成功率 80%
```

#### 2.3 自动提取实体

**触发时机**: 猫回复后、存储实体前
**实现**: 正则提取器（不调 LLM，零延迟）

```python
# src/memory/entity_extractor.py

ENTITY_PATTERNS = [
    # 偏好类: "用户喜欢/偏好/习惯 React"
    (r'用户(?:喜欢|偏好|习惯(?:用)?|常用)\s*(\w+)', 'preference'),
    # 技术类: "项目使用/采用/基于 {X} 框架/库/工具"
    (r'项目(?:使用|采用|基于)\s*(\w+)(?:\s*(?:框架|库|工具|语言))?', 'technology'),
    # 约束类: "不能用/不要用 {X}"
    (r'(?:不能用|不要用|避免)\s*(\w+)', 'constraint'),
    # 角色类: "{X} 负责/擅长 {Y}"
    (r'(\w+)(?:负责|擅长)\s*(.+?)(?:[。，,;\n]|$)', 'role'),
]

def extract_entities(text: str) -> List[Tuple[str, str, str]]:
    """从文本中提取实体。返回 [(name, type, description)]"""
    results = []
    for pattern, entity_type in ENTITY_PATTERNS:
        for match in re.finditer(pattern, text):
            name = match.group(1)
            description = match.group(0)
            results.append((name, entity_type, description))
    return results
```

**设计权衡**：正则提取会漏掉隐含表达的实体（如"我们团队一直写 Vue"表达偏好）。但调 LLM 提取会增加 500ms+ 延迟和 API 成本。正则方案渐进积累——漏掉的实体会被后续对话中更明确的表达捕获。

#### 2.4 自动提取工作流模式

**触发时机**: DAG 执行完成后（`DAGExecutor.execute()` 末尾）

```python
if self.memory_service:
    success_count = sum(1 for r in all_results if r.status == "completed")
    self.memory_service.procedure.store_procedure(
        name=dag_template_name,       # "brainstorm" / "parallel" / "auto_plan"
        category="workflow",
        steps=[n.cat_id for n in dag.nodes],
        trigger_conditions=message[:100],
        outcomes={
            "total_nodes": len(dag.nodes),
            "success": success_count,
            "failed": len(dag.nodes) - success_count,
        }
    )
```

后续对话中，`build_context` 会返回相关工作流经验，猫在决定用哪种工作流模式时可以参考历史成功率。

### 第3节：集成层

#### 3.1 文件结构

```
src/
├── memory/
│   ├── __init__.py          # 已有，修改：FTS5 建表 + 搜索升级 + 实体提取集成
│   └── entity_extractor.py  # 新增：正则实体提取器
├── collaboration/
│   └── a2a_controller.py    # 修改：接收 memory_service，4 种自动化
├── workflow/
│   └── executor.py          # 修改：执行后存储工作流模式
└── web/
    └── app.py               # 修改：lifespan 中初始化 MemoryService
```

#### 3.2 MemoryService 构造函数调整

当前 `MemoryService.__init__` 直接创建所有组件，需要确保 FTS5 表在首次使用时创建：

```python
class MemoryService:
    def __init__(self, db_path: str = None):
        self.db = MemoryDB(db_path)  # __init__ 中已创建所有表（含 FTS5）
        self.episodic = EpisodicMemory(self.db)
        self.semantic = SemanticMemory(self.db)
        self.procedure = ProceduralMemory(self.db)
```

#### 3.3 MCP 工具增强

现有 3 个 MCP 工具（save_memory/query_memory/search_knowledge）保持不变，增加一个新工具：

```python
# 新增工具：搜索所有记忆层
"search_all_memory": {
    "description": "搜索所有记忆层（对话、知识、经验），返回最相关的记忆",
    "handler": search_all_memory_handler,
}
```

让猫可以主动搜索记忆（作为自动注入的补充）。

---

## 非目标（明确排除）

- 向量搜索 / Embedding（需要外部模型，后续可加）
- Marker 审批队列（过度设计，当前规模不需要）
- LSM 式摘要压缩（数据量不到需要压缩的阶段）
- 知识图谱多跳推理（1 跳已够用）
- 跨线程记忆联邦查询

---

## 成功标准

1. 三层记忆系统接入活跃流程（不再是孤立代码）
2. FTS5 搜索工作正常（对比 LIKE 有明显加速）
3. 4 种自动化行为生效（存储、检索、实体提取、工作流模式）
4. 367 个现有测试全部通过
5. 新增测试覆盖所有新功能
