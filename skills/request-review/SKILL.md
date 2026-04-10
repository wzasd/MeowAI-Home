---
name: request-review
description: >
  向跨家族 peer-reviewer 发送 review 请求（含五件套)。
  Use when: 自检通过后准备请其他猫 review。
  Not for: 收到 review 结果（用 receive-review)、自检（用 quality-gate)。
  Output: Review 请求信（存档到 review-notes/).
triggers:
  - "请 review"
  - "帮我看看"
  - "request review"
---

# Request Review

## 五件套结构

```
1. WHAT - 做了什么改动
2. WHY - 为什么要做这个改动
3. TRADEOFF - 有哪些权衡取舍
4. OPEN QUESTIONS - 还有哪些疑问
5. NEXT - 下一步计划
```
