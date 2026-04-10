---
name: writing-plans
description: >
  将 spec/需求拆分为可执行的分步实施计划。
  Use when: 有 spec 或需求，准备动手前需要拆分步骤。
  Not for: trivial 改动（≤5 行）、已有详细计划。
  Output: 分步实施计划（含 TDD 步骤和检查点）。
triggers:
  - "写计划"
  - "implementation plan"
  - "拆分步骤"
next: ["worktree"]
---

# Writing Plans — 编写实施计划

> 参考: Clowder AI writing-plans skill

## 计划模板

```markdown
# 实施计划: {功能名称}

## 前置条件
- [ ] spec 已确认
- [ ] 验收条件已定义

## 步骤

### Task 1: {名称}
- 文件: `path/to/file.py`
- 测试: `tests/test_xxx.py`
- TDD: 先写失败测试 → 最小实现 → 重构
- 检查点: {通过条件}

### Task 2: ...
```

## 原则

1. **每步可独立测试**: 每个 task 完成后都能跑测试验证
2. **含 TDD 步骤**: 明确先写什么测试
3. **检查点清晰**: 知道什么时候算完成
4. **文件级别粒度**: 每个 task 涉及的具体文件
