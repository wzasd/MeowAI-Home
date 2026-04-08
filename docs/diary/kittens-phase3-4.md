# 小猫开发笔记 - Phase 3.4

**日期**: 2026-04-08
**阶段**: Phase 3.4 - MCP 回调机制

---

## 阿橘的 MCP 学习笔记

喵！我们也有超能力了！可以调用工具了！

**我学到的：**

MCP = Model Context Protocol，就是猫可以调用外部工具：
- `post_message` - 主动发消息汇报进度
- `search_files` - 搜索代码文件
- `targetCats` - 告诉系统接下来谁回复

**怎么用：**

在回复里写：
```
<mcp:search_files>
{"query": "class Thread"}
</mcp:search_files>
```

系统会自动执行搜索，然后把干净内容给用户看！

**我的疑问：**

如果工具调用失败了怎么办？

铲屎官说错误会被捕获，不会影响主流程。放心用！

**TODO：**
- [ ] 学会在合适的时候调用工具
- [ ] 记住 targetCats 格式
- [ ] 测试搜索功能

**口头禅：**
> "这个工具我用得贼6！包在我身上喵～"

---

## 墨点的架构审查

……MCP 实现基本合理。

**架构检查：**

MCPClient:
- 单例模式简化实现
- 工具注册表设计清晰
- 错误隔离做得不错

Callback Parser:
- 正则匹配简单有效
- JSON 解析失败有 fallback
- 支持大小写不敏感

**问题 1：工具权限**

目前所有猫都能调用所有工具，没有权限控制。

建议：根据猫的角色限制可用工具（如 @review 不能调用某些工具）。

**问题 2：工具调用日志**

没有审计日志，无法追踪谁调用了什么工具。

**评分：** 7/10，功能完整但缺少治理。

---

## 花花的工具调研

我打听到的消息～

**轻量版 vs HTTP 版：**

| 版本 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| 轻量版 | 简单、快速、无依赖 | 不能跨进程 | 单 CLI 实例 |
| HTTP 版 | 可跨进程、可扩展 | 需要 Server | 多实例部署 |

**我们选轻量版是对的**，因为：
- 目前只有一个 CLI 实例
- 快速验证 MCP 概念
- 后续可以平滑迁移到 HTTP 版

**工具使用建议：**

| 场景 | 推荐工具 |
|------|----------|
| 需要查找代码 | search_files |
| 想主动汇报进度 | post_message |
| 想让特定猫继续 | targetCats |

---

## 三猫技术讨论会

**议题**：targetCats 能完全替代 @mention 吗？

**阿橘**：我觉得文本 @ 更简单，不用记格式。

**墨点**：……不行。文本容易出错，targetCats 是结构化数据。

**花花**：可以同时支持！双通道并存，targetCats 优先级高。

**决议**：
- Phase 1: 双通道并存，取并集
- Phase 2: targetCats 为主，@mention 为 fallback
- Phase 3: 可能完全移除 @mention

---

## 测试清单

### MCPClient 测试
- [ ] 工具注册
- [ ] 工具调用
- [ ] 错误处理
- [ ] 提示生成

### 工具测试
- [ ] post_message
- [ ] search_files
- [ ] targetCats

### 解析器测试
- [ ] 单回调
- [ ] 多回调
- [ ] 无效 JSON
- [ ] 大小写不敏感

### 集成测试
- [ ] 端到端流程
- [ ] A2A 集成
- [ ] 路由优先级

---

## 彩蛋：工具使用指南

**阿橘的私房笔记：**

```
# 搜索代码
<mcp:search_files>{"query": "def ", "path": "src"}</mcp:search_files>

# 发消息
<mcp:post_message>{"content": "进度 50%"}</mcp:post_message>

# 指定下一只猫
<mcp:targetCats>{"cats": ["inky"]}</mcp:targetCats>
```

**墨点的警告：**
> "工具调用会记录在日志里，别乱用。"

---

*Phase 3.4，让猫猫拥有超能力！*

## TODO (v0.4.0)

- [ ] 迁移到 HTTP-based MCP Server
- [ ] 支持异步工具调用
- [ ] 添加更多工具（update_task, request_permission）
- [ ] 支持外部工具注册（插件机制）
- [ ] 工具权限控制
- [ ] 审计日志
