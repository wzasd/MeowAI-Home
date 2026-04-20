# 2026-04-17 设置台 UI / UX 设计记录

## 本轮做了什么

- 审计了当前设置台主容器和核心 tab：
  - `web/src/components/settings/SettingsPanel.tsx`
  - `web/src/components/settings/CatSettings.tsx`
  - `web/src/components/settings/AccountSettings.tsx`
  - `web/src/components/settings/CapabilityBoard.tsx`
  - `web/src/components/settings/GovernanceSettings.tsx`
- 对照现有设计 token 和历史设计 / IA 文档，确认问题不是单页样式，而是设置台整体信息架构失衡
- 写出一版设置台 UI / UX 重构方案：
  - `docs/superpowers/plans/2026-04-17-settings-ui-ux-redesign.md`

## 关键判断

1. 当前设置台最大问题不是“不够美”，而是“配置、治理、观察、自动化”四种任务被扁平 tab 混装
2. 外壳已经接入猫窝设计语言，但内部内容区大量回退成默认后台风格，导致品牌壳和业务内容脱节
3. `QuotaBoard` / `LeaderboardTab` 更像只读观察页，不适合长期留在“设置”语义里

## 方案摘要

- 设置默认页应先给“概览”，先回答“现在先处理什么”
- 左侧导航按用户意图分 4 组，而不是继续平铺 13 个 tab
- 内容页统一成“页头 + section cards + 上下文提示”的三段式结构
- 表格只在必须横向对比时使用，默认优先卡片和分段

## 下一步

- 和 @opus 对齐信息架构与实现边界
- 如确认方向成立，优先落 `SettingsPanel` 外壳 + `GovernanceSettings` / `AccountSettings` 两个示范页

## Phase 1 已落地

- 新增 `web/src/components/settings/settingsRegistry.ts`
  - 把 settings 的分组、描述、保存模式、迁出状态、overview card 元数据收敛到一处
- 新增 `web/src/components/settings/SettingsPageHero.tsx`
  - 统一页头、保存模式提示、迁出状态提示
- 新增 `web/src/components/settings/SettingsOverviewPage.tsx`
  - 设置台默认页改成静态 overview card，不做后端 summary 聚合
- 修改 `web/src/components/settings/SettingsPanel.tsx`
  - 从平铺 tab 改成 `overview + 4 组导航`
  - 读取 registry 生成左侧导航和内容页 hero
  - `QuotaBoard` / `LeaderboardTab` 在导航中标记为迁出观察项

## 本轮验证

- `node --experimental-strip-types --test web/tests/settingsRegistry.test.ts`
- `npm run typecheck`（`web/`）
- 定向 `eslint`

## 还没做的

- 没做实时 overview 聚合，只保留静态入口卡
- 没做 settings 搜索 UI，只把 keyword 元数据预留在 registry
- 没重画各业务子页内部结构，当前优先统一外壳、hero、分组导航

## Phase 2 已扩展的内容页

- 新增 `web/src/components/settings/SettingsSectionCard.tsx`
  - 统一内容页 section shell 和 summary grid
- 新增 / 扩展 `web/src/components/settings/settingsSummaryModels.ts`
  - 先后补了账号、治理、连接器、权限、环境变量、能力编排 6 组 summary model
- `web/src/components/settings/AccountSettings.tsx`
  - 增加账号摘要卡
  - 账号列表和编辑器收进统一 section shell
- `web/src/components/settings/GovernanceSettings.tsx`
  - 增加治理摘要卡
  - 新增项目输入区和治理表统一收口到一个 section
- `web/src/components/settings/ConnectorSettings.tsx`
  - 增加连接器摘要卡
  - 把启用、绑定、二维码、配置测试收进统一控制台卡片
  - 补了可见错误提示，不再只是 `console.error`
- `web/src/components/settings/PermissionsSettings.tsx`
  - 增加权限摘要卡
  - 权限矩阵、风险说明、刷新操作收进统一 section shell
- `web/src/components/settings/EnvVarSettings.tsx`
  - 增加环境变量摘要卡
  - 运行时说明、分类分组、逐项保存动作统一收进口径一致的 section shell
  - 补了可见错误提示和脏值判定，不再对未修改值重复提交
- `web/src/components/settings/CapabilityBoard.tsx`
  - 增加能力编排摘要卡
  - 项目路径控制区、MCP / Skill 两块表格统一收进 section shell
  - 把探测说明、异常提示、空态分层显式摆出来，继续保留即时生效契约
- `web/src/components/settings/QuotaBoard.tsx`
  - 把每只猫的 7 天资源观测聚合提炼为纯函数，补上摘要卡
  - 只读观察视图接入统一 section shell，并显式标明这是观察页不是配置页
- `web/src/components/settings/LeaderboardTab.tsx`
  - 把排行榜排序和摘要逻辑提炼为纯函数，领奖台和表格共用同一份排序结果
  - 时间窗口、空态、错误态统一接入 section shell

## 新增验证

- `node --experimental-strip-types --test web/tests/settingsSummaryModels.test.ts`
- `node --experimental-strip-types --test web/tests/settingsRegistry.test.ts`
- `npm run typecheck`（`web/`）
- 定向 `eslint`

## 当前状态

- `QuotaBoard / LeaderboardTab` 已正式迁出 settings，进入右侧状态台的 `指标` tab
- reviewer follow-up 已补三处：
  - `指标` tab 明确标为全局指标，不再复用“当前线程”文案
  - quota 全量拉取失败时显示 error，不再伪装成“最近没数据”
  - settings 总览里的“治理与观察”描述已改成指向右侧状态台
- 当前新增的行为保护仍以 node 下的 model/layout 测试为主；仓内还没有 `vitest/jsdom/@testing-library/react` 这类组件测试栈
- 本轮仍未做 runtime/截图预览，验证证据以模型测试、类型检查、定向 eslint 为主
