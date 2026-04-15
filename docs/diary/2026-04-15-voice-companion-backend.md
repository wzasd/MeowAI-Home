---
doc_kind: diary
created: 2026-04-15
topics: [voice, tts, asr, edge-tts, whisper]
---

# Voice Companion 后端实现

## 目标
补齐 Clowder 对齐计划中的 Plan 1.3：为每只猫咪提供独立的 TTS 音色和语音输入(ASR)能力。

## 实现内容

### 后端
- `src/voice/tts_service.py`
  - 基于 `edge-tts`（免费、无需 API Key）
  - 默认音色映射：orange→晓晓、inky→云希、patch→晓伊
  - 文件缓存：`~/.meowai/voice/{thread_id}/{hash}.mp3`
  - 支持 rate / volume / pitch 参数

- `src/voice/asr_service.py`
  - 基于 OpenAI Whisper API（复用已有的 `httpx` 依赖）
  - 自动根据扩展名推断 MIME 类型
  - 需要 `OPENAI_API_KEY`

- `src/web/routes/voice.py`
  - `POST /api/voice/tts` — 返回 MP3 文件
  - `POST /api/voice/asr` — 返回转写文本
  - TTS 校验 thread 存在；ASR 限制 25MB 音频

- `src/web/app.py`
  - 注册 `voice_router`

### 前端
- `web/src/api/client.ts`
  - 新增 `api.voice.tts()` 和 `api.voice.asr()`

- `web/src/components/chat/TTSButton.tsx`
  - 从浏览器 `speechSynthesis` 切换到后端 Edge TTS
  - 通过 Blob + ObjectURL 播放音频

- `web/src/components/chat/VoiceInput.tsx`
  - 从浏览器 `SpeechRecognition` 切换到 `MediaRecorder` 录音
  - 录音结束后上传后端 Whisper 识别
  - 优先使用 `audio/webm`，降级到 `audio/mp4`

- `web/src/components/chat/AudioPlayer.tsx`
  - 新增通用音频播放组件（供后续复用）

- `web/src/components/chat/MessageBubble.tsx`
  - `TTSButton` 新增 `catId`  prop 传递

### 测试
- `tests/voice/test_tts_service.py` — 12 项断言，覆盖缓存、空文本、清理
- `tests/voice/test_asr_service.py` — 4 项断言，覆盖成功、缺 Key、缺文件、HTTP 错误
- `tests/web/test_voice_api.py` — 5 项断言，覆盖 TTS/ASR 成功与异常场景

## 验证结果
- 后端测试：17/17 passed
- 前端类型检查：`tsc --noEmit` 0 错误

## 遗留/下一步
- 前端 Vitest 单元测试（AudioPlayer、TTSButton、VoiceInput）待补充
- 猫咪可在设置面板自定义音色（当前为硬编码默认值）
