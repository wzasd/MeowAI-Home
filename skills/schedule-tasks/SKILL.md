---
name: schedule-tasks
description: >
  定时任务注册、管理、能力指南。
  Use when: 设定时任务、定期提醒、周期巡检。
  Not for: 一次性即时操作。
  Output: 注册/管理定时任务。
triggers:
  - "定时"
  - "每天"
  - "每小时"
  - "提醒我"
  - "remind me"
  - "schedule"
  - "cron"
  - "定期"
  - "定时任务"
next: ["rich-messaging"]
---

# Schedule Tasks — 定时任务

> 参考: MeowAI Home schedule-tasks skill

## Cron 表达式

```
分 时 日 月 星期
* * * * *

常用:
*/5 * * * *     — 每5分钟
0 * * * *       — 每小时
0 9 * * 1-5     — 工作日早9点
0 0 1 * *       — 每月1号
```

## 注册流程

1. 解析用户意图 → cron 表达式
2. 注册任务到调度器
3. 返回任务 ID 和下次执行时间

## 管理

- `list`: 查看所有定时任务
- `cancel {id}`: 取消任务
- `update {id} {cron}`: 更新执行时间
