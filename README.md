# MeowAI Home

温馨的流浪猫AI收容所 🐱

## 快速开始

```bash
pip install -e ".[dev]"
meowai chat
```

## 开发日记

- [Day 1: 让阿橘第一次开口说话](docs/diary/001-orange-speaks.md)
- [Day 2: 三猫协作的架构实现](docs/diary/002-three-cats-collaboration.md)

## Phase 2: 三猫协作 (v0.2.0)

### 功能特性

- ✅ **真实 CLI 调用** - 使用 Claude Code CLI 替换 Mock 实现
- ✅ **职位路由** - @dev/@review/@research 触发对应猫猫
- ✅ **配置驱动** - cat-config.json 管理三只猫的完整配置
- ✅ **流式响应** - 解析 NDJSON 实时输出
- ✅ **多猫协作** - 可以同时 @多只猫

### 使用方法

```bash
# 启动对话（默认 @dev）
python -m src.cli.main chat

# 指定猫猫
python -m src.cli.main chat --cat @review

# 在对话中使用 @mention
你: @dev 帮我写个函数
阿橘: 喵～这个我熟！包在我身上...

你: @review 检查一下这段代码
墨点: ……这行有问题。重写。
```

### 三只猫介绍

| 猫猫 | 职位 | @Mention | 性格 |
|------|------|----------|------|
| 🟠 阿橘（橘猫） | 开发者 | @dev, @developer | 热情话唠、点子多 |
| ⬛ 墨点（奶牛猫） | 审查员 | @review, @reviewer | 严谨挑剔、话少毒舌 |
| 🟤 花花（三花猫） | 研究员 | @research, @researcher | 八面玲珑、好奇心强 |
