---
feature_ids: []
topics:
  - web-ui
  - right-panel
  - status-overview
doc_kind: diary
created: 2026-04-16
---

# 2026-04-16 状态台总览重构

## 背景

右侧状态栏原本更像几个零散数字和标签的堆叠，缺少真正的“总览层”：

- 会话、任务、队列、猫咪状态分散在不同标签里
- `总览` 页只有很浅的本地估算信息
- 重要信号没有被提炼成一眼可读的风险和态势

这次重构的目标不是继续加字段，而是把“当前发生了什么”收成一屏可扫读的信息结构。

## 这次怎么改

- 重新设计 `RightStatusPanel` 顶部壳层和 tab 区，让状态台更像一块独立战情板
- 新增 `statusOverviewModel.ts`，把总览层的聚合逻辑抽成纯函数
- 总览页改成四层结构：
  - 头部战情卡：线程、连接态、活跃会话、任务和队列摘要
  - 六宫格指标：上行、下行、缓存命中、上下文占用、当前会话、任务完成
  - 执行摘要：任务推进和队列热度双面板
  - 猫咪脉冲：每只猫当前状态、任务焦点、session/model/CLI、上下文压力
- 风险信号独立成 alerts，而不是埋在细节里
- 为总览模型补了 Node 原生测试，锁住上下文占用、任务完成率、风险提示等关键计算

## 取舍

- 没有伪造“上下文 reset 时间”之类后端暂时没有的字段，只展示当前真实可得数据
- 没有把 session 明细继续塞进总览，而是保留在 `会话` 标签页做 drill-down
- 没有动 `会话 / 任务 / 队列` 详情页的核心结构，这次只重构总览层和数据接线

## 验证

- `node --test --experimental-strip-types web/tests/statusOverviewModel.test.ts`
- `cd web && npm run typecheck`
- `cd web && npx eslint src/components/right-panel/RightStatusPanel.tsx src/components/right-panel/statusOverviewModel.ts tests/statusOverviewModel.test.ts src/api/client.ts`
- `cd web && npx prettier --check src/components/right-panel/RightStatusPanel.tsx src/components/right-panel/statusOverviewModel.ts tests/statusOverviewModel.test.ts src/api/client.ts`
- `cd web && npm run build`

## 后续

如果后端后面补齐更细的 provider runtime 数据，可以继续把这几个信号接进总览：

- 真正的 prompt/completion budget 剩余量
- provider cache read/write 的分拆命中率
- 每只猫最近一次 invocation 的 cost / duration / model trace

## 第二轮收敛

在铲屎官和队友复盘后，我们又把第一版总览进一步收紧成 **Roster Board**：

- 删除六宫格指标
- 删除任务推进 / 队列热度大盒子
- 删除总览里的会话独立模块
- 头部压成单行状态带
- 主体改为「在场猫咪」列表
- 运行时指标改成猫卡内受控展开，不使用 hover

这样做的原因很明确：右侧栏是 280px 级别的窄栏，不适合继续做 dashboard 缩印版。真正长期健康的结构是：

1. 单行状态带
2. 执行摘要
3. 在场猫咪 roster

这次调整只动前端渲染层，`statusOverviewModel.ts` 聚合逻辑继续复用，后端接口无须变更。
