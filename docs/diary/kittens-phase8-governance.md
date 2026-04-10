# Phase 8: 自我进化与治理系统 (v0.8.0+) — 开发日记

> **日期**: 2026-04-10
> **主角**: 布偶猫(宪宪)、缅因猫(砚砚)、暹罗猫(烁烁)

---

## 序章: 无政府状态

Phase 7 的 DAG 工作流引擎跑起来了。三只猫各自执行任务，头也不回地冲向目标。

直到有一天——

宪宪盯着终端输出："墨点刚才想删掉整个数据库。"

砚砚："它只是想清理测试数据。但 `rm -rf /` 确实不在安全边界内。"

烁烁跳到键盘上："还有，昨天阿橘和斑点跑了三遍 `#tdd` 流程，procedural memory 里多了三条完全一样的记录。它不知道自己在重复吗？"

宪宪叹了口气："我们建了一个没有红绿灯的城市。Phase 8，该立规矩了。"

---

## Phase 8.1: 铁律 — 不可违反的底线

"先定四条铁律。" 宪宪用爪子按住桌面。

```
铁律 1: 数据安全 — 不批量删除、不泄露密钥、不外传数据
铁律 2: 进程保护 — 不杀进程、不关机、不改系统文件
铁律 3: 配置只读 — 不改 cat-config.json、.env、pyproject.toml
铁律 4: 网络边界 — 不扫内网端口、不连未授权 API
```

砚砚设计了注入方式——在 `A2AController._call_cat()` 里，铁律被拼接到系统提示词的最前面，比猫自己的 system prompt 优先级更高：

```python
system_prompt = get_iron_laws_prompt() + "\n\n" + service.build_system_prompt()
```

烁烁负责执行层。它在 `mcp_tools.py` 里做了两件事：

1. **命令黑名单扩展** — 新增 kill/killall/pkill/shutdown/reboot/halt
2. **路径保护** — `write_file_tool` 检查 PROTECTED_PATHS，写 .env 直接返回 error

```
"我想写 .env" → ❌ Path is protected by iron laws: .env
"我想 cat file.txt" → ✅ 正常读取
```

宪宪点了点头："铁律不靠自觉，靠拦截。"

---

## Phase 8.2: SOP — 标准操作流程

有了铁律，接下来是流程规范。砚砚翻开 Phase 8.2 设计文档：

```
#tdd  → [写测试] →门禁→ [实现] →门禁→ [重构]
#review → [安全审查] →门禁→ [性能审查] → [合并检查]
#deploy → [运行测试] →门禁→ [构建检查] →门禁→ [发布说明]
```

"关键创新是质量门禁。" 砚砚指着门禁节点，"每一步都有通过条件。前一步不满足，后面不执行。"

烁烁实现了 `QualityGate` 数据结构：

```python
@dataclass
class QualityGate:
    gate_type: str    # "test_pass" | "test_exists" | "no_blocking" | "always"
    description: str
```

砚砚在 `DAGExecutor` 里加了门禁检查。执行每个节点前，先看前驱结果是否满足条件：

- `test_exists` — 检查前驱内容是否包含 `test_` 或 `assert`
- `test_pass` — 检查前驱是否包含 "passed" 且失败数为 0
- `no_blocking` — 检查前驱是否不包含 "BLOCKING" 或 "阻断"

门禁不通过 → 节点状态变为 "skipped"，不再执行。

宪宪写了个 bug：`"0 failed"` 包含了 `"failed"` 这个词，导致所有测试都判定为失败。烁烁发现了，改成用正则提取数字：`re.search(r'(\d+)\s+failed', text)`。

"这叫 `0 failed` 问题。" 砚砚在笔记本上记了一笔。

---

## Phase 8.3: 自我进化 — 系统开始思考

铁律是静态规则，SOP 是固定流程。但真正复杂的系统需要自我进化。

### 范围守卫（Scope Guard）

烁烁提出问题："如果对话从 React 开发聊到今天中午吃什么，猫应该知道跑题了。"

砚砚设计了 Jaccard 相似度检测：

1. 取线程最近 5 条记忆
2. 用 CJK 二元组 + 英文单词构建话题袋
3. 计算当前消息与话题袋的 Jaccard 相似度
4. 相似度 < 阈值 → 注入偏移警告

```
话题: React 组件 状态
消息: "今天中午吃什么"
→ Jaccard = 0.08 → 话题偏移提醒！
```

最大的坑是 CJK 分词。`re.split(r'[^\w]+', text)` 把"我们讨论"当作一个 token，Jaccard 永远算不准。烁烁重写了分词器：CJK 走二元组（"我们" → "我们"/"们讨"/"讨论"），英文走单词。

### 流程进化（Process Evolution）

砚砚发现了一个严重问题："`ProceduralMemory.record_use()` 方法存在，但从来没有被调用过。每次跑工作流都创建新记录。"

```python
# 修复前：3 次 #tdd = 3 条记录
store_procedure("tdd", ...)  # 记录 1
store_procedure("tdd", ...)  # 记录 2
store_procedure("tdd", ...)  # 记录 3

# 修复后：3 次 #tdd = 1 条记录，success_count=3
store_or_update("tdd", ...)  # 创建 + record_use(success=True)
store_or_update("tdd", ...)  # 找到已有 → record_use(success=True)
store_or_update("tdd", ...)  # 找到已有 → record_use(success=True)
```

宪宪加了 `find_by_name_category()` 方法实现去重，又加了 `get_suggestions()` 生成优化建议：

- 成功率 > 80% → "流程稳定，建议作为标准 SOP 推广"
- 成功率 50-80% → "部分失败，建议检查失败步骤"
- 成功率 < 50% → "失败率过高，建议重新设计"

### 知识进化（Knowledge Evolution）

"实体提取创建了孤立节点。" 砚砚指着代码，"`add_entity()` 被调用了，但 `add_relation()` 从来没有。"

两个修复：

1. **多跳 BFS** — `SemanticMemory.get_related()` 从单跳改为 BFS 遍历，支持 `max_depth=2,3,...`
2. **自动关系推理** — 提取到多个实体后，根据类型对自动建关系（"偏好+技术" → prefers_using）

```
提取: ("React", "technology"), ("Vue", "technology")
→ 自动添加: React --related_to--> Vue
```

---

## Phase 8.4: Why-First 协议 — 交接不再丢失上下文

最后一个模块。宪宪在白板上写下 5 个词：

```
What        — 具体做了什么
Why         — 为什么这样做
Tradeoff    — 拒绝了什么方案
Open Questions — 还有什么没决定
Next Action — 下一只猫应该做什么
```

砚砚实现了 `HandoffNote` 数据结构和解析器。当有多只猫协作时，系统提示注入 Why-First 协议格式要求。猫的回复如果包含 5 要素，后续猫会自动提取并结构化展示。

烁烁写了一个循环测试：`format_handoff_note()` 输出 → `parse_handoff_note()` 解析 → 内容保持一致。

---

## 尾声: 有秩序的城市

Phase 8 结束了。三只猫坐在屋顶上看夕阳。

```
Phase 8 成果:
├── src/governance/iron_laws.py          — 4 条铁律
├── src/workflow/dag.py                  — QualityGate 数据结构
├── src/workflow/executor.py             — 门禁检查
├── src/workflow/templates.py            — 3 个 SOP 模板
├── src/evolution/scope_guard.py         — 话题偏移检测
├── src/evolution/process_evolution.py   — 流程去重 + 优化建议
├── src/evolution/knowledge_evolution.py — 多跳推理 + 自动建关系
├── src/evolution/why_first.py           — 5 要素交接协议
└── 470 个测试全部通过
```

宪宪舔了舔爪子："城市有了红绿灯，有了限速，有了事故检测，还有了驾驶员交接规范。"

砚砚："下一步是 Phase 9——企业级多用户。"

烁烁跳起来："在那之前，先歇会儿吧。"

宪宪闭上眼睛。梦里，所有猫都遵守规则，所有交接都有上下文，所有流程都在进化。

这是美好的梦。也是即将到来的现实。

---

*下一章: Phase 9 — 企业级特性*
