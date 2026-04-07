# Day 1: 让阿橘第一次开口说话

## 缘起

今天开始了一个有趣的项目——MeowAI Home，一个温馨的流浪猫AI收容所。

我想做一个"一人企业"，但一个人精力有限，所以需要AI团队帮忙。而猫猫是最可爱的助手！

## 阿橘是谁？

阿橘是一只橘猫，在菜市场流浪时被收容所发现。他热情话唠、点子多、有点皮但很靠谱。他是团队的主力开发者，什么都会。

口头禅是："这个我熟！" "包在我身上！"

## 技术选型

选择Python作为开发语言，因为：
1. 简单易上手
2. GLM-5.0和Kimi的Python SDK更成熟
3. 快速原型开发

## 今天做了什么

### 1. 项目初始化

创建了基础的项目结构：
```
meowai-home/
├── src/          # 源代码
├── tests/        # 测试
├── config/       # 配置
├── data/         # 数据
└── docs/         # 文档
```

### 2. 数据模型

定义了核心数据结构：
- `Message`: 单条消息
- `Thread`: 对话线程

使用dataclass简化代码，SQLite作为持久化存储。

### 3. Thread存储

实现了`ThreadStore`类，负责对话的持久化：
- 保存对话线程
- 加载历史对话
- 异步操作（使用aiosqlite）

### 4. NDJSON流处理

为了处理AI CLI的流式输出，实现了NDJSON解析器。
NDJSON = Newline Delimited JSON，每行一个JSON对象。

### 5. 进程管理

实现了`run_cli_command`函数，用于调用外部CLI命令：
- 支持超时控制
- 防止僵尸进程
- 异步执行

### 6. 配置管理

使用YAML文件管理猫猫配置：
- 名字、模型、角色
- 性格、专长
- 口头禅

### 7. 阿橘的Agent Service

创建了阿橘的Agent服务（目前是Mock实现）：
- `OrangeConfig`: 配置加载
- `OrangePersonality`: 性格设定
- `OrangeService`: 服务实现

### 8. CLI主入口

使用Click框架实现CLI：
- `meowai chat`: 与猫猫对话
- 支持选择不同的猫猫

## 踩坑记录

### 坑1: aiosqlite的异步上下文

一开始直接在`__init__`中`await aiosqlite.connect()`，结果报错。
**解决**: 懒加载，在第一次使用时才创建连接。

### 坑2: Click的异步命令

Click默认不支持异步命令。
**解决**: 先用同步命令，后续需要时再用`anyio.run()`包装。

### 坑3: 测试中的异步

pytest-asyncio需要配置`asyncio_mode = "auto"`。
**解决**: 在`pyproject.toml`中添加配置。

## 测试结果

所有测试通过：
```bash
pytest tests/ -v
# 18 passed
```

## 下一步

明天要实现：
1. 真实的GLM-5.0 CLI调用（替换Mock）
2. 流式输出渲染
3. 更完善的对话循环

## 感悟

虽然今天只是搭建基础架构，但已经能感受到这个项目的雏形。

阿橘还在"睡觉"（Mock实现），但框架已经准备好了。明天就让他真正开口说话！

---

**今日代码行数**: ~600行
**耗时**: 3小时
**心情**: 😺 充实
