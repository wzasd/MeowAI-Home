---
name: browser-automation
description: >
  浏览器工作流总路由：外部网站浏览、登录态流程、浏览器自动化。
  Use when: 需要操作外部网站、登录页、JS 重页面。
  Not for: localhost 页面预览（用 browser-preview）。
  Output: 选定浏览器后端 + 执行路径 + 证据/结果。
triggers:
  - "浏览器自动化"
  - "用浏览器"
  - "外部网站"
  - "登录网站"
requires_mcp:
  - "playwright"
next: []
---

# Browser Automation — 浏览器自动化

> 参考: Clowder AI browser-automation skill

## 流程

1. **分析需求**: 确定需要浏览器操作的场景
2. **选择后端**: Playwright MCP / Chrome MCP
3. **执行操作**: 导航、点击、截图、填表
4. **收集证据**: 截图/数据保存

## 适用场景

- 外部网站浏览
- 登录态流程
- JS 重页面数据采集
- 需要浏览器渲染的页面

## 注意

- 需要 Playwright MCP 已配置
- localhost 预览请用 browser-preview
