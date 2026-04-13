# MeowAI Home 项目规范

## 开发原则

### 参考与原创
- 参考其他项目时**禁止**在代码、文档、日志、日记中提及来源项目名称
- 参考后必须进行**架构反思**：该设计是否适合我们的技术栈、规模和场景
- 在参考基础上鼓励**创新改进**，不照搬
- 参考内容必须**脱敏**：不复制原始代码、配置、文案，只借鉴思路和模式
- 所有设计决策应表述为"团队讨论/分析后决定"，而非"参考了 X"

### 代码质量
- 所有新功能必须有对应测试
- Python 代码通过 `py_compile` 检查
- TypeScript 代码通过 `tsc --noEmit` 检查
- 提交信息用中英文混合，描述 what 和 why

### 文档规范
- 开发日记写到 `docs/diary/`，每次重大更新都要记录
- 计划文档写到 `docs/superpowers/plans/`
- ROADMAP 中的状态标记必须反映**实际代码状态**，不允许标注已完成但代码不存在

## 技术栈
- 后端: Python 3.9+, FastAPI, SQLite + FTS5
- 前端: React 19 + TypeScript + Tailwind CSS + Zustand + Vite
- 测试: pytest (后端), vitest (前端)
- 部署: Docker Compose

## 项目结构
- `src/` — Python 后端源码
- `web/src/` — React 前端源码
- `skills/` — 技能定义文件 (SKILL.md)
- `docs/` — 文档和日记
- `tests/` — 后端测试
- `scripts/` — 工具脚本
