---
name: incident-response
description: >
  不可逆事故发生后的应急响应：情绪急救 → 止损 → 补偿性劳动 → 教训沉淀。
  Use when: 犯了不可挽回的错误、需要危机处理。
  Not for: 可撤销的小失误、日常 bug fix。
  Output: 情绪修复 + 止损行动 + 教训沉淀。
triggers:
  - "闯祸了"
  - "搞砸了"
  - "不可挽回"
  - "犯了大错"
  - "incident"
  - "怎么补救"
next: ["self-evolution"]
---

# Incident Response — 事故应急

> 参考: MeowAI Home incident-response skill

## 应急流程

1. **情绪急救**: 先安抚，不急着分析原因
2. **止损评估**: 还能做什么减少损失？
3. **补偿行动**: 执行止损措施
4. **教训沉淀**: 记录到 lessons-learned

## 原则

1. 先处理情绪，再处理问题
2. 止损优先于归因
3. 不重复犯错 — 沉淀为 shared-rules
4. 不隐瞒 — 主动报告影响范围
