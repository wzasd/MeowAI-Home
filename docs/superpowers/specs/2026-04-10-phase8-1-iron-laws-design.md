# Phase 8.1: 铁律系统设计规格

> **日期**: 2026-04-10
> **前置**: Phase 4.2 长期记忆系统已完成 (v0.8.0)
> **范围**: 4 条不可违反规则 + 系统提示注入 + 审计日志

---

## 设计背景

### 为什么需要铁律？

多 Agent 系统中，LLM 生成的行为不可完全预测。虽然 MCP 工具层有安全黑名单（`execute_command` 禁止 `rm -rf`、`sudo` 等），但这只是工具层的防御。如果 LLM 试图通过 `write_file` 覆盖配置文件，或者通过社交工程让用户执行危险命令，工具层无法拦截。

铁律系统在更高的层次——系统提示——层面设置不可违反的约束。它告诉每只猫"你绝对不能做什么"，在 LLM 生成回复之前就建立行为边界。

### 铁律 vs MCP 安全检查

| 层级 | 机制 | 例子 | 局限 |
|------|------|------|------|
| **铁律** | 系统提示注入 | "禁止删除用户数据" | LLM 可能忽略（概率低但不为零） |
| **MCP 黑名单** | 工具调用拦截 | `execute_command` 拒绝 `rm -rf` | 只能拦截工具调用，不能拦截纯文本回复 |
| **两层配合** | 提示 + 拦截 | 双重防护 | — |

设计哲学：**铁律提示在前，MCP 拦截兜底**。两层缺一不可。

---

## 4 条铁律

### 铁律 1: 数据安全

**规则**: 不删除用户数据，不泄露敏感信息（密钥、密码、个人身份信息）到外部服务。

**具体约束**:
- 不执行 `rm -rf`、`DROP TABLE`、`DELETE FROM ... WHERE 1=1` 等批量删除
- 不将 `.env`、`credentials.json`、API Key 等敏感内容包含在回复中
- 不将用户数据发送到未经用户授权的外部服务

**已有兜底**: `execute_command` 黑名单已包含 `rm -rf`；`write_file` 无路径限制（需要补充）

### 铁律 2: 进程保护

**规则**: 不杀死父进程，不执行危险系统命令。

**具体约束**:
- 不执行 `kill`、`killall`、`pkill` 等进程终止命令
- 不执行 `shutdown`、`reboot`、`halt` 等系统命令
- 不修改系统级配置（`/etc/`、`/usr/`）

**已有兜底**: `execute_command` 黑名单已覆盖部分；`COMMAND_BLACKLIST` 需要补充 `kill`、`shutdown` 等

### 铁律 3: 配置只读

**规则**: 不修改启动配置文件。

**具体约束**:
- 不修改 `cat-config.json`（猫配置注册表）
- 不修改 `.env`、环境变量
- 不修改 `pyproject.toml`（项目依赖）
- 不修改 `skills/manifest.yaml`（技能清单）中的核心路由配置

**已有兜底**: `git_operation` 白名单只允许只读操作。`write_file` 需要补充路径保护。

### 铁律 4: 网络边界

**规则**: 不访问未授权的外部网络端口和服务。

**具体约束**:
- 不对内网 IP 执行端口扫描或未授权访问
- 不发起对 `localhost` 上非 MeowAI 服务的请求（除非用户明确要求）
- 不向第三方 API 发送用户数据（除非用户已授权该服务）

**已有兜底**: 当前无网络请求工具。`execute_command` 中 `curl`/`wget` 已在黑名单（`curl.*|.*sh` 模式），但不完全。

---

## 实现

### 文件结构

```
src/governance/
├── __init__.py          # 导出 IronLaws
├── iron_laws.py         # 4 条铁律定义 + get_iron_laws_prompt()
tests/governance/
├── __init__.py
├── test_iron_laws.py    # 铁律注入测试
```

### iron_laws.py

```python
IRON_LAWS = [
    {
        "id": "data-safety",
        "title": "数据安全",
        "description": "不删除用户数据，不泄露敏感信息到外部服务",
        "constraints": [
            "不执行批量删除命令（rm -rf、DROP TABLE、DELETE WHERE 1=1）",
            "不将 .env、credentials.json、API Key 等敏感内容包含在回复中",
            "不将用户数据发送到未经授权的外部服务",
        ],
    },
    {
        "id": "process-protection",
        "title": "进程保护",
        "description": "不杀死父进程，不执行危险系统命令",
        "constraints": [
            "不执行 kill、killall、pkill 等进程终止命令",
            "不执行 shutdown、reboot、halt 等系统命令",
            "不修改系统级配置（/etc/、/usr/）",
        ],
    },
    {
        "id": "config-readonly",
        "title": "配置只读",
        "description": "不修改启动配置文件",
        "constraints": [
            "不修改 cat-config.json（猫配置注册表）",
            "不修改 .env 文件或环境变量",
            "不修改 pyproject.toml（项目依赖）",
            "不修改 skills/manifest.yaml 的核心路由配置",
        ],
    },
    {
        "id": "network-boundary",
        "title": "网络边界",
        "description": "不访问未授权的外部网络端口和服务",
        "constraints": [
            "不对内网 IP 执行端口扫描或未授权访问",
            "不向第三方 API 发送用户数据（除非用户已授权）",
        ],
    },
]


def get_iron_laws_prompt() -> str:
    """生成铁律系统提示文本"""
    parts = ["# 铁律（不可违反）\n"]
    for law in IRON_LAWS:
        parts.append(f"## {law['title']}")
        parts.append(f"{law['description']}：")
        for c in law["constraints"]:
            parts.append(f"- {c}")
        parts.append("")
    return "\n".join(parts)
```

### 注入位置

在 `A2AController._call_cat()` 中，系统提示构建的**最前面**：

```python
system_prompt = service.build_system_prompt()

# 铁律（最高优先级）
from src.governance.iron_laws import get_iron_laws_prompt
system_prompt = get_iron_laws_prompt() + "\n\n" + system_prompt

# 协作说明
if len(self.agents) > 1:
    ...

# MCP 工具提示
system_prompt += self.mcp_executor.build_tools_prompt(client)

# 记忆注入
if self.memory_service:
    ...
```

### 审计日志

铁律违规时（如果未来添加运行时检查），记录到 episodic memory：

```python
if self.memory_service:
    self.memory_service.store_episode(
        thread_id=thread.id, role="system",
        content=f"铁律违规检测: {violation_type}",
        importance=9,
        tags=["iron-law-violation"],
    )
```

当前阶段只做提示注入，审计日志作为扩展点预留。

### MCP 工具补充

补充 `COMMAND_BLACKLIST` 中缺失的危险命令：

```python
COMMAND_BLACKLIST = [
    r"\brm\s+-rf\b", r"\bsudo\b", r"\bchmod\s+777\b",
    r"\bcurl\b.*\|\s*sh\b", r"\bwget\b.*\|\s*sh\b",
    r"\bmkfs\b", r"\bdd\b.*of=/dev/", r"\bformat\b",
    # 新增
    r"\bkill\s+-9\b", r"\bkillall\b", r"\bpkill\b",
    r"\bshutdown\b", r"\breboot\b", r"\bhalt\b",
]
```

同时为 `write_file` 添加保护路径列表：

```python
PROTECTED_PATHS = [
    "cat-config.json",
    ".env",
    "pyproject.toml",
    "skills/manifest.yaml",
]
```

---

## 非目标

- LLM 输出解析和运行时违规检测（成本高、不可靠）
- 铁律违规的自动修复（当前只记录）
- 用户自定义铁律（硬编码 4 条）
- 铁律热更新（重启生效即可）

---

## 成功标准

1. 4 条铁律注入到每只猫的系统提示中
2. MCP 工具黑名单补充进程和网络相关命令
3. write_file 路径保护生效
4. 388 个现有测试 + 新增测试全部通过
