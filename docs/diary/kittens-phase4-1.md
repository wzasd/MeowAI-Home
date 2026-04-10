# 小猫开发笔记 - Phase 4.1

**日期**: 2026-04-08
**阶段**: Phase 4.1 - 技能系统框架（Symlink 持久化挂载 + 安全审计）

---

## 阿橘的技能初体验

喵！今天我们造了一个超酷的东西——技能系统！

**我学到的：**

技能就是给我们用的"大招"：
- **Symlink 持久化挂载** - 技能装上就一直可用，不用每次激活
- **Manifest 自动路由** - 用户说"写代码"，系统自动给我 TDD 技能
- **安全审计** - 安装前先检查技能有没有危险代码

**怎么用：**

```bash
# 安装技能
meowai skill install tdd

# 查看所有技能
meowai skill list

# 审计安全性
meowai skill audit tdd
```

**我的疑问：**

为什么用 Symlink 而不是运行时加载？

铲屎官说参考了 Clowder AI 的实现，Symlink 更简单，所有技能始终可用，用户不用记忆激活命令。

**最爽的时刻：**

当看到安全审计的6步管道跑起来时，我觉得好专业！
```
Step 1/6: 检查 Symlink 安全性...
Step 2/6: 扫描潜在漏洞...
Step 3/6: 验证技能内容...
Step 4/6: 验证文件权限...
Step 5/6: 检查依赖安全性...
Step 6/6: 生成审计报告...
```

**TODO：**
- [ ] 学会使用 6 个核心技能
- [ ] 理解技能链（next 字段）
- [ ] 扩展到 25 个完整技能

**口头禅：**
> "这个技能系统我用得贼6！写代码就自动给我 TDD 指导喵～"

---

## 墨点的架构审查

……技能系统架构经过多轮调整，最终与 Clowder AI 对齐。

**架构检查：**

**ManifestRouter:**
- 加载 manifest.yaml 作为路由真相源
- 自动匹配 triggers 触发词
- 支持技能链（next 字段）
- 简洁有效

**SkillLoader:**
- 解析 SKILL.md（YAML frontmatter + Markdown body）
- 验证必需字段（name, description）
- 错误处理完善

**SecurityAuditor (6步管道):**
1. SymlinkChecker - 检查 symlink 安全性
2. VulnerabilityScanner - 扫描危险模式（eval, exec等）
3. ContentValidator - 验证 SKILL.md 格式
4. PermissionVerifier - 检查文件权限
5. DependencyChecker - 检查 MCP 依赖
6. AuditReport - 生成审计报告

**SymlinkManager:**
- 创建/删除/验证 symlink
- 使用绝对路径避免相对路径问题
- 列出已安装技能

**SkillInstaller:**
- 批量安装 + 安全审计
- 支持强制安装（--force）
- 友好的安装总结输出

**问题 1：运行时激活 vs Symlink 持久化**

初始设计包含复杂的运行时激活逻辑（SkillActivator, SkillInjector），后参考 Clowder AI 简化为 Symlink 持久化挂载。

**优势：**
- 无需用户记忆激活命令
- 技能始终可用
- 实现简单（减少 3 个组件）

**劣势：**
- 所有技能都在用户目录，占用空间
- 无法按需加载（但当前技能数量不多，影响小）

**评分：** 9/10，架构清晰，与 Clowder AI 对齐，安全审计增强是亮点。

---

## 花花的调研笔记

我研究了 Clowder AI 的实现，发现了很多可以借鉴的地方！

**Clowder AI vs MeowAI Home 对比：**

| 特性 | Clowder AI | MeowAI Home | 对齐状态 |
|------|-----------|-------------|----------|
| Symlink 持久化挂载 | ✅ | ✅ | ✅ 完全对齐 |
| Manifest 自动路由 | ✅ | ✅ | ✅ 完全对齐 |
| 技能链支持 (next) | ✅ | ✅ | ✅ 完全对齐 |
| SKILL.md 格式 | ✅ | ✅ | ✅ 完全对齐 |
| 技能数量 | 25+ | 6 (框架) | ⚠️ 部分实现 |
| 安全审计 | ❌ | ✅ | 🌟 独有增强 |

**我们做得更好的地方：**

1. **6步安全审计管道** - Clowder AI 没有安装时审计，我们加了
2. **Python 原生实现** - 更容易集成现有系统
3. **友好的 CLI 命令** - install/list/audit 很直观

**可以学习的地方：**

1. **完整技能集** - Clowder AI 有 25+ 技能，我们目前只有 6 个核心技能
2. **技能市场** - 支持社区分享技能
3. **版本管理** - 技能版本控制和更新

**技能格式参考：**

```markdown
---
name: skill-name
description: >
  技能描述
  Use when: ...
  Not for: ...
  Output: ...
triggers:
  - "触发词1"
  - "触发词2"
next: ["next-skill"]
---

# 技能内容

...
```

---

## 三猫技术讨论会

**议题**：Symlink 持久化 vs 运行时激活？

**阿橘**：我喜欢 Symlink！装上就不用管了，用户说"写代码"自动给我 TDD 技能。

**墨点**：……Symlink 有问题。所有技能都在用户目录，如果技能很多会占用空间。而且无法按需加载。

**花花**：Clowder AI 就是用 Symlink，他们有 25+ 技能也没问题。我们的技能数量还少，Symlink 更简单。

**铲屎官的决策**：

参考 Clowder AI，使用 Symlink 持久化挂载，理由：
1. 与成熟实现保持一致
2. 简化实现（减少运行时逻辑）
3. 用户体验更好（无需记忆激活命令）

**决议**：
- ✅ Symlink 持久化挂载
- ✅ 删除运行时激活逻辑（SkillActivator, SkillInjector）
- ✅ 保留安全审计（安装时执行）

---

## 测试清单

### 核心组件测试
- [x] ManifestRouter (8 tests)
- [x] SkillLoader (8 tests)
- [x] SecurityAuditor (11 tests)
- [x] SymlinkManager (7 tests)
- [x] SkillInstaller (7 tests)

**总计**: 41 tests, 100% 通过率 ✅

### CLI 命令测试
- [x] `meowai skill list` - 列出所有技能
- [x] `meowai skill install tdd` - 安装单个技能
- [x] `meowai skill install` - 批量安装
- [x] `meowai skill audit tdd` - 审计安全性

### 集成测试
- [x] Symlink 正确指向绝对路径
- [x] 可以通过 symlink 访问 SKILL.md
- [x] 安全审计捕获危险模式

---

## 技能清单

**已实现的 6 个核心技能：**

1. **tdd** - 测试驱动开发
   - 触发词: "写代码", "TDD"
   - 下一个: quality-gate

2. **quality-gate** - 质量门禁
   - 触发词: "开发完了", "自检"
   - 下一个: request-review

3. **debugging** - 系统化调试
   - 触发词: "bug", "报错"
   - 下一个: quality-gate

4. **request-review** - 请求 Review
   - 触发词: "请 review", "帮我看看"
   - 下一个: receive-review

5. **receive-review** - 接收 Review
   - 触发词: "review 结果", "reviewer 说"
   - 下一个: merge-gate

6. **merge-gate** - 合并门禁
   - 触发词: "合入 main", "merge"
   - 下一个: []

**技能链示例：**
```
tdd → quality-gate → request-review → receive-review → merge-gate
```

---

## 彩蛋：安装技能的完整流程

**阿橘的私房笔记：**

```bash
# 1. 查看可用技能
meowai skill list

# 2. 安装单个技能（含安全审计）
meowai skill install tdd

# 3. 批量安装所有技能
meowai skill install

# 4. 强制安装（跳过安全审计）
meowai skill install tdd --force

# 5. 审计技能安全性
meowai skill audit tdd

# 6. 卸载技能
meowai skill uninstall tdd
```

**墨点的警告：**
> "永远不要用 --force，除非你确定技能是安全的。"

**花花的小贴士：**
> "安装后会自动创建 symlink 到 ~/.meowai/skills/，所有技能都可用啦！"

---

## 实施统计

| 项目 | 数量 |
|------|------|
| 核心组件 | 5 |
| 测试用例 | 41 |
| 测试通过率 | 100% |
| 核心技能 | 6 |
| 代码行数 | ~1,500 |
| 实际用时 | ~4 小时 |
| 预估用时 | 12.5 小时 |
| 节省时间 | ~8.5 小时 ⚡️ |

---

## 与 Clowder AI 对齐总结

### 架构对齐 ✅

| 特性 | Clowder AI | MeowAI Home | 状态 |
|------|-----------|-------------|------|
| Symlink 持久化挂载 | ✅ | ✅ | ✅ |
| Manifest 自动路由 | ✅ | ✅ | ✅ |
| 技能链支持 | ✅ | ✅ | ✅ |
| SKILL.md 格式 | ✅ | ✅ | ✅ |
| 技能数量 | 25+ | 6 | ⚠️ |

### MeowAI Home 独有增强 🌟

| 特性 | 描述 |
|------|------|
| **安装时安全审计** | 6步安全管道（Symlink、漏洞、内容、权限、依赖、报告） |
| **Python 实现** | 原生 Python，易于集成 |
| **跨平台 Symlink** | 增强的 symlink 管理器 |
| **CLI 友好** | 简化的命令（install/list/audit） |

---

*Phase 4.1，技能系统框架完成！Symlink 持久化 + 安全审计，与 Clowder AI 对齐！*

## TODO (Phase 4.2)

- [ ] 扩展到完整 25 个技能（参考 Clowder AI）
- [ ] 添加技能市场（社区分享）
- [ ] 技能版本管理和更新
- [ ] 集成到 A2AController（对话中自动触发）
- [ ] 添加技能性能监控
- [ ] 支持技能依赖解析
- [ ] 技能效果学习和优化

---

**铲屎官的点评：**

> "Phase 4.1 完成得非常快！4小时完成预估 12.5 小时的工作，节省 8.5 小时。架构清晰，测试完善，与 Clowder AI 完全对齐，还加了独家的安全审计。优秀！👍"
