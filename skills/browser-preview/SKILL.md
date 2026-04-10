---
name: browser-preview
description: >
  内嵌浏览器预览 localhost 应用。
  Use when: 写前端代码、跑 dev server、需要看页面效果。
  Not for: 后端纯 API 开发。
  Output: 前端页面在 browser panel 中实时预览。
triggers:
  - "看效果"
  - "看看页面"
  - "preview"
  - "浏览器预览"
  - "localhost"
  - "dev server"
next: []
---

# Browser Preview — 浏览器预览

> 参考: Clowder AI browser-preview skill

## 流程

1. **确认 dev server**: 检查是否有 dev server 在运行
2. **打开预览**: 在浏览器面板中打开 localhost
3. **实时刷新**: 支持 HMR 热更新

## 适用场景

- 前端开发实时预览
- UI 调试
- 页面效果确认

## 注意

- 仅限 localhost 页面
- 外部网站请用 browser-automation
