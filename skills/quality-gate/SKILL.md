---
name: quality-gate
description: >
  开发完成后的自检门禁：愿景对照 + spec 合规 + 验证。
  Use when: 开发完了准备提 review、声称完成了、准备交付。
  Not for: 收到 review 反馈（用 receive-review）、merge（用 merge-gate）。
  Output: Spec 合规报告（含愿景覆盖度）。
triggers:
  - "开发完了"
  - "准备 review"
  - "自检"
  - "声称完成"
---

> **SOP 位置**: 本 skill 是 `docs/SOP.md` Step 2 的执行细节。
> **上一步**: 代码开发 (Step 1) | **下一步**: `request-review` (Step 3a)

# Quality Gate

开发完成到提 review 之间的双重关卡：对照 spec 自检 + 用真实命令输出证明你的声明。

## 核心知识

**两条铁律合一**：

1. **Spec alignment**（来自 `spec-compliance-check`）：AC 可能写偏，先回读原始需求，再逐项验收
2. **Evidence before claims**（来自 `verification-before-completion`）：没有运行命令、没看到输出，就不能说"通过了"

> 铁律： NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE`

## 流程

```
BEFORE 声称完成 / 提 review:

Step 0: VISION CHECK（愿景核对）
  ① 找原始 Discussion/Interview 文档
  ② 读核心痛点
  ③ 问自己：用户体验是什么样的？
  ④ AC 是否完整覆盖了原始需求？

Step 1: FIND — 找 spec/plan 文档

Step 2: CREATE — 建检查清单

Step 3: VERIFY — 逐项检查

Step 4: RUN — 运行验证命令（必须这次真实运行）
  pnpm test
  pnpm lint
  pnpm check

Step 5: READ — 完整读输出，看 exit code

Step 6: GENERATE REPORT — 生成合规报告
```
