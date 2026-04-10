---
name: debugging
description: >
  系统化 bug 定位：根因调查 → 模式分析 → 假设验证 → 修复。
  Use when: 遇到 bug、测试失败、 unexpected behavior。
  Not for: 新功能开发、重构、 已知原因的简单修复。
  Output: Bug report（5件套）+ 根因 + 修复（含回归测试)。
triggers:
  - "bug"
  - "报错"
  - "test failure"
  - "unexpected behavior"
---

# Debugging

系统化 bug 定位流程。

## 流程

```
1. 填诊断胶囊
   - 现象：看到了什么？
   - 证据:日志、错误信息、   - 假设:可能的原因
   - 诊断策略:如何验证

2. 写复现测试
   - 必须先失败

3. 验证假设
   - 逐步排除

4. 修复
   - 写代码
   - 确保测试通过

5. 回归测试
   - 跑全量测试
```
