---
name: cross-thread-sync
description: >
  跨 thread 协同：发现平行 session → 通知 → 争用协调 → 确认。
  Use when: 平行 session 之间需要协同、通知改动影响。
  Not for: 跨猫工作交接（用 cross-cat-handoff）。
  Output: cross-post 通知 + 争用协调完成。
triggers:
  - "通知另一个 session"
  - "跨 thread"
  - "平行世界"
  - "parallel session sync"
  - "cross-thread"
next: []
---

# Cross-Thread Sync — 跨 Thread 协同

> 参考: Clowder AI cross-thread-sync skill

## 流程

1. **发现平行 session**: 检测是否有其他 thread 在操作相同文件
2. **通知 (3+2 件套)**:
   - What: 改了什么
   - Why: 为什么改
   - Impact: 影响范围
   - Open: 是否需要协调
   - Next: 建议的下一步
3. **争用协调**: 如有冲突，按优先级协调
4. **确认**: 双方确认协调完成

## 原则

1. 先发现后行动，不盲目操作
2. 共享文件争用时主动通知
3. 协调结果必须双方确认
