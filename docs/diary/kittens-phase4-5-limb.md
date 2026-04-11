# Phase G: Limb 远程控制系统 — 实现日记

**日期:** 2026-04-11
**任务:** Limb 远程设备控制系统 (Phase G)
**范围:** G1-G4 (设备注册、权限策略、租约管理、HTTP 代理、MCP 工具)

---

## 实现概览

Phase G 实现了一套完整的远程设备控制系统，支持三级权限 (FREE/LEASED/GATED)、TTL 租约、HTTP 代理和多设备协调。

---

## 已实现模块

### G1: LimbRegistry — 设备注册中心
**文件:** `src/limb/registry.py`
- 设备注册/注销/查询
- invoke() 管线: check → policy → lease → execute → log
- 设备能力描述 (capabilities)
- 健康状态追踪

### G2: LimbAccessPolicy + LeaseManager
**文件:** `src/limb/policy.py`, `src/limb/lease.py`
- 三级权限模型:
  - `FREE`: 无需授权，直接调用
  - `LEASED`: 需获取租约，TTL 过期自动释放
  - `GATED`: 需用户显式审批
- LeaseManager:
  - TTL-based 租约，自动过期
  - 崩溃清理 (orphaned lease detection)
  - 租约续约机制
  - 每设备每用户最多 1 个活跃租约

### G3: RemoteLimbNode — HTTP 代理
**文件:** `src/limb/remote.py`
- 转发 invoke() 到设备 HTTP 端点
- 健康检查轮询 (可配置间隔)
- Bearer token 认证
- 超时和重试处理
- 异步 HTTP 调用 (httpx)

### G4: Limb MCP 工具
**文件:** `src/limb/mcp_tools.py`
- `limb_list_available` — 列出可用设备
- `limb_invoke` — 调用设备能力
- `limb_pair_list` — 列出配对请求
- `limb_pair_approve` — 审批配对请求

---

## 测试

- `tests/limb/test_registry.py` — 设备注册/注销/查询
- `tests/limb/test_policy.py` — 三级权限验证
- `tests/limb/test_lease.py` — 租约生命周期
- `tests/limb/test_remote.py` — HTTP 代理 (AsyncMock)
- 共 21+ 测试通过

---

## 使用示例

```python
from src.limb.registry import LimbRegistry
from src.limb.policy import LimbAccessPolicy, AccessLevel
from src.limb.lease import LeaseManager

# 注册设备
registry = LimbRegistry()
registry.register("printer-01", name="3D Printer", capabilities=["print", "status"])

# 配置权限
policy = LimbAccessPolicy()
policy.set_level("printer-01", AccessLevel.LEASED)

# 获取租约并调用
lease_mgr = LeaseManager()
lease = lease_mgr.acquire("printer-01", "user-1", ttl_seconds=300)
result = registry.invoke("printer-01", "print", {"file": "model.stl"}, lease=lease)
```
