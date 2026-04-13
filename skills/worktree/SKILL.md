---
name: worktree
description: >
  创建 Git worktree 隔离开发环境。
  Use when: 开始任何代码修改、新功能开发、bug fix。
  Not for: 纯文档修改（≤5 行）。
  Output: 隔离的 worktree + 正确的环境配置。
triggers:
  - "开始开发"
  - "新 worktree"
  - "开 worktree"
next: ["tdd"]
---

# Worktree — Git 工作树隔离

> 参考: MeowAI Home worktree skill

## 创建流程

```bash
# 1. 确保 main 最新
git checkout main && git pull

# 2. 创建 worktree
git worktree add .claude/worktrees/{feature-name} -b feat/{feature-name}

# 3. 进入 worktree 开发
cd .claude/worktrees/{feature-name}
```

## 清理流程

```bash
# 开发完成后
cd {project-root}
git worktree remove .claude/worktrees/{feature-name}
git branch -d feat/{feature-name}
```

## 原则

1. **一个功能一个 worktree**: 避免多个功能互相干扰
2. **命名规范**: `feat/{feature-id}` 或 `fix/{bug-id}`
3. **及时清理**: merge 后立即清理 worktree
