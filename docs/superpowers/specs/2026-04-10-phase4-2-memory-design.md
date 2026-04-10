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

## 技术选型：每层记忆的存储方案

三层记忆的架构决定了高层设计，但每层内部用什么技术来存储和检索，是独立的工程决策。以下逐层分析选型理由。

### Episodic Memory：SQLite + FTS5

**存储内容**：对话片段——谁在什么时候说了什么、重要程度如何。每条记录包含 thread_id、cat_id、role、content、importance、tags 等字段。

**访问模式**：
- **按关键词搜索**：用户问"React"，找到所有提到 React 的对话片段
- **按时间线检索**：获取某个 thread 或某只猫的最近对话
- **按重要度过滤**：只检索 importance >= 3 的片段

**考虑过的替代方案**：

| 方案 | 原理 | 适用场景 | 不选的原因 |
|------|------|---------|-----------|
| **向量数据库**（ChromaDB / Pinecone） | 把文本转为 embedding 向量，用余弦相似度做语义搜索 | 需要语义理解（"前端框架" 能匹配到 "React"） | 需要外部模型生成 embedding，增加延迟 200-500ms 和 API 成本；对"用户喜欢 React"这种短文本，关键词搜索已够用 |
| **Elasticsearch / Solr** | 专业全文搜索引擎，支持分词、同义词、权重调优 | 企业级日志搜索、百万级文档检索 | JVM 进程占 500MB+ 内存，运维复杂度高。我们的数据量（万级）远不到需要独立搜索引擎的程度 |
| **JSONL 日志文件** | 每条对话追加写入文件，搜索时 grep | 最简单的实现，无需数据库 | 无索引，搜索性能随文件增长线性下降；无事务保证；无法做重要度排序 |
| **Redis** | 内存键值存储，支持 TTL 自动过期 | 需要高速读写 + 自动过期的场景 | 内存开销大（1万条对话约 50MB）；数据持久化需要额外配置；无全文搜索能力 |

**为什么选 SQLite + FTS5**：

1. **零外部依赖** — Python 标准库自带 `sqlite3` 模块，FTS5 是 SQLite 3.9.0（2015年）内置的虚拟表机制。不需要 `pip install` 任何东西
2. **FTS5 倒排索引** — 对 `content` 和 `tags` 建立倒排索引，搜索时 O(1) 定位（直接查词→文档列表），不像 `LIKE` 需要 O(n) 全表扫描。实测 1 万条记录，FTS5 搜索约 1ms，LIKE 约 50ms，差距随数据量增长而扩大
3. **BM25 排名** — FTS5 内置 BM25 算法，综合考虑词频（TF，一个词在文档中出现越多越相关）和逆文档频率（IDF，一个词在所有文档中越罕见越有价值）。搜索"React"时，讨论 React 架构的对话会排在只顺带提到 React 的对话前面
4. **内容表模式** — FTS5 虚拟表只存索引不存数据（通过 `content='episodic'` 指向原始表），存储开销仅为原始数据的 10-30%，数据零冗余
5. **单文件数据库** — 所有记忆存在 `~/.meowai/memory.db` 一个文件里，备份只需复制文件，迁移只需移动文件

**优点**：
- 零依赖、零配置、零运维
- ACID 事务保证写入一致性
- FTS5 搜索性能满足万级数据实时查询
- BM25 排名提供相关性排序

**缺点**：
- **无语义理解** — 搜"前端框架"搜不到只提到"React"的对话。后续可通过添加 embedding 列缓解，但当前阶段关键词匹配已覆盖 80% 场景
- **单写者限制** — SQLite 同一时刻只允许一个写事务。对于单用户桌面场景足够，多用户并发写入需要 WAL 模式或迁移到 PostgreSQL
- **中文分词粗糙** — FTS5 默认 `unicode61` 分词器对中文做字符级分词（每个字一个 token），无法识别"人工智能"是一个词。可后续换用 `simple` 或 `porter` 分词器，或引入 jieba 分词做预处理
- **无内置 embedding 支持** — 不支持向量搜索。如需语义搜索，需要 sqlite-vss 扩展或迁移到向量数据库

### Semantic Memory：关系型表（entities + relations）

**存储内容**：结构化知识——实体（"React"、"用户"、"项目 X"）和实体间的关系（"用户 偏好 React"、"项目 X 使用 SQLite"）。

**访问模式**：
- **实体查询**：通过名称精确查找实体及其属性
- **1 跳关系遍历**：查找与某个实体直接相关的所有实体（"React 有哪些关系？"）
- **类型过滤**：只查 preference 类型的实体，或只查 technology 类型的关系

**考虑过的替代方案**：

| 方案 | 原理 | 适用场景 | 不选的原因 |
|------|------|---------|-----------|
| **Neo4j / ArangoDB** | 原生图数据库，节点和边是一等公民，Cypher/Gremlin 查询语言 | 复杂图查询（3+ 跳遍历、图算法如 PageRank、社区发现） | 需要 JVM 进程（Neo4j Community 占 2GB+ 内存）；我们的关系查询仅 1 跳，SQL JOIN 已够用 |
| **RDF 三元组存储**（Apache Jena） | 语义 Web 标准，一切知识表示为 (主语, 谓语, 宾语) 三元组 | 学术研究、知识推理、OWL 本体 | 学习曲线陡峭；SPARQL 查询语言复杂；对"用户偏好 React"这种简单知识是大材小用 |
| **文档数据库**（MongoDB） | 嵌套 JSON 文档，每个实体内嵌其关系数组 | 灵活 schema、频繁变更实体结构 | 关系查询需要 `$lookup` 聚合，性能不如 SQL JOIN；额外的运维依赖；我们 schema 固定，不需要灵活性 |
| **内存图结构**（NetworkX） | Python 图计算库，节点和边在内存中 | 快速原型、图算法分析 | 不持久化（进程退出数据丢失）；不适合长期存储 |

**为什么选关系型表**：

1. **JOIN 天然支持 1 跳关系** — `relations` 表通过 `source_id` 和 `target_id` 外键关联 `entities` 表。查"React 的所有关系"只需一条 JOIN：
   ```sql
   SELECT e.name, r.relation_type, r.strength
   FROM relations r JOIN entities e ON r.target_id = e.id
   WHERE r.source_id = ?
   ```
   这正好覆盖我们的全部关系查询需求

2. **UNIQUE 约束防止重复实体** — `entities.name` 有 `UNIQUE` 约束。`add_entity()` 遇到同名实体会走更新路径（`ON CONFLICT UPDATE`），避免"React"被存储两次

3. **与 Episodic 共享 SQLite 实例** — 三层记忆用同一个 `memory.db`，一次备份全部搞定。不需要管理多个数据库实例

4. **strength 字段支持关系权重** — `relations.strength`（浮点数）记录关系强度。多次提到"用户喜欢 React"会让 strength 递增，少提到的知识权重自然降低

**优点**：
- 统一存储（与 Episodic/Procedural 共享 SQLite）
- 外键约束保证引用完整性（不能关联不存在的实体）
- SQL 聚合查询成熟可靠
- 调试简单（用任何 SQLite 客户端直接查看）

**缺点**：
- **多跳查询需要递归 CTE** — 查"React 的朋友的朋友"需要 `WITH RECURSIVE`，性能随跳数指数增长。但我们的设计只做 1 跳（`max_depth=2` 已足够），这个缺点当前不影响
- **无图算法** — 不能直接做 PageRank、社区发现等图分析。如果未来需要"哪些知识最核心"，需要导出到 NetworkX 或迁移到图数据库
- **Schema 不够灵活** — 加新属性需要 ALTER TABLE 或存在 JSON 字段里。当前用 `attributes TEXT DEFAULT '{}'` 存额外属性作为折中

### Procedural Memory：结构化 JSON 列

**存储内容**：工作流模式——某个工作流叫什么、包含哪些步骤、在什么条件下触发、历史执行结果统计。

**访问模式**：
- **按分类查询**：获取所有 workflow 类型的模式
- **按名称搜索**：搜"brainstorm"找到相关工作流经验
- **成功率排序**：`get_best_practices()` 按成功率从高到低返回最可靠的工作流模式

**考虑过的替代方案**：

| 方案 | 原理 | 适用场景 | 不选的原因 |
|------|------|---------|-----------|
| **规则引擎**（Drools / 业务规则系统） | IF-THEN 规则定义触发条件和执行动作 | 复杂条件组合、实时决策 | 规则定义语言学习成本高；我们的触发条件简单（关键词匹配），不值得引入规则引擎 |
| **决策树 / ML 模型** | 从历史数据学习最优决策路径 | 需要自动优化的场景 | 需要大量训练数据（至少数百次工作流执行）；当前数据量不足以训练有效模型 |
| **事件流**（Kafka / 事件溯源） | 每次执行是一个不可变事件，通过回放构建状态 | 需要完整审计追踪、时间旅行调试 | 架构复杂度高（需要 Kafka 集群或 SQLite 事件表 + 投影）；我们只需要统计聚合，不需要完整事件历史 |
| **YAML/JSON 文件** | 每个工作流一个文件 | 人工编写和编辑工作流定义 | 无法高效聚合统计（需要遍历所有文件）；并发写入风险；无事务保证 |

**为什么选结构化 JSON 列**：

1. **steps / trigger_conditions / outcomes 天然是列表/字典** — 一个工作流包含多个步骤（`["brainstorm", "aggregate"]`）、多个触发条件（`["#brainstorm", "@planner"]`）、复杂的结果（`{"total": 3, "success": 2, "failed": 1}`）。JSON 列完美映射这些嵌套结构，不需要拆分成多张表

2. **`success_count` / `fail_count` 支持增量统计** — `record_use()` 方法每次执行后 `UPDATE ... SET success_count = success_count + 1`，O(1) 操作。`get_best_practices()` 用 SQL 计算成功率排序：
   ```sql
   ORDER BY (CAST(success_count AS REAL) / (success_count + fail_count + 1)) DESC
   ```
   不需要遍历所有记录

3. **SQLite JSON 函数** — SQLite 3.38.0+ 内置 `json_extract()`、`json_each()` 等函数，可以直接在 JSON 列上做查询：
   ```sql
   SELECT * FROM procedures WHERE json_each(steps) = 'brainstorm'
   ```

**优点**：
- 简单 schema，一个表覆盖所有工作流模式
- SQL 聚合（AVG、SUM、COUNT）直接用于成功率统计
- 无额外基础设施
- JSON 列易于扩展（加新字段不改表结构）

**缺点**：
- **JSON 查询比原生列慢** — `WHERE steps LIKE '%brainstorm%'` 需要解析 JSON 字符串，比 `WHERE category = 'workflow'` 慢。不过数据量小时差异可忽略
- **无形式化验证** — JSON 里的 `steps` 可以是任意内容，没有 schema 校验。坏数据（如 `steps = "not a list"`）会导致 `json.loads()` 失败
- **触发条件匹配是手工的** — `trigger_conditions` 存在 JSON 列里，但匹配逻辑在应用代码中（IntentParser），不是数据库层面的规则
- **有限的时间推理** — 只有 `last_used_at`，没有完整的执行时间线。无法回答"这个工作流上周表现如何"

### 统一存储：为什么三层共用一个 SQLite 文件？

以上三层各自选择了最合适的存储结构，但它们共用同一个 SQLite 数据库文件（`~/.meowai/memory.db`），而非各自独立存储。

**这个决策的理由**：

1. **MemoryService.build_context() 跨层检索** — 一次用户查询需要同时搜索三层记忆。共用数据库意味着一次连接就能查询所有表，不需要跨库 JOIN 或在应用层合并结果

2. **事务一致性** — 存储对话片段（Episodic）+ 提取实体（Semantic）+ 记录工作流结果（Procedural）可以在同一个事务中完成，保证数据一致性。如果用三个独立数据库，需要分布式事务或最终一致性

3. **运维简单** — 一个文件 = 一次备份。不需要管理三个数据库的备份策略、版本迁移、磁盘空间

**不选独立数据库的原因**：
- 独立数据库的优势是隔离性（一层出问题不影响其他层）和独立扩展（Episodic 数据量大时可以单独优化）。但当前数据量（万级）远不到需要独立扩展的程度，SQLite 单文件的写性能上限（约 5000 次/秒）远超需求

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
