# MeowAI Home Phase 2 设计文档：三猫协作

**Created**: 2026-04-08
**Status**: Draft
**Owner**: 首席铲屎官

---

## 目录

1. [项目目标](#1-项目目标)
2. [架构设计](#2-架构设计)
3. [配置系统](#3-配置系统)
4. [核心组件](#4-核心组件)
5. [实施计划](#5-实施计划)
6. [测试策略](#6-测试策略)
7. [技术决策](#7-技术决策)

---

## 1. 项目目标

### 1.1 Phase 2 核心目标

让三只流浪猫真正开口说话，实现基于职位的多猫协作。

### 1.2 功能范围

- ✅ **真实 CLI 调用** - 使用 Claude Code CLI 替换 Mock 实现
- ✅ **职位路由** - @dev/@review/@research 触发对应猫猫
- ✅ **配置驱动** - cat-config.json 管理三只猫的完整配置
- ✅ **流式响应** - 解析 NDJSON 实时输出
- ✅ **临时文件管理** - 通过临时文件传递 system prompt

### 1.3 不在范围内

- ❌ MCP 回调机制（Phase 3）
- ❌ 会话持久化和恢复（Phase 3）
- ❌ 复杂的协作工作流（Phase 3）

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────┐
│                    CLI 用户输入                      │
│         python -m src.cli.main chat                 │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              CLI Main (src/cli/main.py)              │
│  - 解析命令行参数                                    │
│  - 识别 @Mentions（@dev/@review/@research）         │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│         Agent Router (src/router/agent_router.py)   │
│  - 根据 mention 选择对应的猫（职位优先）             │
│  - 加载 cat-config.json                             │
│  - 管理 service 实例缓存                            │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│OrangeService │ │ InkyService  │ │ PatchService │
│  (阿橘)       │ │  (墨点)       │ │  (花花)       │
│  @dev         │ │  @review      │ │  @research    │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        ▼
              ┌──────────────────┐
              │  Claude CLI      │
              │  --output-format │
              │  stream-json     │
              │  --append-system │
              │  -prompt-file    │
              └──────────────────┘
```

### 2.2 数据流

```
用户输入 "@dev 帮我写代码"
    │
    ├─ CLI 解析
    │   └─ 提取 mention: "dev"
    │
    ├─ Router 路由
    │   ├─ 职位映射: dev -> orange
    │   ├─ 加载配置: cat-config.json
    │   └─ 创建/获取 OrangeService
    │
    ├─ Service 处理
    │   ├─ 构建 system prompt（性格+角色）
    │   ├─ 创建临时文件（system_prompt.txt）
    │   ├─ 调用 Claude CLI
    │   │   claude --output-format stream-json \
    │   │          --append-system-prompt-file /tmp/orange_xxx.txt \
    │   │          "帮我写代码"
    │   └─ 解析 NDJSON 流式输出
    │
    └─ 返回结果
        └─ 阿橘: "喵～这个我熟！包在我身上..."
```

---

## 3. 配置系统

### 3.1 cat-config.json 结构

```json
{
  "version": 2,
  "breeds": [
    {
      "id": "orange",
      "name": "橘猫",
      "displayName": "阿橘",
      "roles": ["developer", "coder", "implementer"],
      "mentionPatterns": [
        "@dev", "@developer", "@coder",
        "@阿橘", "@orange", "@橘猫"
      ],
      "roleDescription": "主力开发者，全能型选手",
      "personality": "热情话唠、点子多、有点皮但靠谱",
      "catchphrases": ["这个我熟！", "包在我身上！"],
      "cli": {
        "command": "claude",
        "outputFormat": "stream-json",
        "defaultArgs": ["--output-format", "stream-json"]
      }
    },
    {
      "id": "inky",
      "name": "奶牛猫",
      "displayName": "墨点",
      "roles": ["reviewer", "auditor", "inspector"],
      "mentionPatterns": [
        "@review", "@reviewer", "@audit",
        "@墨点", "@inky", "@奶牛猫"
      ],
      "roleDescription": "代码审查员，专抓 bug",
      "personality": "严谨挑剔、话少毒舌、内心温柔",
      "catchphrases": ["……这行有问题。", "重写。"],
      "cli": {
        "command": "claude",
        "outputFormat": "stream-json",
        "defaultArgs": ["--output-format", "stream-json"]
      }
    },
    {
      "id": "patch",
      "name": "三花猫",
      "displayName": "花花",
      "roles": ["researcher", "designer", "creative"],
      "mentionPatterns": [
        "@research", "@researcher", "@design",
        "@花花", "@patch", "@三花猫"
      ],
      "roleDescription": "研究/创意助手，收集信息和出点子",
      "personality": "八面玲珑、好奇心强、爱收集信息",
      "catchphrases": ["我打听到的消息是…", "要不要试试这个？"],
      "cli": {
        "command": "claude",
        "outputFormat": "stream-json",
        "defaultArgs": ["--output-format", "stream-json"]
      }
    }
  ]
}
```

### 3.2 配置字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | string | 品种唯一标识 | `"orange"` |
| `name` | string | 猫的品种名 | `"橘猫"` |
| `displayName` | string | 显示名称 | `"阿橘"` |
| `roles` | string[] | 职位列表（用于路由） | `["developer", "coder"]` |
| `mentionPatterns` | string[] | 触发模式（职位+名称） | `["@dev", "@阿橘"]` |
| `roleDescription` | string | 角色描述 | `"主力开发者"` |
| `personality` | string | 性格设定 | `"热情话唠"` |
| `catchphrases` | string[] | 口头禅 | `["这个我熟！"]` |
| `cli.command` | string | CLI 命令 | `"claude"` |
| `cli.outputFormat` | string | 输出格式 | `"stream-json"` |
| `cli.defaultArgs` | string[] | 默认参数 | `["--output-format", "stream-json"]` |

---

## 4. 核心组件

### 4.1 CatConfigLoader（配置加载器）

**职责**：加载和管理 cat-config.json 配置

**关键方法**：
```python
class CatConfigLoader:
    def load() -> Dict[str, Any]
    def get_breed(breed_id: str) -> Dict[str, Any]
    def get_breed_by_mention(mention: str) -> Optional[Dict[str, Any]]
    def list_breeds() -> list
```

**设计要点**：
- 单例模式，避免重复加载
- 缓存配置，提升性能
- 支持按职位和名称两种方式查找

---

### 4.2 AgentRouter（路由器）

**职责**：解析 @mention 并路由到对应的 AgentService

**职位映射表**：
```python
ROLE_TO_BREED = {
    # 开发相关 -> 橘猫
    "developer": "orange",
    "coder": "orange",
    "implementer": "orange",

    # 审查相关 -> 奶牛猫
    "reviewer": "inky",
    "audit": "inky",
    "inspector": "inky",

    # 研究/设计 -> 三花猫
    "researcher": "patch",
    "designer": "patch",
    "creative": "patch",
}
```

**路由流程**：
1. 解析消息中的 @mentions
2. 先尝试职位匹配（ROLE_TO_BREED）
3. 再尝试 mentionPatterns 匹配
4. 返回对应的 breed 配置

**Service 缓存**：
```python
self._services = {}  # breed_id -> service instance

def get_service(breed_id):
    if breed_id not in self._services:
        # 创建新实例并缓存
        self._services[breed_id] = create_service(breed_id)
    return self._services[breed_id]
```

---

### 4.3 AgentService 基类

**职责**：定义 Agent 服务的统一接口

```python
class AgentService(ABC):
    def __init__(self, breed_config: Dict[str, Any]):
        self.config = breed_config
        self.name = breed_config["displayName"]
        self.personality = breed_config["personality"]
        self.catchphrases = breed_config.get("catchphrases", [])
        self.cli_config = breed_config["cli"]

    def build_system_prompt() -> str:
        """构建系统提示词"""
        # 拼接性格、角色、口头禅

    @abstractmethod
    async def chat(message: str, system_prompt: Optional[str] = None) -> str:
        """同步获取完整回复"""

    @abstractmethod
    async def chat_stream(message: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
        """流式获取回复"""
```

---

### 4.4 OrangeService（阿橘服务）

**真实 CLI 调用实现**：

```python
async def chat_stream(message: str, system_prompt: Optional[str] = None):
    # 1. 构建 system prompt
    if system_prompt is None:
        system_prompt = self.build_system_prompt()

    # 2. 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', suffix='.txt', delete=False
    )
    temp_file.write(system_prompt)
    temp_file.close()

    try:
        # 3. 构建 CLI 命令
        cmd = self.cli_config["command"]
        args = self.cli_config["defaultArgs"].copy()
        args.extend([
            "--append-system-prompt-file", temp_file.name,
            message
        ])

        # 4. 执行 CLI
        result = await run_cli_command(
            command=cmd, args=args, timeout=300.0
        )

        # 5. 解析 NDJSON
        async for event in parse_ndjson_stream(result["stdout"]):
            if event.get("type") == "assistant":
                # 提取文本内容
                for block in event["message"]["content"]:
                    if block["type"] == "text":
                        yield block["text"]
    finally:
        # 6. 清理临时文件
        os.unlink(temp_file.name)
```

**临时文件管理**：
- 使用 `tempfile.NamedTemporaryFile` 创建
- `delete=False` 确保在关闭后仍可访问
- `finally` 块确保清理

---

### 4.5 CLI Main（主入口）

**交互式对话**：

```python
@cli.command()
@click.option('--cat', default='@dev', help='默认对话的猫猫')
def chat(cat: str):
    router = AgentRouter()

    click.echo(f"🐱 正在启动与 {cat} 的对话...")

    while True:
        message = click.prompt("你", type=str)

        # 如果没有 @mention，添加默认的
        if '@' not in message:
            message = f"{cat} {message}"

        # 路由消息
        results = asyncio.run(router.route_message(message))

        # 显示结果
        for result in results:
            click.echo(f"\n{result['name']}: {result['response']}\n")
```

---

## 5. 实施计划

### 5.1 任务清单

| Task | 描述 | 优先级 | 预估时间 |
|------|------|--------|----------|
| Task 1 | 创建 cat-config.json | P0 | 30 分钟 |
| Task 2 | 实现配置加载器 | P0 | 1 小时 |
| Task 3 | 实现真实 OrangeService | P0 | 2 小时 |
| Task 4 | 实现 AgentRouter | P0 | 1.5 小时 |
| Task 5 | 更新 CLI 主入口 | P0 | 1 小时 |
| Task 6 | 创建 InkyService 和 PatchService | P1 | 1 小时 |
| Task 7 | 集成测试 | P0 | 1.5 小时 |
| Task 8 | Day 2 开发日记 | P1 | 1 小时 |
| Task 9 | 最终集成和 v0.2.0 标签 | P0 | 30 分钟 |

**总预估时间**：~10 小时

### 5.2 依赖关系

```
Task 1 (cat-config.json)
  │
  ├─→ Task 2 (ConfigLoader) ─→ Task 4 (Router)
  │                              │
  └─→ Task 3 (OrangeService) ────┤
                                 │
                                 └─→ Task 5 (CLI Main)
                                       │
                                       └─→ Task 6 (Inky/Patch)
                                             │
                                             └─→ Task 7 (集成测试)
                                                   │
                                                   └─→ Task 8 (日记)
                                                         │
                                                         └─→ Task 9 (v0.2.0)
```

---

## 6. 测试策略

### 6.1 单元测试

**ConfigLoader 测试**：
- ✅ 加载配置文件成功
- ✅ 按 breed_id 获取配置
- ✅ 按 mention 获取配置（职位）
- ✅ 按 mention 获取配置（名称）
- ✅ 处理配置不存在的情况

**Router 测试**：
- ✅ 解析单个 @mention
- ✅ 解析多个 @mention
- ✅ 职位到品种映射
- ✅ 名称到品种映射
- ✅ Service 缓存机制

**NDJSON 解析测试**：
- ✅ 解析单行 JSON
- ✅ 解析多行 JSON
- ✅ 处理空行
- ✅ 处理格式错误

### 6.2 集成测试

**OrangeService 真实调用**：
- ✅ 调用 Claude CLI 成功
- ✅ 解析流式输出
- ✅ 临时文件创建和清理
- ✅ 超时处理

**多猫协作测试**：
- ✅ 单猫对话
- ✅ 多猫 @mention
- ✅ 默认猫猫选择

### 6.3 测试配置

**Mock 配置**（tests/fixtures/cat-config-test.json）：
```json
{
  "breeds": [
    {
      "id": "orange",
      "cli": {
        "command": "echo",
        "defaultArgs": []
      }
    }
  ]
}
```

使用 `echo` 命令替代真实 CLI，避免依赖外部环境。

---

## 7. 技术决策

### 7.1 ADR-001: System Prompt 传递方式

**决策**：使用临时文件 + `--append-system-prompt-file`

**备选方案**：
- ❌ CLI 参数（`--append-system-prompt`）：长度限制、转义复杂
- ❌ stdin 传递：不确定 Claude CLI 是否支持
- ✅ 临时文件：无长度限制、稳定可靠、官方支持

**理由**：
1. Claude Code CLI 明确支持 `--append-system-prompt-file`
2. System prompt 可能很长（性格、规则等）
3. 避免命令行参数长度限制
4. 实现简单，易于调试

**性能影响**：写 1KB 临时文件 < 1ms，相比 CLI 启动开销（500ms-2s）可忽略

---

### 7.2 ADR-002: 路由策略

**决策**：职位优先 + 名称兼容

**理由**：
1. 职位是稳定的（developer/reviewer/researcher）
2. 名称可随时修改，不影响路由逻辑
3. 符合实际使用习惯（按功能找人）
4. 保持灵活性（仍支持名称调用）

**示例**：
```bash
@dev 帮我写代码      # 职位调用（推荐）
@阿橘 这个我熟！      # 名称调用（兼容）
```

---

### 7.3 ADR-003: Service 实例缓存

**决策**：在 Router 中缓存 Service 实例

**理由**：
1. 避免重复创建实例
2. 临时文件跟踪和清理
3. 未来可扩展连接池等优化

**实现**：
```python
self._services = {}  # breed_id -> service

def get_service(breed_id):
    if breed_id not in self._services:
        self._services[breed_id] = create_service(breed_id)
    return self._services[breed_id]
```

---

## 8. 风险与缓解

### 8.1 CLI 调用风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| CLI 未配置 | 无法调用 | 检测 `claude` 命令是否存在 |
| 超时 | 长时间等待 | 设置 5 分钟超时 + 用户提示 |
| 输出格式变化 | 解析失败 | 容错解析 + 版本锁定 |
| 僵尸进程 | 资源泄漏 | `run_cli_command` 已处理 |

### 8.2 临时文件风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 磁盘空间 | 临时文件堆积 | `finally` 块清理 |
| 并发冲突 | 文件名冲突 | `NamedTemporaryFile` 自动唯一命名 |
| 权限问题 | 无法写入 | 使用系统临时目录 |

---

## 9. 成功标准

### 9.1 功能验收

- ✅ `@dev` 路由到阿橘
- ✅ `@review` 路由到墨点
- ✅ `@research` 路由到花花
- ✅ 名称调用仍有效（`@阿橘`）
- ✅ 真实 CLI 调用成功
- ✅ 流式输出正常
- ✅ 临时文件自动清理

### 9.2 质量标准

- ✅ 所有单元测试通过（10+ 测试）
- ✅ 所有集成测试通过（5+ 测试）
- ✅ 代码覆盖率 > 80%
- ✅ 无 P0/P1 级别 bug

### 9.3 文档标准

- ✅ Day 2 开发日记完成
- ✅ README 更新（三猫使用说明）
- ✅ 代码注释完整

---

## 10. 未来规划（Phase 3+）

### 10.1 Phase 3 预告

- 会话持久化和恢复
- MCP 回调机制（猫猫主动发言）
- Thread 管理（多会话）
- 复杂协作工作流

### 10.2 长期优化

- 进程池（复用 CLI 进程）
- 流式输出实时渲染（Rich 库）
- Web UI 界面
- 语音交互

---

**文档结束**

*本文档将随项目演进而持续更新。*
