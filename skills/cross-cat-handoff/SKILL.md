---
name: cross-cat-handoff
description: >
  跨猫传话/交接的五件套结构（What/Why/Tradeoff/Open/Next）。
  Use when: 交接工作给其他猫、传话、写 review 信。
  Not for: 自己的任务。
  Output: 结构化交接信。
triggers:
  - "交接"
  - "传话"
  - "handoff"
next: []
---

# Cross-Cat Handoff — 跨猫交接

> 参考: MeowAI Home cross-cat-handoff skill

## 五件套结构

```markdown
## 交接信: {from} → {to}

### What
{交接的内容是什么}

### Why
{为什么要交接/背景}

### Tradeoff
{已知的权衡/取舍}

### Open
{未解决的问题/风险}

### Next
{建议的下一步}
```

## 原则

1. **完整**: 五件套缺一不可
2. **简洁**: 每件 ≤ 3 句话
3. **可操作**: Next 必须具体
