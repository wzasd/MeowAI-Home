---
name: receive-review
description: >
  处理 reviewer 反馈：Red→Green 修复 + 技术论证（禁止表演性同意)。
  Use when: 收到 review 结果、 reviewer 提了 P1/P2、 需要处理反馈。
  Not for: 发 review 请求（用 request-review）、自检（用 quality-gate)。
  Output: 逐项修复确认 + reviewer 放行。
triggers:
  - "review 结果"
  - "review 意见"
  - "reviewer 说"
---

# Receive Review

**铁律**: 不表演性同意。如果不确定, 技术论证。

## 流程

```
1. 逐项处理
2. 标记颜色
   - 🔴 P0 Critical - 必须修复
   - 🟡 P1 Important - 建议修复
   - 🟢 P2 Nice to have - 可选

3. 修复
4. Re-trigger review
```
