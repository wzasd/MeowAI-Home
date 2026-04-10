---
name: merge-gate
description: >
  合入 main 的完整流程: 门禁检查 → PR → 云端 review → squash merge → 清理。
  Use when: reviewer 放行后准备合入、开 PR、 触发云端 review、 准备 merge。
  Not for: 开发中、review 未通过、自检未完成。
  Output: PR merged + worktree cleaned.
triggers:
  - "合入 main"
  - "merge"
  - "准备合入"
  - "开 PR"
---

# Merge Gate

## 流程

```
1. 检查 reviewer 放行
2. 创建 PR
   - gh pr create

3. 触发云端 review
4. 等待通过
5. Squash merge
   - gh pr merge --squash

6. 清理 worktree
```
