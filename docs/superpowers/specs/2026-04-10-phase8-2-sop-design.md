# Phase 8.2: SOP 工作流设计规格

> **日期**: 2026-04-10
> **前置**: Phase 8.1 铁律系统已完成
> **范围**: 3 个 SOP 模板（TDD/代码审查/部署发布）+ 质量门禁

---

## 设计背景

Phase 7 已实现轻量 DAG 工作流引擎（`src/workflow/`），支持 `brainstorm`/`parallel`/`auto_plan` 三种模板。Phase 8.2 在此基础上新增 3 个 SOP（标准操作流程）模板，并引入质量门禁机制。

### SOP vs 普通工作流

| 维度 | 普通工作流（Phase 7） | SOP 工作流（Phase 8.2） |
|------|---------------------|----------------------|
| 触发 | `#brainstorm` 等标签 | `#tdd`、`#review`、`#deploy` 标签 |
| 流程 | 灵活的 DAG 拓扑 | 固定的标准化步骤 |
| 门禁 | 无 | 每步有通过条件 |
| 目的 | 协作效率 | 流程合规 + 质量保证 |

---

## 3 个 SOP 模板

### SOP 1: TDD 开发流程

触发: `#tdd` 标签

```
用户需求 → [写测试] → [实现] → [重构] → 完成
              ↓           ↓
           门禁:测试存在  门禁:测试通过
```

步骤:
1. **写测试** — 第一只猫根据需求生成测试用例
2. **实现** — 第二只猫写最小实现让测试通过
3. **重构** — 第三只猫（或同一只）优化代码，保持测试通过

门禁:
- Step 1 → Step 2: 测试文件存在且包含 `test_` 函数
- Step 2 → Step 3: `run_tests` 工具返回通过

### SOP 2: 代码审查流程

触发: `#review` 标签

```
代码 → [审查者1] → [审查者2] → [合并检查] → 完成
          ↓            ↓
       门禁:无阻断问题  门禁:无高危问题
```

步骤:
1. **审查者 1** — 第一只猫审查代码（安全性、正确性）
2. **审查者 2** — 第二只猫审查代码（性能、可维护性）
3. **合并检查** — 汇总审查结果

门禁:
- Step 1 → Step 2: 无 "阻断"（blocking）问题
- Step 2 → Step 3: 无高危问题

### SOP 3: 部署发布流程

触发: `#deploy` 标签

```
发布请求 → [运行测试] → [构建检查] → [发布说明] → 完成
              ↓            ↓
           门禁:全通过    门禁:无安全告警
```

步骤:
1. **运行测试** — 执行全部测试
2. **构建检查** — 检查依赖、安全扫描
3. **发布说明** — 生成 changelog

门禁:
- Step 1 → Step 2: 测试全部通过
- Step 2 → Step 3: 无安全告警

---

## 质量门禁

### 设计

质量门禁是 SOP 步骤之间的通过条件。在 DAG 执行中，门禁作为前置检查——如果前一步的结果不满足条件，后续步骤不会执行。

**实现方式**: 扩展 `DAGNode`，添加 `gate` 字段。`DAGExecutor` 在执行节点前检查前驱节点的门禁条件。

### QualityGate 数据结构

```python
@dataclass
class QualityGate:
    """质量门禁条件"""
    gate_type: str    # "test_pass" | "test_exists" | "no_blocking" | "always"
    description: str  # 门禁描述
```

### 门禁类型

| 类型 | 检查逻辑 | 用于 |
|------|---------|------|
| `test_pass` | 前驱结果包含 "passed" 且无 "failed" | TDD Step 2, 部署 Step 1 |
| `test_exists` | 前驱结果包含 "test_" 或 "assert" | TDD Step 1 |
| `no_blocking` | 前驱结果不包含 "BLOCKING" 或 "阻断" | 代码审查 |
| `always` | 总是通过（无门禁） | 默认 |

---

## 实现

### 文件结构

```
src/governance/
├── iron_laws.py          # 已有
├── sop_templates.py      # 新增: 3 个 SOP 模板
├── quality_gate.py       # 新增: 质量门禁检查
src/workflow/
├── dag.py                # 修改: DAGNode 添加 gate 字段
├── executor.py           # 修改: 执行前检查门禁
├── templates.py          # 修改: 注册 SOP 模板
```

### IntentParser 扩展

在 `WORKFLOW_TAGS` 中添加 3 个新标签：

```python
WORKFLOW_TAGS = {
    "brainstorm": "brainstorm",
    "parallel": "parallel",
    "autoplan": "auto_plan",
    # Phase 8.2: SOP 工作流
    "tdd": "tdd",
    "review": "review",
    "deploy": "deploy",
}
```

---

## 非目标

- SOP 模板的自定义编辑器
- 门禁失败的人工审批流程
- 部署到真实环境（只做模拟检查）
- 审计追踪（已有 episodic memory 记录）

---

## 成功标准

1. `#tdd`、`#review`、`#deploy` 标签触发对应 SOP 工作流
2. 质量门禁在步骤间执行检查
3. 406 个现有测试 + 新增测试全部通过
