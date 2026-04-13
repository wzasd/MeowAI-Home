# 个人用户功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 针对个人用户场景，补充高价值功能，提升使用体验

**Architecture:** 保持现有架构（Python + FastAPI + React），在现有基础上增量添加

---

## 优先级排序（个人用户场景）

| 优先级 | 功能 | 用户价值 | 复杂度 | 前置依赖 |
|--------|------|---------|--------|----------|
| **P0** | @mention 响应优化 | 核心体验 | M | 无 |
| **P1** | 文件上传 | 传代码/截图分析 | M | 无 |
| **P2** | TTS 语音合成 | 让猫"说话" | M | 文件上传（存储） |
| **P3** | 真实向量嵌入 | 记忆搜索更准 | M | 调研 embedding 方案 |
| **P4** | Session Chain 增强 | 上下文连贯 | L | 已部分实现 |
| **P5** | VSCode 插件 | 编辑器内交互 | XL | 低优先级 |

---

## 任务详情

### 任务 1: @mention 响应优化

**问题诊断:**
- `_call_cat()` 每次调用都串行执行: 记忆检索 → 服务调用 → 记忆存储 → 实体提取 → 关系推断
- CLI 子进程启动本身有延迟
- 实体提取和关系推断阻塞响应返回

**优化方案:**
1. **并行化辅助操作** - 记忆检索和范围守卫检查并行执行
2. **后置化处理** - 记忆存储、实体提取改为后台异步任务
3. **响应流式化** - 首 token 立即返回，不等完整响应
4. **连接池** - CLI 子进程复用（长期运行模式）

**Files:**
- Modify: `src/collaboration/a2a_controller.py`
- Create: `src/collaboration/async_processor.py`

---

### 任务 2: 文件上传

**需求:**
- 支持图片、代码文件、文档上传
- 保存到 thread workspace
- Agent 可以读取并分析内容

**Files:**
- Create: `src/web/routes/uploads.py`
- Modify: `src/web/app.py` - 注册上传路由
- Modify: `src/collaboration/mcp_tools.py` - 添加 `read_uploaded_file` 工具
- Create: `web/src/components/chat/FileUpload.tsx`
- Modify: `web/src/api/client.ts` - 添加上传 API

---

### 任务 3: TTS 语音合成

**需求:**
- 后端: 集成 edge-tts 或类似方案
- 每只猫独特声音（不同 voice/pitch/speed）
- 前端: 音频播放组件

**Files:**
- Create: `src/tts/service.py`
- Create: `src/tts/voices.py` - 猫声配置
- Create: `src/web/routes/tts.py`
- Create: `web/src/components/chat/TtsPlayer.tsx`

---

### 任务 4: 真实向量嵌入

**需求:**
- 替换当前 MD5 hash 假嵌入
- 集成 sentence-transformers 或 OpenAI embedding
- Hybrid RRF: FTS5 + 向量搜索

**Files:**
- Modify: `src/search/embedding.py`
- Create: `src/search/providers/` - OpenAI, Local, etc.
- Modify: `src/search/vector_store.py` - 存储真实向量

---

### 任务 5: Session Chain 增强

**需求:**
- 前端显示会话链
- 手动 seal/unseal 操作
- 会话摘要显示

**Files:**
- Modify: `src/web/routes/threads.py` - session chain 端点
- Create: `web/src/components/thread/SessionChain.tsx`

---

## 执行顺序

```
任务 1: @mention 优化 (核心体验)
  ↓
任务 2: 文件上传 (解锁多模态)
  ↓
任务 3: TTS (语音交互)
  ↓
任务 4: 向量嵌入 (搜索质量)
  ↓
任务 5: Session Chain UI
  ↓
任务 6: VSCode 插件 (可选)
```

---

## 验证标准

每个任务完成后:
1. 功能测试通过
2. 用户体验有明显改善
3. 性能测试达标（@mention 响应 < 2s）
