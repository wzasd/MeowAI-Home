---
date: 2026-04-15
doc_kind: diary
topics: ["limb", "iot", "control-plane", "plan-2.4"]
---

# Limb Control Plane 补齐完成

今日完成 Plan 2.4（Limb Control Plane）全部剩余工作，实现前后端打通、测试覆盖与类型检查通过。

## 已完成内容

1. **后端路由修复与补齐**
   - `src/web/routes/limbs.py` 已包含完整的 CRUD、配对/解配对、调用、日志、租约生命周期等 14 个 REST 端点。
   - 修复路由注册顺序问题：`GET /leases` 原本排在 `GET /{device_id}` 之后，被 FastAPI 优先匹配为设备 ID，导致列表租约返回 404。将 `list_leases` 端点前移至 `get_device` 之前，问题消除。

2. **模块导出修复**
   - `src/limb/__init__.py` 补充 `DeviceCapability` 导入与 `__all__` 声明，解除 pytest 收集阶段的 `ImportError`。

3. **前后端集成**
   - `src/web/app.py` lifespan 中初始化 `LimbRegistry` 与 `LeaseManager`，并挂载 `limbs_router`。
   - `web/src/components/settings/SettingsPanel.tsx` 新增 "Limb 设备" 标签页，条件渲染 `<LimbPanel />`。

4. **前端实现**
   - `web/src/hooks/useLimbs.ts`：封装设备与租约的 fetch 逻辑。
   - `web/src/components/settings/LimbPanel.tsx`：设备注册、状态展示、配对开关、action 调用、日志查看、租约获取/释放 UI。

5. **测试覆盖**
   - 新增 `tests/web/test_limbs_api.py`，覆盖 17 个异步测试用例（设备 CRUD、配对、available 过滤、调用、日志、租约获取/延长/释放及 404 场景）。
   - 全部通过：`17 passed`。

6. **质量检查**
   - Python `py_compile` 通过。
   - 前端 `tsc --noEmit` 通过。

## 关键修复点

- **路由顺序**：FastAPI 按注册顺序匹配路径参数，静态路径（如 `/leases`、`/available`）必须注册在 `/{device_id}` 之前，否则会被吞掉。
- **Enum 导出**：`DeviceCapability` 被 `src/web/routes/limbs.py` 依赖，但未在 `src/limb/__init__.py` 中暴露，导致测试收集失败。

## 下一步

Plan 2.4 已全部完成，可继续推进 Plan 2.5 或进入后续迭代。
