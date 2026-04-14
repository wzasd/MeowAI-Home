# Phase 2: 执行层补齐 + 真实指标采集 + 治理持久化

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 capabilities/permissions/governance 真正生效，建立真实指标采集管线，治理项目列表持久化到 SQLite。

**Architecture:** 
- Prompt 层：`src/providers/base.py` 的 `build_system_prompt()` 注入 capabilities/permissions/iron_laws
- Dispatch 层：`src/collaboration/capability_map.py` + `A2AController` 根据任务类型匹配 capability，不匹配则拒绝
- Tool 层：`src/collaboration/permission_guard.py` 拦截高风险 MCP 工具调用
- Metrics：`src/metrics/collector.py` + `src/metrics/sqlite_store.py` 在调用链路中插桩采集
- Governance：`governance_projects` SQLite 表替换内存字典

**Tech Stack:** Python 3.10+, FastAPI, SQLite, Pydantic, React + Zustand

---

## File Map

| File | Responsibility |
|------|----------------|
| `src/collaboration/capability_map.py` | capability → 任务类型映射表 |
| `src/collaboration/permission_guard.py` | 高风险工具与 permission 的拦截规则 |
| `src/providers/base.py` | `build_system_prompt()` 注入 caps/perms |
| `src/collaboration/a2a_controller.py` | 调用 capability 检查 + metrics 采集点 |
| `src/metrics/collector.py` | `MetricsCollector` 接口（start/finish） |
| `src/metrics/sqlite_store.py` | `invocation_metrics` 表操作 |
| `src/web/routes/metrics.py` | `GET /api/metrics/cats` 和 `/api/metrics/leaderboard` |
| `src/web/routes/governance.py` | 改为 SQLite 持久化 |
| `src/web/app.py` | 注册新增 routes |
| `web/src/components/settings/GovernanceSettings.tsx` | 从 SQLite 读写项目列表 |
| `web/src/components/settings/QuotaBoard.tsx` | 从真实 API 加载数据 |
| `web/src/components/settings/Leaderboard.tsx` | 从真实 API 加载数据 |
| `tests/collaboration/test_capability_map.py` | capability 映射测试 |
| `tests/collaboration/test_permission_guard.py` | permission 拦截测试 |
| `tests/metrics/test_collector.py` | metrics 采集测试 |
| `tests/web/test_metrics.py` | metrics API 测试 |

---

## Task 1: Capability Map + Permission Guard

**Files:**
- Create: `src/collaboration/capability_map.py`
- Create: `tests/collaboration/test_capability_map.py`
- Create: `src/collaboration/permission_guard.py`
- Create: `tests/collaboration/test_permission_guard.py`

### capability_map.py

```python
from typing import List, Optional

CAPABILITY_TASK_MAP = {
    "chat": ["general", "conversation"],
    "code": ["implement", "write_code", "refactor", "debug"],
    "code_review": ["review", "audit", "inspect"],
    "research": ["research", "design", "brainstorm"],
    "shell_exec": ["execute_command", "run_script"],
    "file_write": ["write_file", "edit_file", "delete_file"],
    "git_ops": ["git_commit", "git_push", "git_branch"],
}


def get_task_type(intent: str, mentions: List[str]) -> str:
    """根据 intent 和 mention 推断任务类型"""
    intent_lower = intent.lower()
    if any(k in intent_lower for k in ("review", "audit", "check")):
        return "review"
    if any(k in intent_lower for k in ("research", "find", "look up", "design")):
        return "research"
    if any(k in intent_lower for k in ("write", "code", "implement", "refactor", "debug")):
        return "implement"
    if any(k in intent_lower for k in ("run", "execute", "command", "shell")):
        return "execute_command"
    return "general"


def required_capabilities_for_task(task_type: str) -> List[str]:
    """返回执行某任务类型所需的 capability 列表"""
    caps = []
    for cap, tasks in CAPABILITY_TASK_MAP.items():
        if task_type in tasks:
            caps.append(cap)
    return caps


def cat_can_handle(cat_capabilities: List[str], task_type: str) -> bool:
    """检查猫的 capabilities 是否覆盖任务类型"""
    required = required_capabilities_for_task(task_type)
    if not required:
        return True
    return any(r in cat_capabilities for r in required)
```

### permission_guard.py

```python
from typing import List

HIGH_RISK_TOOLS = {
    "execute_command": ["shell_exec"],
    "delete_file": ["file_write"],
    "write_file": ["file_write"],
    "git_push": ["git_ops"],
    "edit_file": ["file_write"],
}


def check_permission(cat_permissions: List[str], tool_name: str) -> bool:
    """检查猫是否有权限调用指定工具"""
    if tool_name not in HIGH_RISK_TOOLS:
        return True
    required = HIGH_RISK_TOOLS[tool_name]
    return any(r in cat_permissions for r in required)


def get_missing_permission(tool_name: str) -> Optional[str]:
    """返回缺失的 permission 建议"""
    if tool_name not in HIGH_RISK_TOOLS:
        return None
    return HIGH_RISK_TOOLS[tool_name][0]
```

### Tests

- `test_capability_map.py`: `test_get_task_type_review`, `test_required_capabilities`, `test_cat_can_handle`, `test_general_task_no_requirement`
- `test_permission_guard.py`: `test_low_risk_allowed`, `test_execute_command_requires_shell_exec`, `test_missing_permission_hint`

---

## Task 2: Provider Base build_system_prompt() 注入

**Files:**
- Modify: `src/providers/base.py`

在 `BaseProvider`（或等价的 Agent base class）中修改/新增 `build_system_prompt()` 方法，将 cat 的 `capabilities` 和 `permissions` 注入 system prompt。

```python
def build_system_prompt(self, extra_context: str = "") -> str:
    """Build system prompt with capabilities and permissions injected."""
    parts = []
    if extra_context:
        parts.append(extra_context)
    
    caps = getattr(self.config, "capabilities", []) or []
    perms = getattr(self.config, "permissions", []) or []
    
    if caps:
        parts.append(f"你的能力范围：{', '.join(caps)}。超出能力范围的任务请明确拒绝。")
    if perms:
        parts.append(f"你的操作权限：{', '.join(perms)}。没有权限的操作禁止执行。")
    
    return "\n\n".join(parts)
```

如果 `src/providers/base.py` 中已有 `build_system_prompt` 或 `build_env`，在其实现上追加。

---

## Task 3: A2AController 集成 Capability 检查

**Files:**
- Modify: `src/collaboration/a2a_controller.py`

在 `_dispatch()` 或调用 service 之前插入 capability 检查逻辑：

```python
from src.collaboration.capability_map import get_task_type, cat_can_handle

# Inside _call_cat or dispatch logic:
task_type = get_task_type(intent.clean_message, [agent["breed_id"] for agent in agents])
cat_capabilities = getattr(cat_config, "capabilities", []) or []
if not cat_can_handle(cat_capabilities, task_type):
    yield AgentMessage(
        type=AgentMessageType.TEXT,
        content=f"🚫 {cat_config.display_name} 没有 `{task_type}` 相关能力，无法处理该任务。",
        cat_id=cat_id,
        is_final=True,
    )
    return
```

---

## Task 4: MetricsCollector + SQLite Store

**Files:**
- Create: `src/metrics/collector.py`
- Create: `src/metrics/sqlite_store.py`
- Create: `tests/metrics/test_collector.py`

### collector.py

```python
import time
from typing import Optional
from dataclasses import dataclass

from src.metrics.sqlite_store import MetricsSQLiteStore


@dataclass
class InvocationRecord:
    cat_id: str
    thread_id: Optional[str]
    project_path: Optional[str]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    success: bool = True
    duration_ms: int = 0


class MetricsCollector:
    """调用指标采集器"""

    def __init__(self, store: MetricsSQLiteStore = None):
        self._store = store or MetricsSQLiteStore()
        self._starts: dict[str, float] = {}

    def record_start(self, invocation_id: str) -> None:
        self._starts[invocation_id] = time.time()

    def record_finish(self, invocation_id: str, record: InvocationRecord) -> None:
        start = self._starts.pop(invocation_id, None)
        if start:
            record.duration_ms = int((time.time() - start) * 1000)
        try:
            self._store.save(record)
        except Exception:
            pass
```

### sqlite_store.py

```python
import aiosqlite
from pathlib import Path
from typing import List, Optional

from src.metrics.collector import InvocationRecord

DEFAULT_DB_PATH = Path.home() / ".meowai" / "meowai.db"

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS invocation_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    cat_id TEXT NOT NULL,
    thread_id TEXT,
    project_path TEXT,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    success INTEGER DEFAULT 1,
    duration_ms INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_metrics_cat ON invocation_metrics(cat_id);
CREATE INDEX IF NOT EXISTS idx_metrics_project ON invocation_metrics(project_path);
CREATE INDEX IF NOT EXISTS idx_metrics_time ON invocation_metrics(timestamp);
"""


class MetricsSQLiteStore:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db: Optional[aiosqlite.Connection] = None

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            await self._db.executescript(_INIT_SQL)
        return self._db

    async def save(self, record: InvocationRecord) -> None:
        import time
        db = await self._get_db()
        await db.execute(
            """
            INSERT INTO invocation_metrics
            (timestamp, cat_id, thread_id, project_path, prompt_tokens, completion_tokens, success, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                time.time(),
                record.cat_id,
                record.thread_id,
                record.project_path,
                record.prompt_tokens,
                record.completion_tokens,
                1 if record.success else 0,
                record.duration_ms,
            ),
        )
        await db.commit()

    async def list_by_cat(self, cat_id: str, days: Optional[int] = None) -> List[dict]:
        db = await self._get_db()
        sql = "SELECT * FROM invocation_metrics WHERE cat_id = ?"
        params = [cat_id]
        if days:
            import time
            sql += " AND timestamp >= ?"
            params.append(time.time() - days * 86400)
        sql += " ORDER BY timestamp DESC"
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [_row_to_dict(row) for row in rows]

    async def leaderboard(self, days: Optional[int] = None) -> List[dict]:
        db = await self._get_db()
        sql = """
            SELECT cat_id,
                   COUNT(*) as total_calls,
                   SUM(prompt_tokens) as total_prompt_tokens,
                   SUM(completion_tokens) as total_completion_tokens,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_calls,
                   AVG(duration_ms) as avg_duration_ms
            FROM invocation_metrics
        """
        params = []
        if days:
            import time
            sql += " WHERE timestamp >= ?"
            params.append(time.time() - days * 86400)
        sql += " GROUP BY cat_id ORDER BY total_calls DESC"
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [
            {
                "cat_id": row[0],
                "total_calls": row[1],
                "prompt_tokens": row[2] or 0,
                "completion_tokens": row[3] or 0,
                "success_rate": (row[4] or 0) / row[1] if row[1] else 1.0,
                "avg_duration_ms": row[5] or 0,
            }
            for row in rows
        ]


def _row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "timestamp": row[1],
        "cat_id": row[2],
        "thread_id": row[3],
        "project_path": row[4],
        "prompt_tokens": row[5],
        "completion_tokens": row[6],
        "success": bool(row[7]),
        "duration_ms": row[8],
    }
```

### test_collector.py

- `test_record_start_finish`
- `test_save_and_query`
- `test_leaderboard_aggregation`

---

## Task 5: A2AController 插桩 Metrics

**Files:**
- Modify: `src/collaboration/a2a_controller.py`

在 `_call_cat()` 中：

1. 生成唯一 invocation_id（可用 `f"{thread.id}:{cat_id}:{time.time()}"`）
2. `metrics_collector.record_start(invocation_id)`
3. 调用结束后计算 token usage（优先从返回的 `AgentMessage.usage`，否则按 content 字节 `/ 4` 估算）
4. `metrics_collector.record_finish(invocation_id, InvocationRecord(...))`

确保 `MetricsCollector` 初始化在 `A2AController.__init__` 中可传入，默认新建实例。

---

## Task 6: Metrics API

**Files:**
- Create/Modify: `src/web/routes/metrics.py`
- Modify: `src/web/app.py` 注册 route

```python
from fastapi import APIRouter, Query
from typing import Optional

from src.metrics.sqlite_store import MetricsSQLiteStore

router = APIRouter()
store = MetricsSQLiteStore()


@router.get("/api/metrics/cats")
async def get_cat_metrics(cat_id: str, days: Optional[int] = Query(default=7)):
    rows = await store.list_by_cat(cat_id, days=days if days > 0 else None)
    return {"cat_id": cat_id, "days": days, "data": rows}


@router.get("/api/metrics/leaderboard")
async def get_leaderboard(days: Optional[int] = Query(default=7)):
    rows = await store.leaderboard(days=days if days > 0 else None)
    return {"days": days, "leaderboard": rows}
```

---

## Task 7: Governance SQLite 持久化

**Files:**
- Modify: `src/web/routes/governance.py`
- Create: `tests/web/test_governance.py`

把现有的 governance 路由（如有）从内存 dict 改为 SQLite 表 `governance_projects`。如果没有现成路由，新建如下：

```python
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import aiosqlite
import json
import time
from pathlib import Path

router = APIRouter()
DB_PATH = Path.home() / ".meowai" / "meowai.db"


class GovernanceProject(BaseModel):
    project_path: str
    status: str = "healthy"
    version: Optional[str] = None
    findings: List[str] = []
    confirmed: bool = False


async def _ensure_table():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS governance_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_path TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'healthy',
                version TEXT,
                findings TEXT DEFAULT '[]',
                synced_at REAL,
                confirmed INTEGER DEFAULT 0
            )
        """)
        await db.commit()


@router.get("/api/governance/projects")
async def list_projects() -> dict:
    await _ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT * FROM governance_projects ORDER BY synced_at DESC")
        rows = await cursor.fetchall()
    return {
        "projects": [
            {
                "id": row[0],
                "project_path": row[1],
                "status": row[2],
                "version": row[3],
                "findings": json.loads(row[4] or "[]"),
                "synced_at": row[5],
                "confirmed": bool(row[6]),
            }
            for row in rows
        ]
    }


@router.post("/api/governance/projects")
async def add_project(payload: GovernanceProject):
    await _ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO governance_projects (project_path, status, version, findings, synced_at, confirmed)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_path) DO UPDATE SET
                status = excluded.status,
                version = excluded.version,
                findings = excluded.findings,
                synced_at = excluded.synced_at,
                confirmed = excluded.confirmed
            """,
            (
                payload.project_path,
                payload.status,
                payload.version,
                json.dumps(payload.findings),
                time.time(),
                1 if payload.confirmed else 0,
            ),
        )
        await db.commit()
    return {"success": True}


@router.delete("/api/governance/projects/{project_path:path}")
async def delete_project(project_path: str):
    await _ensure_table()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM governance_projects WHERE project_path = ?", (project_path,))
        await db.commit()
    return {"success": True}
```

---

## Task 8: 前端 QuotaBoard / Leaderboard 切换真实数据

**Files:**
- Modify: `web/src/components/settings/QuotaBoard.tsx`
- Modify: `web/src/components/settings/Leaderboard.tsx`
- Modify: `web/src/api/client.ts`

在 `client.ts` 新增：

```typescript
  metrics: {
    cat: (catId: string, days?: number) =>
      request<{ cat_id: string; days: number; data: any[] }>(`/api/metrics/cats?cat_id=${catId}&days=${days ?? 7}`),
    leaderboard: (days?: number) =>
      request<{ days: number; leaderboard: any[] }>(`/api/metrics/leaderboard?days=${days ?? 7}`),
  },
  governance: {
    listProjects: () => request<{ projects: any[] }>("/api/governance/projects"),
    addProject: (data: { project_path: string; status?: string; version?: string; findings?: string[]; confirmed?: boolean }) =>
      request<{ success: boolean }>("/api/governance/projects", { method: "POST", body: JSON.stringify(data) }),
    deleteProject: (projectPath: string) =>
      request<{ success: boolean }>(`/api/governance/projects/${encodeURIComponent(projectPath)}`, { method: "DELETE" }),
  },
```

前端组件：
- `QuotaBoard`: 用 `api.metrics.cat(selectedCat, days)` 替换 mock data
- `Leaderboard`: 用 `api.metrics.leaderboard(days)` 替换 mock data，支持 days 切换（7/30/all）

---

## Task 9: GovernanceSettings 对接 SQLite

**Files:**
- Modify: `web/src/components/settings/GovernanceSettings.tsx`

把 GovernanceSettings 中的项目列表从本地 state/mock 改为：

1. `useEffect` 中调用 `api.governance.listProjects()` 加载
2. 新增项目时 `POST /api/governance/projects`
3. 删除项目时 `DELETE /api/governance/projects/{path}`
4. 操作成功后重新拉取列表

---

## Task 10: Phase 2 集成验证

- [ ] 运行全部新增测试：`pytest tests/collaboration/test_capability_map.py tests/collaboration/test_permission_guard.py tests/metrics/test_collector.py tests/web/test_governance.py tests/web/test_metrics.py -v`
- [ ] 运行后端测试套件：`pytest tests/ -q --no-header`（仅接受 pre-existing 失败）
- [ ] Python `py_compile` 检查所有新增/修改文件
- [ ] 写 Phase 2 完成日记到 `docs/diary/`
- [ ] Commit

---

## Self-Review

**Spec coverage:**
- capability/permission/governance 三层防御 → Tasks 1-3 ✅
- 真实指标采集 → Tasks 4-6 ✅
- Governance 持久化 → Task 7 ✅
- 前端切换真实数据 → Tasks 8-9 ✅

**Placeholder scan:** No TBD/TODO/"implement later" ✅
