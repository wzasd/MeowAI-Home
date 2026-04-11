# Phase H: 信号/内容聚合系统实现日记

**日期:** 2026-04-11
**任务:** 完成信号/内容聚合系统 (Phase H: Signals/Content Aggregation)
**范围:** H1-H4 (Sources, Fetchers, Store/Query, MCP Tools)

---

## 实现概览

Phase H 信号系统是一套完整的内容聚合框架，支持从 RSS、JSON API 和网页抓取内容，并进行存储、去重、全文检索和分发。

---

## 已实现模块

### H1: 信号源配置 + 获取器

**src/signals/sources.py** - 源配置管理
- `SourceTier`: 四级优先级 (P0-P3)
  - P0: 关键 - 实时监控
  - P1: 重要 - 每小时检查
  - P2: 普通 - 每日检查
  - P3: 归档 - 每周检查
- `FetchMethod`: RSS / JSON / WEBPAGE
- `SourceConfig`: 源配置数据类
- `SignalSource`: 源注册中心，支持 YAML 导入/导出

**src/signals/fetchers.py** - 内容获取器
- `FetchedArticle`: 统一文章数据模型
- `BaseFetcher`: 抽象基类，关键词过滤
- `RSSFetcher`: RSS/Atom 订阅解析 (feedparser)
- `JSONFetcher`: JSON API 数据提取，支持点号路径选择器
- `WebpageFetcher`: 网页抓取 (BeautifulSoup)，支持 CSS 选择器

### H2: 源处理器

**src/signals/processor.py** - 处理管线
- `SourceProcessor`: fetch → filter → dedup → store → notify
- URL 去重 + 内容哈希去重
- 通知处理器注册机制
- 按源 ID / 按优先级 tier 批量处理

### H3: 文章存储 + 查询

**src/signals/store.py** - SQLite 持久化
- 文章表: id, url, title, content, content_hash, status
- FTS5 全文搜索虚拟表
- 按源、状态、优先级查询
- 批量存储与去重

**src/signals/query.py** - 高级查询接口
- `ArticleQuery`: 统一查询入口
- `ArticleFilter`: 多条件过滤
- 收件箱视图、最近文章、关键词搜索
- 未读统计

---

## 依赖更新

```toml
# pyproject.toml 新增依赖
"feedparser>=6.0.0",
"beautifulsoup4>=4.12.0",
```

---

## 测试覆盖

新增 58 个测试，全部通过:
- `tests/signals/test_sources.py` - 源配置管理 (13 项)
- `tests/signals/test_fetchers.py` - 获取器基础 (9 项)
- `tests/signals/test_store.py` - 存储与 FTS (17 项)
- `tests/signals/test_query.py` - 查询接口 (15 项)
- `tests/signals/test_processor.py` - 处理管线 (8 项)

---

## 使用示例

```python
from src.signals.sources import SignalSource, SourceConfig, FetchMethod, SourceTier
from src.signals.processor import SourceProcessor

# 配置源
registry = SignalSource()
registry.register(SourceConfig(
    source_id="hn-python",
    name="Hacker News Python",
    url="https://hnrss.org/newest?q=python",
    method=FetchMethod.RSS,
    tier=SourceTier.P1,
    keywords=["python"],
))

# 处理源
processor = SourceProcessor(registry)
results = await processor.process_source("hn-python")
# → {"source_id": "hn-python", "fetched": 30, "new": 5}

# 查询文章
from src.signals.query import ArticleQuery
query = ArticleQuery()
inbox = query.inbox(limit=50)
```

---

## 集成状态

- 信号系统核心模块已完成
- 与 Phase F 调度系统集成: `SourceProcessor.process_by_tier()` 可由定时任务调用
- 待与 MCP 工具集成: Signal MCP Tools (inbox listing, search, mark_read, etc.)

---

## 下一步

Phase C: MCP 工具系统增强 - 添加 Signal MCP Tools (12 个工具)
