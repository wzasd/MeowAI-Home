# Phase 4.2: 技能系统集成与扩展

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将技能系统集成到 A2A 协作流程，扩展到完整 25 个技能，实现对话中自动触发技能。

**Architecture:** 在 A2AController 中集成 ManifestRouter，根据用户消息自动匹配技能，注入技能上下文到系统提示。参考 Clowder AI 扩展到完整技能集（25个）。

**Tech Stack:** Python 3.9+, asyncio, pytest

---

## 背景

Phase 4.1 已完成技能系统框架：
- ✅ Symlink 持久化挂载
- ✅ Manifest 自动路由
- ✅ 6步安全审计
- ✅ 6个核心技能

Phase 4.2 目标：
1. 集成到 A2AController（对话中自动触发）
2. 扩展到完整 25 个技能（参考 Clowder AI）
3. 实现技能链式调用

---

## 文件结构

| 文件 | 责任 |
|------|------|
| `src/collaboration/a2a_controller.py` | 集成技能路由 |
| `src/cli/main.py` | 技能提示显示 |
| `skills/manifest.yaml` | 扩展到 25 个技能 |
| `skills/*/SKILL.md` | 新增 19 个技能 |
| `tests/collaboration/test_a2a_skill_integration.py` | 集成测试 |

---

## Task 1: A2AController 集成技能路由

**Files:**
- Modify: `src/collaboration/a2a_controller.py`
- Test: `tests/collaboration/test_a2a_skill_integration.py`

**Context:** 在 A2A 协作流程中自动触发技能。

- [ ] **Step 1: 修改 A2AController**

在 `src/collaboration/a2a_controller.py` 中添加技能路由：

```python
from src.skills.router import ManifestRouter
from src.skills.loader import SkillLoader
from pathlib import Path

class A2AController:
    """A2A 协作控制器 - 集成技能系统"""

    def __init__(self, agents: List[Dict[str, Any]]):
        self.agents = agents
        # 加载技能路由器
        manifest_path = Path("skills/manifest.yaml")
        if manifest_path.exists():
            self.skill_router = ManifestRouter(manifest_path)
            self.skill_loader = SkillLoader()
        else:
            self.skill_router = None
            self.skill_loader = None

    async def execute(
        self,
        intent: IntentResult,
        message: str,
        thread: Thread
    ) -> AsyncIterator[CatResponse]:
        """执行协作 - 支持技能路由"""

        # 检查是否有技能触发
        active_skills = []
        if self.skill_router:
            active_skills = self.skill_router.route(message)

        if active_skills:
            # 技能激活模式
            skill_id = active_skills[0]["skill_id"]  # 使用优先级最高的
            async for response in self._execute_with_skill(
                skill_id, intent, message, thread
            ):
                yield response
        else:
            # 正常协作模式
            async for response in self._execute_normal(intent, message, thread):
                yield response

    async def _execute_with_skill(
        self,
        skill_id: str,
        intent: IntentResult,
        message: str,
        thread: Thread
    ) -> AsyncIterator[CatResponse]:
        """带技能的协作执行"""

        # 加载技能内容
        skill_data = self._load_skill(skill_id)
        if not skill_data:
            # 技能加载失败，降级到正常模式
            async for response in self._execute_normal(intent, message, thread):
                yield response
            return

        # 注入技能上下文到每只猫
        for agent_info in self.agents:
            service = agent_info["service"]
            skill_context = self._build_skill_context(skill_data)
            service.add_context(skill_context)

        # 执行正常流程
        async for response in self._execute_normal(intent, message, thread):
            yield response

    def _load_skill(self, skill_id: str) -> Optional[Dict]:
        """加载技能（从 symlink）"""
        try:
            skill_path = Path.home() / ".meowai" / "skills" / skill_id
            if skill_path.exists():
                return self.skill_loader.load_skill(skill_path)
        except Exception as e:
            print(f"加载技能失败: {e}")
        return None

    def _build_skill_context(self, skill_data: Dict) -> str:
        """构建技能上下文"""
        metadata = skill_data["metadata"]
        content = skill_data["content"]

        return f"""
## 激活技能: {metadata['name']}

{metadata['description']}

{content}

---
"""
```

- [ ] **Step 2: 编写集成测试**

Create `tests/collaboration/test_a2a_skill_integration.py`:

```python
import pytest
from src.collaboration.a2a_controller import A2AController
from src.collaboration.intent_parser import parse_intent
from src.thread.models import Thread
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_agents():
    """创建模拟 agents"""
    agent1 = {
        "breed_id": "orange",
        "name": "阿橘",
        "service": MagicMock()
    }
    agent1["service"].build_system_prompt = MagicMock(return_value="你是阿橘")
    agent1["service"].chat_stream = AsyncMock(return_value=AsyncIteratorMock(["测试"]))
    agent1["service"].add_context = MagicMock()

    return [agent1]


@pytest.mark.asyncio
async def test_skill_triggered_in_a2a(mock_agents):
    """测试技能在 A2A 中触发"""
    controller = A2AController(mock_agents)

    # 用户说"写代码"，应该触发 tdd 技能
    intent = parse_intent("帮我写代码", cat_count=1)
    thread = Thread.create("Test")

    responses = []
    async for response in controller.execute(intent, "帮我写代码", thread):
        responses.append(response)

    # 验证 add_context 被调用（技能上下文注入）
    assert mock_agents[0]["service"].add_context.called


@pytest.mark.asyncio
async def test_no_skill_triggered(mock_agents):
    """测试无技能触发"""
    controller = A2AController(mock_agents)

    # 随便说说，不应该触发技能
    intent = parse_intent("随便聊聊", cat_count=1)
    thread = Thread.create("Test")

    responses = []
    async for response in controller.execute(intent, "随便聊聊", thread):
        responses.append(response)

    # 验证 add_context 没有被调用
    assert not mock_agents[0]["service"].add_context.called
```

- [ ] **Step 3: 运行测试**

```bash
pytest tests/collaboration/test_a2a_skill_integration.py -v
```

---

## Task 2: 扩展到完整 25 个技能

**Files:**
- Modify: `skills/manifest.yaml`
- Create: 19 个新的 SKILL.md

**Context:** 参考 Clowder AI 的 25 个技能，扩展完整技能集。

### 技能分类（参考 Clowder AI）

**核心开发流程 (7个)** ✅ 已完成
1. tdd
2. quality-gate
3. debugging
4. writing-plans
5. worktree
6. feat-lifecycle
7. collaborative-thinking

**协作流程 (3个)** ✅ 已完成
8. request-review
9. receive-review
10. cross-cat-handoff

**合并流程 (1个)** ✅ 已完成
11. merge-gate

**高级功能 (6个)** - 待新增
12. self-evolution
13. cross-thread-sync
14. deep-research
15. schedule-tasks
16. writing-skills
17. incident-response

**MCP 集成 (3个)** - 待新增
18. pencil-design
19. rich-messaging
20. browser-automation

**用户体验 (3个)** - 待新增
21. workspace-navigator
22. browser-preview
23. image-generation

**健康与训练营 (2个)** - 待新增
24. hyperfocus-brake
25. bootcamp-guide

- [ ] **Step 1: 更新 manifest.yaml**

在 `skills/manifest.yaml` 中添加 19 个新技能的元数据。

- [ ] **Step 2: 创建 19 个新技能**

参考 `cankao/clowder-ai-main/cat-cafe-skills/` 创建：

```bash
# 创建技能目录
mkdir -p skills/{self-evolution,cross-thread-sync,deep-research,schedule-tasks,writing-skills,incident-response,pencil-design,rich-messaging,browser-automation,workspace-navigator,browser-preview,image-generation,hyperfocus-brake,bootcamp-guide}
```

每个技能创建 `SKILL.md`，格式：

```markdown
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

# 技能内容

...
```

- [ ] **Step 3: 验证技能格式**

```bash
# 运行安全审计验证所有技能
python3 -m src.cli.main skill audit
```

---

## Task 3: CLI 技能提示优化

**Files:**
- Modify: `src/cli/main.py`

**Context:** 在对话中显示技能激活提示。

- [ ] **Step 1: 修改 chat 命令**

在 `src/cli/main.py` 的 chat 命令中添加技能提示：

```python
@cli.command()
@click.option('--cat', default=None, help='覆盖默认猫')
@click.option('--thread', 'thread_id', help='指定 thread ID')
@click.option('--resume', is_flag=True, help='恢复上次会话')
def chat(cat: str, thread_id: str, resume: bool):
    """与猫猫开始对话"""
    from src.thread import ThreadManager
    from src.skills.router import ManifestRouter
    from pathlib import Path

    manager = ThreadManager()
    router = AgentRouter()

    # 加载技能路由器
    skill_router = None
    manifest_path = Path("skills/manifest.yaml")
    if manifest_path.exists():
        skill_router = ManifestRouter(manifest_path)

    # ... 原有 thread 处理逻辑 ...

    # 显示状态
    click.echo(f"\n🐱 Thread: {thread.name} | 猫: @{get_cat_mention(cat_id)}")
    click.echo(f"   历史: {len(thread.messages)}条消息")
    click.echo("💡 提示: 使用 #ideate 多猫并行讨论, #execute 串行接力执行")

    # 显示技能提示
    if skill_router:
        installed_count = len(SymlinkManager().list_installed_skills())
        total_count = len(skill_router.list_all_skills())
        click.echo(f"📚 技能: {installed_count}/{total_count} 已安装")

    click.echo("   (按 Ctrl+C 退出)\n")

    try:
        while True:
            message = click.prompt("你", type=str)

            # 检查是否触发技能
            if skill_router:
                matches = skill_router.route(message)
                if matches:
                    skill_id = matches[0]["skill_id"]
                    skill_name = matches[0].get("name", skill_id)
                    click.echo(f"\n🎯 激活技能: {skill_name}\n")

            # ... 原有对话逻辑 ...
```

- [ ] **Step 2: 测试技能提示**

```bash
python3 -m src.cli.main chat

# 输入 "帮我写代码"，应该显示 "🎯 激活技能: TDD"
```

---

## Task 4: 技能链式调用

**Files:**
- Modify: `src/collaboration/a2a_controller.py`

**Context:** 实现技能的 `next` 字段，支持技能链。

- [ ] **Step 1: 实现技能链逻辑**

```python
class A2AController:
    def _build_skill_context(self, skill_data: Dict) -> str:
        """构建技能上下文（包含链提示）"""
        metadata = skill_data["metadata"]
        content = skill_data["content"]

        context = f"""
## 激活技能: {metadata['name']}

{metadata['description']}

{content}
"""

        # 添加技能链提示
        if "next" in skill_data and skill_data["next"]:
            next_skills = skill_data["next"]
            if isinstance(next_skills, list) and len(next_skills) > 0:
                next_skill_id = next_skills[0]
                next_skill_data = self._load_skill(next_skill_id)
                if next_skill_data:
                    next_name = next_skill_data["metadata"].get("name", next_skill_id)
                    context += f"""

**建议下一步**: 使用 `{next_name}` 技能
"""

        context += "\n---\n"
        return context
```

- [ ] **Step 2: 测试技能链**

```python
@pytest.mark.asyncio
async def test_skill_chain_hint(mock_agents):
    """测试技能链提示"""
    controller = A2AController(mock_agents)

    # tdd 技能应该包含 quality-gate 的提示
    context = controller._build_skill_context({
        "metadata": {
            "name": "TDD",
            "description": "测试驱动开发",
            "next": ["quality-gate"]
        },
        "content": "TDD 内容"
    })

    assert "建议下一步" in context
    assert "quality-gate" in context.lower()
```

---

## Task 5: 文档和测试

**Files:**
- Create: `docs/skills/README.md`
- Create: `docs/skills/creating-skills.md`
- Update: `docs/diary/kittens-phase4-2.md`

- [ ] **Step 1: 创建技能使用文档**

Create `docs/skills/README.md`:

```markdown
# MeowAI Home 技能系统

## 概述

技能系统提供 25 个专业工作流技能，通过 Symlink 持久化挂载，自动触发。

## 技能分类

### 核心开发流程 (7个)
...

### 协作流程 (3个)
...

...

## 使用方式

### 自动触发

用户说"写代码" → 自动激活 TDD 技能

### 技能链

tdd → quality-gate → request-review → receive-review → merge-gate

...
```

- [ ] **Step 2: 创建技能编写指南**

Create `docs/skills/creating-skills.md`:

```markdown
# 创建自定义技能

## SKILL.md 格式

...

## manifest.yaml 配置

...

## 最佳实践

...
```

- [ ] **Step 3: 编写开发日记**

参考 Phase 4.1 的日记格式，记录三只猫的开发过程。

---

## 实施总结

| Task | 描述 | 预估时间 |
|------|------|----------|
| 4.2.1 | A2AController 集成 | 1.5 小时 |
| 4.2.2 | 扩展到 25 个技能 | 3 小时 |
| 4.2.3 | CLI 技能提示 | 0.5 小时 |
| 4.2.4 | 技能链式调用 | 1 小时 |
| 4.2.5 | 文档和测试 | 1 小时 |

**总计**: ~7 小时

---

## 验收标准

- [ ] A2AController 集成技能路由
- [ ] 用户消息自动触发技能
- [ ] 技能上下文正确注入
- [ ] 25 个技能全部创建
- [ ] 所有技能通过安全审计
- [ ] CLI 显示技能激活提示
- [ ] 技能链提示正确显示
- [ ] 集成测试通过
- [ ] 文档完整

---

**执行选项:**

1. **Subagent-Driven (推荐)** - 每个 task 独立子代理
2. **Inline Execution** - 本会话内批量执行

选择后使用对应的 skill 开始实施。
