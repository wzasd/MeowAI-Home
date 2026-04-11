# MeowAI Home vs Clowder AI (参考UI) 功能对比

## 组件数量对比

| 项目 | 组件文件数 |
|------|-----------|
| Clowder AI (参考) | 133 |
| MeowAI Home | ~50 (合并组织后) |

## 功能模块对比

### 核心聊天功能

| 功能 | Clowder AI | MeowAI Home | 差距 |
|------|------------|-------------|------|
| 消息气泡 | ChatMessage.tsx | MessageBubble.tsx | 功能相当 |
| 输入框 | ChatInput.tsx | InputBar.tsx | 功能相当 |
| 连接器消息 | ConnectorBubble.tsx | ❌ 缺失 | 需实现 |
| 富文本块 | RichBlocks | RichBlocks | 功能相当 |
| 语音输入 | VoiceSettingsPanel | VoiceInput.tsx | 功能相当 |
| Markdown渲染 | MarkdownContent | 基础实现 | 需增强 |
| 历史搜索 | HistorySearchModal | HistorySearchModal | 功能相当 |

### 右侧面板

| 功能 | Clowder AI | MeowAI Home | 差距 |
|------|------------|-------------|------|
| Token用量 | CatTokenUsage | TokenUsagePanel | 功能相当 |
| Session链 | 有 | SessionChainPanel | 功能相当 |
| 任务面板 | taskStore | TaskPanel | 功能相当 |
| 队列管理 | 有 | QueuePanel | 功能相当 |
| 审计日志 | audit | AuditPanel | 功能相当 |
| 证据检索 | EvidencePanel | ❌ 缺失 | 需实现 |
| Git健康 | useGitHealth | ❌ 缺失 | 可选 |

### Hub/设置面板

| 功能 | Clowder AI | MeowAI Home | 差距 |
|------|------------|-------------|------|
| 猫咪管理 | HubCatEditor | SettingsPanel基础 | 需增强 |
| 能力配置 | HubCapabilityTab | CapabilitySettings | 功能相当 |
| 排行榜 | HubLeaderboardTab | LeaderboardTab | 功能相当 |
| 治理面板 | HubGovernanceTab | ❌ 缺失 | 需实现 |
| 环境变量 | HubEnvFilesTab | ❌ 缺失 | 可选 |
| 提供商配置 | HubProviderProfilesTab | ❌ 缺失 | 可选 |
| 刹车设置 | BrakeSettingsPanel | BrakeSystem | 功能相当 |
| 配额看板 | DailyUsageSection | QuotaBoard | 功能相当 |

### Signal 系统

| 功能 | Clowder AI | MeowAI Home | 差距 |
|------|------------|-------------|------|
| 收件箱 | signals/page | SignalInboxPage | 功能相当 |
| 来源管理 | signals/sources | SourcesView | 功能相当 |
| 文章详情 | 有 | ArticleDetail | 功能相当 |

### Mission 系统

| 功能 | Clowder AI | MeowAI Home | 差距 |
|------|------------|-------------|------|
| 任务看板 | mission-hub | MissionHubPage | 功能相当 |
| Mission Control | mission-control | ❌ 缺失 | 需实现 |

### Workspace 系统

| 功能 | Clowder AI | MeowAI Home | 差距 |
|------|------------|-------------|------|
| 文件树 | workspace | WorkspacePanel | 功能相当 |
| IDE面板 | 有 | 有 | 功能相当 |
| 终端集成 | 有 | 有(占位) | 需完善 |

### 游戏/娱乐

| 功能 | Clowder AI | MeowAI Home | 差距 |
|------|------------|-------------|------|
| Pixel Brawl | pixel-brawl | ❌ 缺失 | 可选 |

### 连接器集成

| 功能 | Clowder AI | MeowAI Home | 差距 |
|------|------------|-------------|------|
| 飞书集成 | FeishuQrPanel | ❌ 仅后端 | 需前端 |
| 微信集成 | WeixinQrPanel | ❌ 仅后端 | 需前端 |
| GitHub集成 | 有 | ❌ 缺失 | 可选 |

## 缺失的关键功能 (按优先级排序)

### P1 - 高优先级

1. **ConnectorBubble** - 连接器消息展示 (用于显示外部系统消息)
2. **EvidencePanel** - 证据检索结果面板 (RAG功能展示)
3. **HubGovernanceTab** - 治理面板 (铁律系统配置)
4. **Mission Control** - 高级任务控制面板

### P2 - 中优先级

5. **MarkdownContent** - 增强的Markdown渲染
6. **useGitHealth** - Git健康状态监控
7. **HubEnvFilesTab** - 环境变量管理
8. **连接器前端面板** - 飞书/微信二维码绑定UI

### P3 - 低优先级

9. **Pixel Brawl游戏** - 娱乐功能
10. **HubProviderProfilesTab** - 多提供商配置
11. **语音输出(TTS)** - 语音播放

## Hooks 对比

| Hook | Clowder AI | MeowAI Home |
|------|------------|-------------|
| useCatData | 有 | useCatStore (相当) |
| useChatHistory | 有 | useChatStore (相当) |
| useFileManagement | 有 | useWorkspace (相当) |
| useGovernanceStatus | 有 | ❌ 缺失 |
| useGitHealth | 有 | ❌ 缺失 |
| useAuthorization | 有 | ❌ 缺失 |
| useCoCreatorConfig | 有 | ❌ 缺失 |

## 状态管理对比

| Store | Clowder AI | MeowAI Home |
|-------|------------|-------------|
| chatStore | 有 | 有 |
| brakeStore | 有 | 有 |
| taskStore | 有 | 有 |
| toastStore | 有 | ❌ 缺失 |
| voiceSessionStore | 有 | 有 |
| missionControlStore | 有 | ❌ 缺失 |
| gameStore | 有 | ❌ 缺失 |
| externalProjectStore | 有 | ❌ 缺失 |

## 建议实现顺序

1. **Phase 1**: ConnectorBubble + EvidencePanel (完善聊天体验)
2. **Phase 2**: HubGovernanceTab (铁律系统配套UI)
3. **Phase 3**: Mission Control (高级任务管理)
4. **Phase 4**: 连接器前端面板 (企业集成)
5. **Phase 5**: 其他增强功能
