# Phase 10 开发日记 — 监控与可观测性 (v0.10.0)

**日期**: 2026-04-10
**角色**: 阿橘（基础设施）、墨点（审计安全）、花花（API设计）

---

## 架构决策

### 为什么自研而不是用现成方案？

阿橘："Sentry、DataDog 这些 SaaS 方案太贵，而且数据外传。我们要支持企业本地部署，必须内建可观测性。"

墨点："而且我们需要审计日志，这是合规刚需，必须自己控制数据。"

**技术选型**:
- **结构化日志**: Python 原生 logging + 自定义 JSONFormatter（无额外依赖）
- **审计日志**: 自研审计框架（22种事件类型）
- **指标**: prometheus-client（业界标准，K8s 原生支持）
- **健康检查**: 自研 HealthChecker（支持 K8s 探针）

---

## Sub-Phase 10.1: 结构化日志

### 核心设计

**问题**: 传统文本日志难以解析和查询。

**方案**:
```python
# 输出格式
{"timestamp": "2026-04-10T14:30:00", "level": "INFO", "logger": "app", "message": "started", "user_id": "123"}
```

**关键类**:
- `JSONFormatter`: 将 LogRecord 转为 JSON
- `StructuredLogger`: 支持 `logger.info("msg", key="value")` 的额外字段
- `get_logger()`: 单例工厂，避免重复配置

### 代码统计
- 1 个新文件 (`src/monitoring/logging.py`)
- 12 个测试

---

## Sub-Phase 10.2: 审计日志

### 安全事件全覆盖

墨点："审计日志不是普通日志，它是安全证据链。每条记录必须包含：谁在什么时间对什么资源做了什么操作。"

**AuditEventType** (22种):
- **认证**: `auth.login`, `auth.logout`, `auth.failed`, `auth.refresh`
- **权限**: `permission.check`, `permission.denied`
- **数据**: `data.access`, `data.create`, `data.update`, `data.delete`
- **配置**: `config.change`
- **Agent**: `agent.register`, `agent.deregister`, `agent.update`
- **技能**: `skill.install`, `skill.uninstall`, `skill.execute`
- **Pack**: `pack.activate`, `pack.deactivate`
- **工作流**: `workflow.start`, `workflow.complete`, `workflow.cancel`
- **MCP**: `mcp.tool_call`, `mcp.tool_error`

**使用示例**:
```python
audit = get_audit_logger()
audit.auth_login(user_id="user123", success=True, ip_address="192.168.1.1")
audit.data_access(user_id="user123", action="read", resource_type="memory", resource_id="mem_abc")
```

### 代码统计
- 1 个新文件 (`src/monitoring/audit.py`)
- 22 个测试

---

## Sub-Phase 10.3: Prometheus 指标

### 12 类指标设计

花花："Prometheus 是云原生的事实标准，Grafana 可以直接对接。"

**指标清单**:

| 类别 | 指标 | 类型 | 说明 |
|------|------|------|------|
| HTTP | `http_requests_total` | Counter | 按 method/endpoint/status 统计 |
| HTTP | `http_request_duration_seconds` | Histogram | P50/P95/P99 延迟 |
| A2A | `a2a_messages_total` | Counter | 消息处理计数 |
| A2A | `a2a_active_invocations` | Gauge | 当前活跃调用数 |
| Agent | `agent_invocations_total` | Counter | Agent 调用计数 |
| Agent | `agent_tokens_total` | Counter | Token 消耗统计 |
| Thread | `threads_active` | Gauge | 活跃会话数 |
| Skill | `skill_executions_total` | Counter | 技能执行计数 |
| Workflow | `workflows_active` | Gauge | 活跃工作流数 |
| Workflow | `workflow_nodes_executed` | Histogram | 每工作流节点数分布 |
| Memory | `memory_operations_total` | Counter | 记忆层操作计数 |
| MCP | `mcp_tool_calls_total` | Counter | 工具调用计数 |

**Timer 工具**:
```python
# 上下文管理器
with Timer(collector.http_request_duration, "GET", "/api/test"):
    process_request()

# 装饰器
@timed("skill_execution_duration", skill_name="tdd")
async def execute_skill():
    pass
```

### 代码统计
- 1 个新文件 (`src/monitoring/metrics.py`)
- 18 个测试
- 新增依赖: `prometheus-client>=0.19.0`

---

## Sub-Phase 10.4: 健康检查 API

### K8s 原生支持

阿橘："企业部署用 Kubernetes，必须支持 livenessProbe 和 readinessProbe。"

**探针端点**:
- `GET /api/monitoring/health/live` — Liveness（进程存活）
- `GET /api/monitoring/health/ready` — Readiness（可接受流量）
- `GET /api/monitoring/health` — 完整健康状态

**组件检查**:
- **database**: SQLite 连通性检查
- **memory**: 内存使用率（>90% 为 Degraded）
- **disk**: 磁盘使用率（>90% 为 Degraded）
- **custom**: 支持注册用户自定义检查

**状态分级**:
- `HEALTHY` — 所有检查通过
- `DEGRADED` — 有警告但可用（如内存高）
- `UNHEALTHY` — 有组件失败

**返回示例**:
```json
{
  "status": "healthy",
  "version": "0.10.0",
  "uptime_seconds": 3600,
  "components": [
    {"name": "database", "status": "healthy", "latency_ms": 2.5, "message": "Database connection OK"},
    {"name": "memory", "status": "healthy", "latency_ms": 1.0, "message": "Memory usage: 45%"}
  ]
}
```

### API 端点汇总

| 端点 | 说明 |
|------|------|
| `GET /api/monitoring/health` | 完整健康状态 |
| `GET /api/monitoring/health/live` | K8s liveness |
| `GET /api/monitoring/health/ready` | K8s readiness |
| `GET /api/monitoring/status` | 详细系统状态 |
| `GET /api/monitoring/metrics` | Prometheus 指标 |

### 代码统计
- 2 个新文件 (`src/monitoring/health.py`, `src/web/routes/monitoring.py`)
- 28 个测试

---

## 测试

| 类别 | 数量 | 状态 |
|------|------|------|
| 现有测试 | 641 | ✅ 通过 |
| 结构化日志 | 12 | ✅ 通过 |
| 审计日志 | 22 | ✅ 通过 |
| Prometheus | 18 | ✅ 通过 |
| 健康检查 | 28 | ✅ 通过 |
| **总计** | **721** | **✅ 100%** |

---

## 运行方式

### 查看指标
```bash
# 健康检查
curl http://localhost:8000/api/monitoring/health

# Prometheus 指标
curl http://localhost:8000/api/monitoring/metrics

# 详细状态
curl http://localhost:8000/api/monitoring/status
```

### Kubernetes 配置示例
```yaml
livenessProbe:
  httpGet:
    path: /api/monitoring/health/live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /api/monitoring/health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Grafana 集成
1. 添加 Prometheus 数据源: `http://meowai:8000/api/monitoring/metrics`
2. 导入 dashboard（提供模板 `grafana-dashboard.json`）

---

## 监控清单完成

- [x] 结构化日志 (JSON)
- [x] 审计日志 (22 事件类型)
- [x] Prometheus 指标 (12 类)
- [x] 健康检查 API (K8s 探针)
- [x] REST API 端点 (5 个)

*Phase 10 完成！MeowAI Home 现在拥有企业级可观测性基础设施。* 🎯
