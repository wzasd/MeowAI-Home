# MeowAI Home 🐱

[![Tests](https://img.shields.io/badge/tests-721%2F721-brightgreen)](./tests)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](./pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

> 🏠 **企业级多 Agent AI 协作平台** — 开源、可商用、功能完整

**MeowAI Home** 是 [Clowder AI](https://clowder.ai) 的开源替代品，支持多模型 Agent 协作、三层记忆系统、技能框架和企业级治理。

---

## ✨ 核心特性

| 特性 | 状态 | 说明 |
|------|------|------|
| 🐱 **多 Agent 协作** | ✅ | @mention 路由，并行/串行执行 |
| 🧠 **三层记忆** | ✅ | Episodic/Semantic/Procedural |
| 🎯 **技能框架** | ✅ | 25+ 技能，YAML 定义 |
| 🔧 **MCP 工具** | ✅ | 16 个标准工具 |
| 🌐 **Web UI** | ✅ | React + FastAPI，流式响应 |
| 📊 **监控告警** | ✅ | Prometheus + 健康检查 |
| 🔐 **安全审计** | ✅ | JWT + RBAC + 审计日志 |
| 🚀 **K8s 原生** | ✅ | 存活/就绪探针 |

---

## 🚀 快速开始

### Docker 一键启动

```bash
docker run -p 8000:8000 -p 5173:5173 meowai/meowai-home:latest
```

访问 http://localhost:5173

### 源码安装

```bash
git clone https://github.com/meowai/meowai-home.git
cd meowai-home
pip install -e ".[dev]"
./scripts/dev.sh
```

---

## 📊 性能指标

| 指标 | 目标 | 实际 |
|------|------|------|
| P50 响应 | < 200ms | ✅ |
| P95 响应 | < 500ms | ✅ |
| 内存占用 | < 1GB | ✅ |
| 测试覆盖 | > 90% | ✅ 100% |

---

## 🏗️ 架构

```
User → FastAPI → A2AController → Agents → Models (Claude/GPT/Gemini/...)
         ↓              ↓              ↓
    Monitoring    Workflow Engine   Memory (FTS5)
```

**技术栈**: Python 3.10+ | FastAPI | React | SQLite+FTS5 | WebSocket

---

## 📚 文档

- [快速开始](./docs/production/user/quickstart.md)
- [架构设计](./docs/production/dev/architecture.md)
- [部署指南](./docs/production/ops/docker.md)
- [API 文档](http://localhost:8000/api/monitoring/health)

---

## 🤝 贡献

欢迎 PR！请阅读 [贡献指南](./docs/production/dev/contributing.md)。

## 📄 License

MIT © MeowAI Home Team
