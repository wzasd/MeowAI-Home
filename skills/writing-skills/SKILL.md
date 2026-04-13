---
name: writing-skills
description: >
  创建或修改 skill 的元技能（含 CSO、测试、发布）。
  Use when: 写新 skill、修改现有 skill、验证 skill 质量。
  Not for: 使用 skill（直接触发对应 skill）。
  Output: 新/更新的 SKILL.md + manifest 条目 + symlinks。
triggers:
  - "写 skill"
  - "新 skill"
  - "修改 skill"
  - "SKILL.md"
  - "创建 hook"
next: []
---

# Writing Skills — 编写技能

> 参考: MeowAI Home writing-skills skill

## SKILL.md 格式

```yaml
---
name: skill-name
description: >
  技能描述
  Use when: ...
  Not for: ...
  Output: ...
triggers:
  - "触发词1"
  - "触发词2"
next: ["next-skill"]
---

# 技能标题

> 简短说明

## 流程
1. 步骤1
2. 步骤2

## 模板
...
```

## 质量检查清单

- [ ] frontmatter 完整（name, description, triggers）
- [ ] description 含 Use when / Not for / Output
- [ ] triggers ≥ 2 个
- [ ] 内容有明确的流程/步骤
- [ ] 通过安全审计
