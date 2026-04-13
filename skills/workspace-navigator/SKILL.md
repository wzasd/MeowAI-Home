---
name: workspace-navigator
description: >
  猫猫可编程导航 Workspace 面板：模糊意图 → 找到路径 → 自动打开。
  Use when: 铲屎官说"打开日志""看看代码""帮我打开那个文档"。
  Not for: 打开 localhost 前端页面（用 browser-preview）。
  Output: Workspace 面板自动打开并导航到目标。
triggers:
  - "打开文件"
  - "看看代码"
  - "看日志"
  - "帮我打开"
  - "一起看看"
  - "帮我找到"
next: []
---

# Workspace Navigator — Workspace 导航

> 参考: MeowAI Home workspace-navigator skill

## 工作流

1. **解析意图**: 从模糊描述定位文件/目录
2. **搜索匹配**: 在项目中搜索最匹配的目标
3. **打开导航**: 自动定位到目标位置

## 示例

- "打开日志" → `logs/` 目录
- "看看代码" → `src/` 目录
- "帮我打开配置" → `config/` 或 `.env`
- "看看设计文档" → `docs/design/`

## 原则

1. 模糊匹配，给最相关的结果
2. 多个匹配时列出供选择
3. 不修改文件，只导航
