# NeowAI Phase 1 完成日记

**日期:** 2026-04-14

## 概述

完成 NeowAI 项目猫窝（Nest）Phase 1 的全部 9 个任务，实现 `.neowai/` 初始化、CLAUDE.md 区块注入、Thread `project_path` 必填以及 provider `cwd` 透传。

## 已交付内容

### Task 1: NestConfig Pydantic Model + 自动修正
- `src/config/nest_config.py`: `NestConfig` 模型，支持 `fix_config`、`load_nest_config`、`save_nest_config`
- `tests/config/test_nest_config.py`: 8 个测试覆盖默认值、fix 行为、JSON 解析错误、校验回退等场景

### Task 2: NestRegistry 全局项目索引
- `src/config/nest_registry.py`: 管理 `~/.meowai/nest-index.json`，支持注册/注销/查询
- `tests/config/test_nest_registry.py`: 6 个测试覆盖增删改查、幂等注册、损坏 JSON 恢复

### Task 3: ClaudeMdWriter
- `src/cli/claude_md_writer.py`: `NEOWAI-CATS-START/END` 区块读写，支持追加、替换、备份
- `tests/cli/test_claude_md_writer.py`: 7 个测试覆盖全部操作路径

### Task 4: neowai CLI 智能初始化
- `src/cli/nest_init.py`: `run_nest_init` 根据当前目录智能初始化或显示项目状态
- `tests/cli/test_nest_init.py`: 3 个测试覆盖全新初始化、重复初始化、无可用 cats
- `src/cli/main.py`: 无参数时默认调用 `run_nest_init()`

### Task 5-7: cwd 透传
- `src/models/types.py`: `InvocationOptions` 新增 `cwd` 字段
- 4 个 provider (`claude`, `codex`, `gemini`, `opencode`) 将 `cwd` 传入 `spawn_cli`
- `src/collaboration/a2a_controller.py`: `_call_cat` 使用 `thread.project_path` 作为 `cwd`
- `src/web/routes/ws.py`: 发送消息前校验 `thread.project_path` 存在

### Task 8: Thread `project_path` 必填 + 前端适配
- 后端: `schemas.py`、`thread/models.py`、`thread_manager.py`、`sqlite_store.py` 统一要求 `project_path`
- 前端: `ThreadSidebar` 新增创建表单，含对话名称、cat 选择器、项目目录路径输入
- 类型: `client.ts`、`threadStore.ts`、`types/index.ts` 同步更新

### Task 9: 集成验证
- 新测试: 37/37 passed
- `py_compile`: 全部通过
- 后端测试套件: 仅有 pre-existing 失败（缺失 fixture、SOCKS 代理环境）
- TypeScript: `node_modules` 未安装，无法运行 `tsc`，属 pre-existing 环境问题

## 提交记录

```
08f05d0 feat: make project_path required for Thread creation + frontend integration
798c735 feat: pass cwd through InvocationOptions, providers, and A2AController
886b647 fix: nest_init CLI 代码质量审查问题修复
7dd88df fix: nest_init CLI 测试与冗余调用修复
6ec59cd feat: neowai CLI smart init with CLAUDE.md block injection
6acaa8f feat: ClaudeMdWriter for NEOWAI-CATS block injection
c289a04 feat: NestRegistry for global activated project index
6472ba6 feat: NestConfig Pydantic model with validation and auto-fix
```

## 下一步

Phase 2: capabilities/permissions/governance 三层实际执行 + metrics 采集管线实现。
