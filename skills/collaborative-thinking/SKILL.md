---
name: collaborative-thinking
description: >
  单人或多猫的创意探索、独立思考、讨论收敛。
  Use when: brainstorm、多猫独立思考、讨论结束需要收敛。
  Not for: 已有明确 spec 直接写代码。
  Output: 收敛报告（共识/分歧/行动项）。
triggers:
  - "brainstorm"
  - "讨论"
  - "多猫独立思考"
  - "收敛"
  - "总结一下"
next: ["writing-plans", "feat-lifecycle"]
---

# Collaborative Thinking — 协作思考

> 参考: MeowAI Home collaborative-thinking skill

## 模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **发散** | 每只猫独立思考，不互相干扰 | 开放性问题、方案设计 |
| **收敛** | 汇总结览，提取共识 | 讨论结束、决策前 |

## 发散模式 (Ideate)

每只猫独立回答，产出去重后的独立见解：
- 核心观点
- 支撑论据
- 潜在风险

## 收敛模式 (Converge)

汇总所有猫的观点，产出收敛报告：

```markdown
## 收敛报告

### 共识
1. {所有猫都同意的点}

### 分歧
1. {有争议的点} — 正方: ... / 反方: ...

### 行动项
- [ ] {下一步行动}
```

## 原则

1. **不批评**: 发散阶段不评价他人观点
2. **建设性**: 分歧必须附带替代方案
3. **可操作**: 行动项必须有明确负责人和时间
