---
name: rich-messaging
description: >
  富媒体消息发送：语音、图片、卡片、清单、代码 diff。
  Use when: 发语音、发图、发卡片、展示结构化信息。
  Not for: 纯文字聊天。
  Output: rich block 附着在消息上。
triggers:
  - "发语音"
  - "发图"
  - "发个卡片"
  - "checklist"
  - "庆祝一下"
  - "给我看看"
next: []
---

# Rich Messaging — 富媒体消息

> 参考: Clowder AI rich-messaging skill

## 支持类型

| 类型 | 说明 | 触发词 |
|------|------|--------|
| **Audio** | 语音消息 | 发语音、给我听听 |
| **Image** | 图片展示 | 发图、给我看看 |
| **Card** | 结构化卡片 | 发个卡片 |
| **Checklist** | 待办清单 | checklist、清单 |
| **Diff** | 代码变更展示 | show diff |

## 使用方式

直接说触发词，猫猫会自动选择合适的 rich block 类型。
