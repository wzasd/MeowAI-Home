# Phase 7: 高级协作与工作流系统 (v0.7.0) — 开发日记

> **日期**: 2026-04-09 ~ 2026-04-10
> **主角**: 布偶猫(宪宪)、缅因猫(砚砚)、暹罗猫(烁烁)

---

## 序章: 四座孤岛

Phase 6 结束后，三只猫看着项目状态报告，陷入了沉默。

宪宪指着屏幕说："我们 Phase 6 做了 12 个模块——CatRegistry、AgentRegistry、AgentRouterV2、SessionChain、InvocationTracker、StreamMerge——但是，WebSocket 活跃流程里一个都没接入。"

砚砚推了推眼镜："是的。它们就像建好的桥梁，两端都没连上路。AgentRouterV2 存在但没人用它；SessionChain 记录 session 但没人写进去；InvocationTracker 追踪 invocation 但没人启动它。"

烁烁跳到键盘上："还有 A2AController——333 行，路由、执行、MCP、技能注入全混一起。每次改一个地方都得看半天。"

宪宪叹了口气："所以 Phase 7 的第一件事：把桥接上。"

## 第一步: 建桥

三只猫分头行动：

**砚砚** 负责 DAG 引擎——工作流的核心。
- `WorkflowDAG` 数据结构，支持拓扑排序和环检测
- `DAGExecutor` 按层并行执行，同一层的节点同时跑
- `ResultAggregator` 三种聚合模式：merge / last / summarize
- `WorkflowTemplateFactory` 三个预定义模板 + YAML 自定义

**烁烁** 负责辅助类提取——让 A2AController 瘦身。
- `MCPExecutor` — 工具注册和回调执行，从 A2AController 里剥离
- `SkillInjector` — 技能上下文注入，用 lambda 包装替换原始方法

**宪宪** 负责接入层——把孤岛连起来。
- AgentRouterV2 替换 v1（支持中文/日文 @mention）
- InvocationTracker 接入 WebSocket（新消息自动取消旧 invocation）
- SessionChain 接入 _call_cat（CLI session 复用，3 次失败自动 seal）
- IntentParser 扩展 workflow 检测（#brainstorm、#parallel、#autoplan）

## 第二步: 三种工作流模板

三只猫坐在一起设计工作流模板。

**头脑风暴模板**：多只猫并行思考，最后一只猫汇总。

```
用户消息 → [阿橘思考] ──┐
          [墨点思考] ──→ [汇总猫] → 最终结果
          [斑点思考] ──┘
```

**并行分工模板**：每只猫负责不同部分，最后合并。

```
用户消息 → [阿橘做前端] ──┐
          [墨点做后端] ──→ [合并猫] → 完整交付
          [斑点写测试] ──┘
```

**LLM 自动规划模板**：让一只猫当规划者，分析任务后输出 JSON DAG 定义，系统自动执行。

```
用户消息 → [规划猫] → 输出 JSON DAG → 系统执行 → 最终结果
```

烁烁问："如果规划猫输出的 JSON 解析失败怎么办？"

宪宪说："降级为 brainstorm 模板，不会卡住。"

砚砚补充："这叫优雅降级——参考项目 Clowder AI 也是这个思路。"

## 第三步: 并行施工

三只猫决定用子代理并行开发——6 个独立模块同时开工。

砚砚管理调度：Tasks 1-4（核心引擎）、Tasks 5-6（辅助类）、Tasks 7-8（重构）、Tasks 9-10（接入层），总共 10 个子代理同时执行。

**问题是文件冲突**——多个代理可能同时写同一个文件。

砚砚的解决方案："每个代理只创建自己负责的文件，不碰别人的。需要依赖的模块，把完整代码内嵌在 prompt 里。"

结果是：10 个代理全部成功，只有 `__init__.py` 的导出需要最后手动补全。

## 实施完成

**11 个 Task 全部完成：**

| 子阶段 | Tasks | 状态 |
|--------|-------|------|
| 7.1 核心引擎 | 1-4 (DAG、聚合器、模板、执行器) | ✅ |
| 7.2 辅助类 | 5-6 (MCPExecutor、SkillInjector) | ✅ |
| 7.3 重构 | 7-8 (A2AController、IntentParser) | ✅ |
| 7.4 接入 | 9-11 (RouterV2、WebSocket、回归) | ✅ |

**新增文件**: 12 Python 源文件 + 8 测试文件
**修改文件**: 7 个
**测试**: 318 → 367（+49 新测试），全绿
**A2AController**: 333 行 → ~180 行（-46%）

---

*三只猫看着 367 个全绿的测试结果，宪宪伸了个懒腰说："桥接上了，路通了。"*
