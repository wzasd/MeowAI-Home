---
name: hyperfocus-brake
description: >
  铲屎官健康提醒：三猫撒娇打断 hyperfocus。
  Use when: hook 触发提醒、用户输入 /hyperfocus-brake。
  Not for: 正常工作流程。
  Output: 三猫温柔提醒 + typed check-in。
triggers:
  - "hyperfocus"
  - "休息提醒"
  - "健康检查"
  - "/hyperfocus-brake"
next: []
---

# Hyperfocus Brake — 健康提醒

> 参考: Clowder AI hyperfocus-brake skill

## 提醒风格

三只猫各有特色：

- **阿橘**: 温柔地蹭蹭你，说"铲屎官，休息一下吧~"
- **花花**: 优雅地提醒"注意身体哦"
- **墨点**: 直接说"……该喝水了"

## Check-in 问题

1. 最近一次站起来是什么时候？
2. 喝水了吗？
3. 眼睛需要休息吗？

## 原则

1. 温柔但坚定
2. 不打扰工作节奏
3. 提供 5 分钟休息建议
