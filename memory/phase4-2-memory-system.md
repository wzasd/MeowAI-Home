---
name: Phase 4.2 三层记忆系统完成
description: >
  Episodic(对话片段)/Semantic(知识图谱)/Procedural(工作流模式) 三层记忆，
  MemoryService 统一检索，SQLite 存储，24 测试全部通过，203 总测试。
type: project
created: 2026-04-09
---

# Phase 4.2: 三层记忆系统完成

## 三层记忆架构

| 层 | 类 | 存什么 | 关键方法 |
|---|---|--------|---------|
| Episodic | EpisodicMemory | 对话片段 + 重要度 + 标签 | store, recall_by_thread, search |
| Semantic | SemanticMemory | 实体 + 关系（知识图谱） | add_entity, add_relation, get_related |
| Procedural | ProceduralMemory | 工作流模式 + 成功率 | store_procedure, record_use, get_best_practices |

## MemoryService
- `store_episode()` — 存储对话到 Episodic
- `build_context(query)` — 自动检索三层记忆，拼成 Markdown 上下文
- 拆分关键词搜索 + 去重

## 存储
- SQLite: ~/.meowai/memory.db
- 5 张表：episodic, entities, relations, procedures, memories
- 有索引优化

## 统计
- 总测试: 203 (100%)
- 新增测试: 24
