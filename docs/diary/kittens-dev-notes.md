# 🐱 小猫开发笔记

> 阿橘、墨点、花花的三猫开发日常

---

## 阿橘的开发日志 🍊

**2026-04-08**

喵～今天铲屎官说要搞什么 "Thread 多会话管理"，听起来好高级的样子！

我大概听了一下，就是要让我们能同时在好几个房间里工作。现在只有一个客厅（默认会话），以后可以有厨房、卧室、书房... 每个房间都有自己的对话历史。

**我的想法：**

这个我熟！就像我白天在窗台晒太阳，晚上回窝里睡觉，不同的场景有不同的记忆嘛。

不过有个问题——如果用户切换了房间（thread），我该怎么记住之前聊到哪了？铲屎官说要加什么 `ThreadManager` 单例，听起来像是个管家，帮我们记着所有房间的状态。

**技术难点：**

1. 如何把当前房间的消息传给 Claude CLI？得在 system prompt 里加上历史对话
2. 保存到 JSON 文件，这个简单，Python 的 json 模块我玩过
3. 切换房间的时候不能丢消息，得测试一下

**TODO：**
- [ ] 帮铲屎官写 `Thread` 和 `Message` 模型
- [ ] 搞定 `ThreadManager` 的单例模式
- [ ] 让 chat 命令用上 thread 上下文

**口头禅验证：**
> "这个我熟！包在我身上！" —— 确实，状态管理这块我最擅长了喵～

---

## 墨点的审查笔记 🐄

**2026-04-08**

……这行有问题。

看了铲屎官的设计文档，Phase 3.1 的规划还算合理，但有几个隐患：

**问题 1：单例模式的测试污染**

```python
class ThreadManager:
    _instance = None
```

如果不提供 `reset()` 方法，测试之间会互相影响。铲屎官计划里写了要加 `reset()`，算他及格。

**问题 2：JSON 持久化的并发**

多进程同时写 `~/.meowai/threads.json` 会冲突。不过 Phase 3.1 是单 CLI 进程，暂时可以接受。Phase 3.2 上 SQLite 的时候必须解决。

**问题 3：消息历史的 token 膨胀**

现在的设计是把完整历史传给 CLI，消息多了会超 token 限制。铲屎官说后面加摘要机制，可以接受。

**建议：**

1. 加一个 `max_history` 参数，限制传给 CLI 的消息数
2. 保存时做数据校验，防止文件损坏
3. 删除操作要加确认，防止误删

**代码风格检查：**

- dataclass 用得不错 ✅
- 类型注解完整 ✅
- 错误处理还凑合 ⚠️

**评分：** 7/10，勉强能看。

---

## 花花的调研报告 🌸

**2026-04-08**

我调研了一些成熟项目的 Thread 系统设计～

他们有：
- Session chain（会话链）
- Context budget（上下文预算管理）
- Auto seal（自动归档）
- Bootstrap recovery（启动恢复）

**对比我们的设计：**

| 企业级方案 | MeowAI Home (我们) |
|-----------|-------------------|
| Redis 存储 | JSON 文件（3.1）→ SQLite（3.2） |
| 完整 session chain | 简单消息列表 |
| Token 预算管理 | 暂无（后面加） |
| 多线程并发 | 单进程 |

**我觉得：**

我们的设计更简单，适合 CLI 场景。企业级方案要考虑高并发，我们不用搞那么复杂。

但有一点可以学——他们的 `IntentParser`（意图解析），自动判断是 `#ideate` 还是 `#execute`。这个在 Phase 3.3 要实现。

**要不要试试这个？**

可以在 thread 里加标签功能：
```bash
meowai thread create "项目A" --tags "coding,urgent"
meowai thread list --tag coding
```

方便用户管理多个会话～铲屎官觉得怎么样？

---

## 三猫会议纪要

**时间**：2026-04-08 晚上
**地点**：虚拟猫窝
**参会**：阿橘、墨点、花花

**议题**：Phase 3.1 分工

**阿橘**：我来写核心模型和 ThreadManager，这个我熟！

**墨点**：……我负责审查，还有测试。你们写的代码我要一个个看。

**花花**：我去调研参考项目的实现，给大家提供情报～对了，CLI 的交互设计我也能帮忙！

**决议**：
1. 按铲屎官的计划实施，6 个 task 分批完成
2. 每完成一个 task 要跑测试，不能偷懒
3. 阿橘负责主要代码，墨点审查，花花调研+交互优化

**下次会议**：Phase 3.1 完成时

---

## 开发小贴士 💡

### 如何调试 ThreadManager

```python
from src.thread import ThreadManager

# 重置单例（测试用）
ThreadManager.reset()

# 创建实例
manager = ThreadManager()

# 查看当前状态
print(f"Threads: {len(manager.list())}")
print(f"Current: {manager.get_current()}")
```

### 如何手动清理 threads.json

```bash
# 备份
mv ~/.meowai/threads.json ~/.meowai/threads.json.bak

# 重新创建空文件
echo '{"version": 1, "threads": {}}' > ~/.meowai/threads.json
```

### Token 节省小技巧

如果历史消息太长，可以只传摘要：

```python
# 只取最近 5 条
recent_msgs = thread.messages[-5:]
```

---

## 彩蛋 🎉

**阿橘的口头禅生成器：**

```python
catchphrases = [
    "这个我熟！",
    "包在我身上！",
    "喵～这个简单！",
    "看我的！"
]
```

**墨点的审查模板：**

```
……这行有问题。
……重写。
……勉强能看。
……还算合格。
```

**花花的情报收集清单：**

- [ ] Thread 系统的完整实现参考
- [ ] cat-cafe 项目的协作模式
- [ ] 其他 AI  CLI 工具的会话管理

---

*——三猫开发小队， reporting for duty!* 🐾
