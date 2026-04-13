---
name: deep-research
description: >
  多源深度调研管道（Web + Coder 合成）。
  Use when: 技术问题需要多源调查、设计决策需要证据。
  Not for: 简单搜索（直接用 WebSearch）。
  Output: 调研报告 + 证据合成。
triggers:
  - "调研"
  - "research"
  - "深度研究"
next: ["collaborative-thinking"]
---

# Deep Research — 深度调研

> 参考: MeowAI Home deep-research skill

## 调研流程

1. **定义问题**: 明确调研目标和关键问题
2. **多源搜索**: Web 搜索 + 文档查阅 + 代码分析
3. **证据收集**: 每个来源标注可靠性等级
4. **合成报告**: 汇总证据，给出结论和建议

## 报告模板

```markdown
# 调研报告: {主题}

## 问题
{调研的核心问题}

## 来源
1. {来源1} — 可靠性: 高/中/低
2. {来源2} — 可靠性: 高/中/低

## 发现
1. {发现1}
2. {发现2}

## 结论
{基于证据的结论}

## 建议
1. {行动建议}
```
