---
date: 2026-04-21
doc_kind: diary
topics: ["tool", "chat", "ui", "ux", "copywriting"]
---

# Tool 展示格式 V2

这轮不是继续加功能，而是先把 Tool 展示的“说话方式”收紧。

当前落地已经有可见性，但还有明显工程感：

- live 态像工具卡，不像过程提示
- raw tool name 太技术
- 持久化块太像 CLI 日志

所以新稿把结构改成两层：

- **Action Strip**：直播态只有一句动作句，例如“正在读 tool-visibility-rail.md”
- **Action Receipt**：落库后是一条可展开的动作回执，而不是 terminal 风格输出块

重点不是加更多字段，而是先把已有字段翻译成用户读得懂的产品语言。

产物：

- `docs/design/2026-04-21-tool-visibility-format-v2.md`
- `docs/design/tool-visibility-format-v2.html`
- `docs/design/assets/tool-visibility-format-v2.png`
