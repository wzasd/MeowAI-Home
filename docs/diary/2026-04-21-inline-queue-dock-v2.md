---
feature_ids: []
topics: [queue, chat, composer, ui, ux]
doc_kind: diary
created: 2026-04-21
---

# Inline Queue Dock V2

今天补了一版队列区视觉稿，不再只优化“队列面板长什么样”，而是把重点转到“入队动作有没有被用户看见”。

这次的核心改动：

- 队列从独立 panel 改成输入框上沿长出的 `Send Dock`
- 第一条待发消息改成贴着输入框的主卡
- 后续队列压成纸边，只保留存在感，不抢阅读焦点
- `插队发送` 降级成危险次动作
- 让 `已放入待送区` 成为持久状态，而不是瞬时提示

产物：

- `docs/design/2026-04-21-inline-queue-dock-v2.md`
- `docs/design/inline-queue-dock-v2.html`
- `docs/design/assets/inline-queue-dock-v2.svg`
