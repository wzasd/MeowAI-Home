# Phase 4.2 开发日记 — 三层记忆系统

**日期**: 2026-04-09
**角色**: 阿橘（实现）、花花（设计）、墨点（审查）

---

## 午夜的思考

Phase 4.3 刚把 MCP 工具加到 15 个，三只猫不休息，直接进入记忆系统。

### 花花的设计

"三层记忆架构，参考 Clowder AI 和认知科学："

| 层 | 名称 | 存什么 | 类比 |
|---|------|--------|------|
| L1 | **Episodic** | 对话片段 | 日记本 |
| L2 | **Semantic** | 实体关系 | 百科全书 |
| L3 | **Procedural** | 工作流模式 | 经验手册 |

"猫记住的不只是'说了什么'（Episodic），还有'知识点'（Semantic）和'怎么做'（Procedural）。"

### 阿橘的实现

一个文件搞定四层架构：`src/memory/__init__.py`

```python
MemoryDB          # SQLite 底层（5 张表）
EpisodicMemory    # 对话片段（thread_id + cat_id + importance）
SemanticMemory    # 知识图谱（entities + relations）
ProceduralMemory  # 工作流模式（steps + success_count）
MemoryService     # 统一检索（build_context 自动拼三层记忆）
```

**Episodic** 的核心是 `importance` 字段。普通聊天 importance=0，关键决定=5，不可逆决策=9。检索时可以按重要性过滤。

**Semantic** 的核心是实体-关系模型。`add_entity("Django", "framework")` + `add_relation("Django", "Python", "depends_on")` 就构成了一条知识。

**Procedural** 的核心是 `success_count` / `fail_count`。每次用完记录成败，`get_best_practices()` 自动算成功率排名。

**MemoryService.build_context()** 是魔法入口：
1. 拆分搜索词
2. 并行搜索三层记忆
3. 去重拼成 Markdown
4. 注入系统提示

### 墨点的审查

"……数据库有索引？"

"有。episodic 有 thread_id 和 cat_id 索引，relations 有 source_id 索引，procedures 有 category 索引。"

"……关系查询支持多跳？"

"参数写了 max_depth，目前只实现了单跳。多跳后续加。"

"……够用。测试呢？"

"24 个。7 个 Episodic + 8 个 Semantic + 5 个 Procedural + 4 个 Service。"

---

## build_context 的搜索改进

一开始 `build_context("React 前端")` 搜不到东西——因为搜索词是整个字符串，而数据库里只存了 "React" 或 "前端"。

改成拆分关键词，每个词单独搜，然后去重。效果好多了。

---

## 统计

| 项目 | 数量 |
|------|------|
| 新增模块 | 1 (src/memory/) |
| 数据表 | 5 (episodic, entities, relations, procedures, memories) |
| 新增测试 | 24 |
| 总测试数 | 203 (100% 通过) |

---

## 第二夜：技术选型辩论

*Phase 7 完成后，铲屎官决定回头把记忆系统接上。三只猫围在白板前，讨论每层记忆用什么技术。*

### Episodic：SQLite + FTS5 的决定

**花花**先画了一张表：

"Episodic 存的是对话片段。核心访问模式是关键词搜索——用户问 React，找到所有提到 React 的对话。"

她列出了四个候选：

| 方案 | 原理 | 不选的原因 |
|------|------|-----------|
| 向量数据库（ChromaDB） | embedding 余弦相似度，语义搜索 | 需要 API 调用生成 embedding，+200ms 延迟 |
| Elasticsearch | 专业全文搜索引擎 | JVM 占 500MB+，万级数据用不着 |
| JSONL 日志文件 | 追加写入，grep 搜索 | 无索引，数据大了搜索线性变慢 |
| Redis | 内存 KV 存储 | 无全文搜索，内存贵 |

**阿橘**举手："那我选 SQLite + FTS5！Python 自带 sqlite3，FTS5 是 2015 年就内置的，零依赖。"

**墨点**皱眉："FTS5 是什么原理？"

**阿橘**在白板上画了张图：

```
普通搜索 (LIKE '%React%'):
  对话1 → 逐字匹配 → 不含 → 跳过
  对话2 → 逐字匹配 → 不含 → 跳过
  对话3 → 逐字匹配 → 含有 → 返回  ← O(n) 全表扫描

FTS5 倒排索引:
  建索引: "React" → [对话3, 对话7, 对话15]
  搜  索: 查 "React" → 直接得到 [3, 7, 15]  ← O(1) 定位
```

"倒排索引——先建好'哪个词出现在哪个文档里'的映射表。搜索时直接查映射，不需要扫描全表。"

**墨点**："排序呢？LIKE 按插入时间排，不是相关性。"

**花花**接过话："FTS5 内置 BM25 排名算法。综合考虑两个因素：
- **词频（TF）**：一个词在文档中出现越多，这个文档越相关
- **逆文档频率（IDF）**：一个词在所有文档中越罕见，匹配到它越有价值

所以'讨论 React 架构设计'的对话会排在'顺便提到 React 还行'的前面。"

**墨点**："缺点？"

**阿橘**数了三个：
1. **无语义理解** — 搜"前端框架"搜不到只写"React"的对话。后续可加 embedding 缓解
2. **中文分词粗糙** — 默认 unicode61 做字符级分词，"人工智能"会被拆成"人""工""智""能"
3. **单写者限制** — SQLite 同一时刻只允许一个写事务。单用户够用，多用户需要 WAL 模式

**墨点**点了点头："……够用。数据量万级，FTS5 性能远超需求。继续。"

### Semantic：为什么不用图数据库？

**花花**翻到下一页："Semantic 记忆存的是知识图谱——实体和关系。'用户偏好 React'、'项目使用 SQLite'。"

"直觉上应该用图数据库——Neo4j 或者 ArangoDB。毕竟知识图谱天然是图结构。"

**阿橘**摇头："Neo4j Community 需要 JVM，占 2GB+ 内存。我们的关系查询只做 1 跳——查'React 的所有关系'，SQL JOIN 一条就够了："

```sql
SELECT e.name, r.relation_type, r.strength
FROM relations r JOIN entities e ON r.target_id = e.id
WHERE r.source_id = ?
```

"1 跳遍历不需要图数据库。3 跳以上才有优势。"

**花花**补充了对比：

| 方案 | 适用场景 | 我们的情况 |
|------|---------|-----------|
| Neo4j | 3+ 跳遍历、PageRank | 只做 1 跳，SQL JOIN 够用 |
| RDF 三元组 | 语义推理、OWL 本体 | 学习曲线陡峭，杀鸡用牛刀 |
| MongoDB | 灵活 schema | 关系查询要 $lookup，不如 JOIN |
| NetworkX | 图算法分析 | 不持久化，进程退出数据丢失 |

"选关系型表的理由：与 Episodic 共享 SQLite 实例，外键保证引用完整性，UNIQUE 约束防重复实体，调试直接用 SQLite 客户端查看。"

**墨点**："strength 字段？"

**花花**："`relations.strength` 是浮点数，记录关系强度。多次提到'用户喜欢 React'，strength 递增。少提到的知识权重自然降低。"

**墨点**："……好。缺点？"

"多跳查询需要递归 CTE，性能随跳数指数增长。但我们只做 1 跳，不影响。另一个是无图算法——不能做 PageRank、社区发现。"

### Procedural：JSON 列的取舍

**阿橘**主动了："Procedural 存工作流模式——brainstorm/parallel/auto_plan 的执行历史和成功率。"

"核心数据是嵌套的：steps 是列表、trigger_conditions 是列表、outcomes 是字典。用 JSON 列存这些结构天然合理。"

**墨点**："为什么不用规则引擎或者 ML 模型？"

**花花**：

| 方案 | 不选的原因 |
|------|-----------|
| 规则引擎（Drools） | 触发条件只是关键词匹配，不需要 IF-THEN 规则语言 |
| ML 决策树 | 需要数百次执行记录才能训练，当前数据量不够 |
| 事件流（Kafka） | 架构复杂度高，我们只需要聚合统计 |
| YAML 文件 | 无法聚合统计，并发写入风险，无事务保证 |

"选 JSON 列的理由：一个表覆盖所有模式，`success_count`/`fail_count` 支持增量统计，SQLite 3.38+ 有 `json_extract()` 原生 JSON 查询。"

**阿橘**："缺点是 JSON 查询比原生列慢——`WHERE steps LIKE '%brainstorm%'` 要解析字符串。但数据量小时差异可忽略。"

### 统一存储的最后决定

**墨点**："三层用三个数据库还是一个？"

**花花**："一个。`~/.meowai/memory.db`。"

"理由：
1. `build_context()` 一次连接搜索三层，不需要跨库合并
2. 存对话 + 提取实体 + 记录工作流可以在同一个事务中完成
3. 备份一次搞定——复制一个文件

独立数据库的优势是隔离和独立扩展，但万级数据远不需要。"

**墨点**在白板上画了个框：

```
~/.meowai/memory.db
├── episodic        (对话片段)
├── entities        (知识实体)
├── relations       (实体关系)
├── procedures      (工作流模式)
└── memories        (向后兼容 KV)
```

"……就这样。开始实现。"

---

## Phase 4.2 升级：从孤岛到自动化

*以上是 Phase 4.2 初次构建三层记忆系统的日记。609 行代码写完了，但从未被任何模块导入——它是孤立代码。*

*Phase 7 完成后，铲屎官决定回头接入记忆系统。这次的工作不是写新代码，而是：*
1. *FTS5 搜索升级（替换 LIKE）*
2. *4 种自动化行为（自动存储、自动检索、实体提取、工作流记录）*
3. *接入 A2AController 活跃流程*

*详细设计见 `docs/superpowers/specs/2026-04-10-phase4-2-memory-design.md`*

---

*花花合上设计文档："Phase 4 全部完成——技能、记忆、工具，三位一体。可以准备 Phase 5 Web UI 了。"*

*阿橘趴在键盘上："先让我睡一觉..."*

*墨点默默在测试报告上画了最后一个勾。*
