---
doc_kind: diary
created: 2026-04-15
topics: [signals, podcast, research, notes, study]
---

# Signal Study 深度功能补齐

## 目标
将 Signal 从"RSS 阅读器"升级为"AI 研究助手"，补齐 Plan 1.2：笔记持久化、播客生成、多猫研究报告。

## 实现内容

### 1. 笔记持久化
- `src/signals/store.py`
  - 通过 `ALTER TABLE` 兼容式新增 `notes TEXT` 字段
  - 新增 `get_notes(article_id)` 和 `save_notes(article_id, notes)`

- `src/web/routes/signals.py`
  - `GET /api/signals/articles/{id}/notes`
  - `POST /api/signals/articles/{id}/notes`

- 前端
  - `useSignals.ts` 新增 `getNotes` / `saveNotes`
  - `SignalInboxPage.tsx` 学习模式中的 textarea 改为持久化存储，增加"保存"按钮

### 2. 播客生成
- `src/signals/podcast.py`
  - `PodcastGenerator` 将文章标题+摘要构造成中文播客脚本
  - 调用 `tts_service.synthesize()`（复用 Plan 1.3 的 Edge TTS）生成 MP3
  - 缓存路径：`~/.meowai/voice/signal-{article_id}/{hash}.mp3`

- `src/web/routes/signals.py`
  - `POST /api/signals/articles/{id}/podcast` — 返回 `audio/mpeg` 文件

- 前端
  - `useSignals.ts` 新增 `generatePodcast`
  - `SignalInboxPage.tsx` 点击"生成播客"后显示 `<audio controls>` 播放器

### 3. 多猫研究报告
- `src/signals/research.py`
  - `ResearchGenerator` 接收 `CatRegistry` + `AgentRegistry`
  - 并行向所有注册猫咪发送研究提示词（基于文章摘要）
  - 聚合各猫输出为 Markdown 格式报告

- `src/web/routes/signals.py`
  - `POST /api/signals/articles/{id}/research` — 返回 `{title, sections, summary}`

- 前端
  - `useSignals.ts` 新增 `generateResearch`
  - `SignalInboxPage.tsx` 点击"讨论（多猫研报）"后在下方展开 Markdown 报告

## 测试
- `tests/signals/test_store.py`：新增 `test_notes`、`test_notes_nonexistent`
- `tests/web/test_signals_api.py`：新增 `TestNotes`（GET/POST notes 边界测试）
- 后端测试：34/34 passed
- 前端类型检查：`tsc --noEmit` 0 错误

## 验证结果
- Signal 学习模式三大按钮（保存笔记、生成播客、多猫研报）均已对接真实后端
- 播客利用已有 TTS 服务，无新增外部依赖
- 研报复用已有 provider 注册表，无需额外配置

## 下一步
- Phase 2 启动：Mission Hub / Workspace 增强（Plan 2.1）
