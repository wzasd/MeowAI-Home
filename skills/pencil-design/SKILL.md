---
name: pencil-design
description: >
  使用 Pencil MCP 创建/编辑 .pen 设计文件，或导出为 React 代码。
  Use when: 设计 UI、编辑 .pen 文件、从设计稿生成代码。
  Not for: 纯代码实现（无设计稿）。
  Output: .pen 设计文件或 React/Tailwind 组件代码。
triggers:
  - "pencil"
  - ".pen 文件"
  - "设计稿"
requires_mcp:
  - "pencil"
next: []
---

# Pencil Design — Pencil 设计

> 参考: Clowder AI pencil-design skill

## 流程

1. **创建设计**: 用 Pencil MCP 创建 .pen 文件
2. **编辑布局**: 拖拽组件、调整样式
3. **导出代码**: .pen → React + Tailwind 组件

## 适用场景

- UI 设计稿
- 布局原型
- 组件视觉规范

## 注意

- 需要 Pencil MCP 已配置
- 导出代码需人工 review
