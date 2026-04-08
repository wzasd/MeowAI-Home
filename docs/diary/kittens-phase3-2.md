# 🐱 小猫开发笔记 - Phase 3.2

**日期**: 2026-04-08
**阶段**: Phase 3.2 - SQLite 持久化

---

## 阿橘的 SQLite 学习笔记 🍊

喵！Phase 3.1 刚搞完，铲屎官又要上 SQLite 了。

**我学到的：**

JSON 文件虽然简单，但是：
- 每次都要全量读写（慢）
- 不能搜索（找东西麻烦）
- 容易损坏（一崩全没）

SQLite 就厉害了：
- 增量更新（只改需要改的）
- SQL 查询（想搜啥搜啥）
- 事务安全（崩了也能恢复）

**我的疑问：**

从 JSON 迁移到 SQLite，用户的数据会不会丢？

铲屎官说要写个 migration 脚本，自动把旧数据搬过去。这个好，用户无感知升级！

**TODO：**
- [ ] 学习 aiosqlite 异步 API
- [ ] 设计 threads 和 messages 表结构
- [ ] 写迁移脚本

**口头禅：**
> "这个迁移脚本... 包在我身上！"

---

## 墨点的数据库审查 🐄

……看了铲屎官的表结构设计，基本合格。

**Schema 检查：**

```sql
CREATE TABLE threads (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    current_cat_id TEXT NOT NULL,
    is_archived INTEGER DEFAULT 0
);
```

**问题 1：时间戳用 TEXT**

虽然 ISO 8601 字符串可以排序，但最好用 REAL (Unix timestamp) 或 INTEGER。

不过铲屎官说 Python 的 datetime 转换方便，勉强接受。

**问题 2：缺少外键约束检查**

SQLite 默认关闭外键检查，需要：
```python
await db.execute("PRAGMA foreign_keys = ON")
```

**问题 3：索引设计**

```sql
CREATE INDEX idx_messages_thread ON messages(thread_id, timestamp);
```

这个索引好，查询某个 thread 的消息时会用到。

**建议：**

1. 加 `PRAGMA foreign_keys = ON`
2. 考虑 fts5 扩展做全文搜索（不只是 LIKE）
3. 定期 VACUUM 清理碎片

**评分：** 8/10，比 JSON 靠谱多了。

---

## 花花的调研报告 🌸

我打听到的消息～

**aiosqlite vs sqlite3：**

| 库 | 同步/异步 | 特点 |
|---|----------|------|
| sqlite3 | 同步 | 标准库，简单 |
| aiosqlite | 异步 | 适配 asyncio，线程安全 |

**我们用 aiosqlite 是对的**，因为：
- 我们的服务层已经是异步的
- 避免阻塞事件循环
- 支持并发操作

**迁移策略：**

参考了 Alembic（SQLAlchemy 的迁移工具），但对我们来说太重了。

铲屎官的简单方案够用了：
1. 检查 SQLite 文件是否存在
2. 不存在则检查 JSON 文件
3. 有 JSON 就迁移，没有就初始化空库

**要不要加 fts5？**

SQLite 的 fts5 扩展可以做全文搜索，比 `LIKE '%keyword%'` 快多了。

但铲屎官说 Phase 3.2 先不做，后面再加。

**结论：** 支持铲屎官的决策，先保证功能可用，再优化性能。

---

## 三猫技术讨论会

**议题**：`--resume` 功能设计

**阿橘**：我觉得应该自动恢复上次会话，不用加 `--resume` 参数。

**墨点**：……不行。用户可能想开新会话，自动恢复会打断思路。

**花花**：可以做个提示："检测到上次会话 '项目A'，是否恢复？ [Y/n]"

**决议**：
- 默认不自动恢复
- `meowai chat --resume` 显式恢复
- 显示上次会话信息，让用户选择

---

## 代码审查清单

### 数据库操作
- [ ] 使用 `async with` 管理连接
- [ ] 开启外键检查
- [ ] 事务提交/回滚
- [ ] 异常处理

### 迁移脚本
- [ ] 备份 JSON 文件
- [ ] 原子性迁移
- [ ] 失败回滚
- [ ] 迁移后验证

### 测试
- [ ] 单元测试（CRUD）
- [ ] 集成测试（端到端）
- [ ] 迁移测试
- [ ] 并发测试

---

## 性能优化建议

### 查询优化
```python
# 坏的：全表扫描
cursor = await db.execute("SELECT * FROM messages WHERE content LIKE '%keyword%'")

# 好的：使用索引
cursor = await db.execute("SELECT * FROM messages WHERE thread_id = ?", (thread_id,))
```

### 批量插入
```python
# 批量插入比单条快
await db.executemany(
    "INSERT INTO messages (thread_id, content) VALUES (?, ?)",
    [(t1, c1), (t2, c2), (t3, c3)]
)
```

---

## 彩蛋：SQL 注入防护 🛡️

**错误示范**（字符串拼接）：
```python
query = f"SELECT * FROM threads WHERE name = '{user_input}'"
# 用户输入：' OR '1'='1
# 结果：SELECT * FROM threads WHERE name = '' OR '1'='1'
# 返回所有数据！
```

**正确做法**（参数化查询）：
```python
await db.execute("SELECT * FROM threads WHERE name = ?", (user_input,))
```

**阿橘的评价**：
> "SQL 注入？这个我熟！用参数化查询就完事了喵～"

---

*Phase 3.2，让数据更安全！* 🐾
