---
name: feat-lifecycle
description: >
  Feature 立项、讨论、完成的全生命周期管理。
  Use when: 开个新功能、new feature、立项、feature 完成、验收通过。
  Not for: 代码实现、review、merge（有专门的 skill）。
  Output: Feature 聚合文件 + BACKLOG 索引。
triggers:
  - "开个新功能"
  - "new feature"
  - "立项"
  - "feature 完成"
  - "验收通过"
  - "讨论新功能需求"
next: ["writing-plans"]
---

# Feature Lifecycle — 功能生命周期管理

> 参考: MeowAI Home feat-lifecycle skill

## 三个阶段

| 阶段 | 动作 | 产出 |
|------|------|------|
| **Kickoff** | 收集需求 → 定义验收条件 → 创建 Feature 文件 | Feature 聚合文件 |
| **Discussion** | 技术方案讨论 → 拆分任务 | 任务列表 |
| **Completion** | 验收检查 → 关闭 Feature | 完成报告 |

## Kickoff 流程

1. **收集需求**: 明确功能目标、用户故事、边界条件
2. **定义验收条件**: 写出可验证的 AC (Acceptance Criteria)
3. **创建 Feature 文件**: `docs/features/{feature-id}.md`

## Feature 文件模板

```markdown
# {Feature ID}: {名称}

## 愿景
{一句话描述这个功能要解决什么问题}

## 验收条件
- [ ] AC1: ...
- [ ] AC2: ...

## 任务分解
- [ ] Task 1: ...
- [ ] Task 2: ...

## 状态
📋 Kickoff / 🔨 开发中 / ✅ 完成
```

## Completion 流程

1. 逐项检查验收条件
2. 确认所有任务完成
3. 更新 Feature 文件状态
4. 触发 `feat-lifecycle` 完成闭环
