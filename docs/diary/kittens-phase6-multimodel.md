# Phase 6: 多模型支持 (v0.6.0) — 开发日记

> **日期**: 2026-04-09
> **主角**: 布偶猫(宪宪)、缅因猫(砚砚)、暹罗猫(烁烁)

---

## 序章: 为什么不用 SDK？

今天宪宪在调研多模型架构方案时，分析了一个关键架构决策：**ADR-001**。有意思的是，最初选择了 SDK 直连（方案 A），但经过评估后改成了 CLI 子进程（方案 B）。

**原因很简单——钱。**

砚砚推了推眼镜说："用户已经订阅了 Claude Max、ChatGPT Plus、Gemini Advanced。用 SDK 就得再用 API Key 付费，等于花两份钱。CLI 工具原生支持 OAuth 订阅认证，直接读本地凭据文件，不花一分钱。"

烁烁跳起来说："还有一个原因！CLI 工具不只是聊天——它们有完整的 Agent 能力！文件操作、命令执行、MCP 工具调用，这些 SDK 都没有。用 SDK 的话，这些全得自己写。"

宪宪点头："对，还有进程隔离。CLI 子进程崩了不影响主进程，SDK 是在进程内调用，崩了全崩。而且 CLI 可以独立更新，不需要重新部署后端。"

三只猫达成共识：**采用 CLI 子进程模式。**

## 架构决策记录

已写入 `docs/decisions/001-cli-as-backend.md`。

核心决策：
- **CLI 子进程 + NDJSON 解析** 而非 Python SDK
- 每个 Provider 独立 Service 实现
- 统一 `invoke()` AsyncGenerator 接口
- 双注册表: CatRegistry（配置）+ AgentRegistry（服务实例）
- 配置级联: env > cat-config.json > 硬编码默认值

## Phase 6 完整实施范围

多模型架构包含以下核心模块：

| 模块 | 目标 | 当前状态 |
|------|----------|-----------|
| Provider 适配器 | 5个独立 Service | 3个基础 Service |
| AgentRegistry | 动态注册表 | 无 |
| CatRegistry | 全局配置注册 | 无（直接读 JSON） |
| AgentRouter | @mention + intent 路由 | 已有基础版 |
| AccountResolver | subscription/api_key 模式 | 无 |
| Context Budget | token 预算管理 | 无 |
| anthropic-proxy | 第三方网关代理 | 无 |
| CLI Spawn | 统一进程管理 | 基础版 |
| Hot-Reload | 配置热更新 | 无 |
| Session Chain | 会话链管理 | 无 |

接下来将逐一实现。

---

*三只猫看着满屏的架构图，深吸一口气，开始干活了。*

---

## 实施完成

**16 个 Task 全部完成：**

| 子阶段 | Tasks | 状态 |
|--------|-------|------|
| 6.1 基础设施 | 1-7 (Types, CatRegistry, AgentRegistry, CLI Spawn, Providers, 集成) | ✅ |
| 6.2 配置系统 | 8-10 (Budget, Model Resolver, Account Resolver) | ✅ |
| 6.3 高级路由 | 11 (AgentRouterV2) | ✅ |
| 6.4 会话管理 | 12-14 (Session Chain, Stream Merge, Tracker) | ✅ |
| 6.5 企业特性 | 15-16 (Anthropic Proxy, 集成测试) | ✅ |

**新增文件**: 30+ Python 源文件 + 测试
**测试覆盖**: 全量通过 (300+ tests)
**向后兼容**: Phase 1-5 功能不受影响

---

*宪宪、砚砚、烁烁看着完整的多模型架构，终于松了一口气。*
