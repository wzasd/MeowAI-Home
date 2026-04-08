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

## Thread 多会话管理 (Phase 3.1)

支持多个独立对话线程，每个 thread 有自己的上下文历史：

```bash
# Thread 管理
meowai thread create "项目A" [--cat @dev]   # 创建 thread
meowai thread list                          # 列出 threads
meowai thread switch <id>                   # 切换 thread
meowai thread rename <id> "新名称"          # 重命名
meowai thread archive <id>                  # 归档
meowai thread delete <id> [--force]         # 删除
meowai thread info                          # 当前 thread 信息

# 对话（使用当前 thread）
meowai chat                                 # 进入交互模式
meowai chat --thread <id>                   # 使用指定 thread
```

### 特性

- **多会话管理**: 同时维护多个独立对话
- **自动保存**: 每次对话自动保存到当前 thread
- **上下文记忆**: 猫能看到 thread 中的历史对话
- **快速切换**: 在不同任务间无缝切换

## 会话持久化 (Phase 3.2)

数据存储在 SQLite 数据库 (`~/.meowai/meowai.db`)，支持：

- **自动迁移**: 从 JSON 格式自动迁移到 SQLite
- **消息搜索**: 支持内容搜索
- **会话恢复**: 快速恢复上次对话

```bash
# 恢复上次会话
meowai chat --resume

# 数据存储位置
~/.meowai/meowai.db       # SQLite 数据库
~/.meowai/threads.json    # 旧格式（自动迁移后会保留）
```

## A2A 智能协作 (Phase 3.3)

支持多猫协作模式：

```bash
# 并行讨论模式 (#ideate) - 多猫同时给出独立见解
@dev @review 这个架构怎么样？#ideate

# 串行执行模式 (#execute) - 猫按顺序接力完成
@dev @review 实现这个功能 #execute

# 批判性分析 (#critique) - 严格审查找出问题
@review 检查这段代码 #critique
```

### 自动模式选择

- **>=2 只猫**: 默认进入 `#ideate` 并行讨论
- **1 只猫**: 默认进入 `#execute` 串行执行
- **显式标签**: 使用用户指定的模式

## MCP 回调机制 (Phase 3.4)

猫可以调用外部工具，支持结构化路由：

```bash
# 猫会自动调用工具完成任务
@dev 帮我搜索 Thread 类的定义

# 结构化路由（替代 @mention）
@dev 检查这个代码
# 猫回复：<mcp:targetCats>{"cats": ["review"]}</mcp:targetCats>
# 自动路由给 @review
```

### 可用工具

| 工具 | 功能 | 示例 |
|------|------|------|
| `post_message` | 发送消息到当前 thread | 猫主动汇报进度 |
| `search_files` | 搜索项目文件 | 查找代码定义 |
| `targetCats` | 声明下一个回复的猫 | 结构化 A2A 路由 |

### 使用方式

猫在回复中嵌入工具调用：

```markdown
我来帮你搜索相关代码。

<mcp:search_files>
{"query": "class A2AController", "path": "src"}
</mcp:search_files>

找到问题了！请 @review 帮我检查。

<mcp:targetCats>
{"cats": ["inky"]}
</mcp:targetCats>
```

系统会自动：
1. 执行 `search_files` 工具
2. 解析 `targetCats` 并路由给墨点
3. 返回干净的内容给用户

### TODO (v0.4.0)

- [ ] HTTP-based MCP Server
- [ ] 异步工具调用
- [ ] 更多工具（update_task, request_permission）
- [ ] 插件机制支持外部工具注册
