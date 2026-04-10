"""三层记忆系统测试"""
import pytest
import sqlite3
import tempfile
from pathlib import Path

from src.memory import (
    MemoryDB, EpisodicMemory, SemanticMemory,
    ProceduralMemory, MemoryService
)


@pytest.fixture
def db():
    """创建临时数据库"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_memory.db")
        yield MemoryDB(db_path)


@pytest.fixture
def episodic(db):
    return EpisodicMemory(db)


@pytest.fixture
def semantic(db):
    return SemanticMemory(db)


@pytest.fixture
def procedural(db):
    return ProceduralMemory(db)


@pytest.fixture
def service(db):
    return MemoryService(db.db_path)


# === Episodic 记忆测试 ===

class TestEpisodicMemory:
    def test_store_and_recall(self, episodic):
        ep_id = episodic.store("thread1", "user", "帮我写代码", importance=5)
        assert ep_id > 0

        results = episodic.recall_by_thread("thread1")
        assert len(results) == 1
        assert results[0]["content"] == "帮我写代码"
        assert results[0]["importance"] == 5

    def test_recall_by_cat(self, episodic):
        episodic.store("t1", "assistant", "内容1", cat_id="orange")
        episodic.store("t1", "assistant", "内容2", cat_id="inky")

        results = episodic.recall_by_cat("orange")
        assert len(results) == 1
        assert results[0]["cat_id"] == "orange"

    def test_search(self, episodic):
        episodic.store("t1", "user", "写一个排序算法")
        episodic.store("t1", "user", "今天天气不错")

        results = episodic.search("排序")
        assert len(results) == 1
        assert "排序" in results[0]["content"]

    def test_importance_filter(self, episodic):
        episodic.store("t1", "user", "重要决定", importance=8)
        episodic.store("t1", "user", "闲聊", importance=1)

        results = episodic.recall_by_thread("t1", min_importance=5)
        assert len(results) == 1
        assert results[0]["content"] == "重要决定"

    def test_recall_important(self, episodic):
        episodic.store("t1", "user", "一般", importance=2)
        episodic.store("t2", "assistant", "关键决策", importance=9, cat_id="orange")

        results = episodic.recall_important()
        assert len(results) == 1
        assert results[0]["importance"] == 9

    def test_tags(self, episodic):
        episodic.store("t1", "user", "tagged", tags=["bug", "critical"])
        results = episodic.recall_by_thread("t1")
        assert "bug" in results[0]["tags"]

    def test_empty_recall(self, episodic):
        results = episodic.recall_by_thread("nonexistent")
        assert len(results) == 0


# === Semantic 记忆测试 ===

class TestSemanticMemory:
    def test_add_entity(self, semantic):
        eid = semantic.add_entity("Python", "language", "编程语言")
        assert eid > 0

        entity = semantic.get_entity("Python")
        assert entity is not None
        assert entity["name"] == "Python"
        assert entity["type"] == "language"

    def test_add_relation(self, semantic):
        semantic.add_entity("Django", "framework", "Web 框架")
        semantic.add_entity("Python", "language", "编程语言")
        rid = semantic.add_relation("Django", "Python", "depends_on")
        assert rid > 0

        entity = semantic.get_entity("Django")
        assert len(entity["relations"]) == 1
        assert entity["relations"][0]["target"] == "Python"

    def test_entity_not_found(self, semantic):
        assert semantic.get_entity("nonexistent") is None

    def test_search_entities(self, semantic):
        semantic.add_entity("React", "framework", "前端框架")
        semantic.add_entity("Redis", "database", "内存数据库")

        results = semantic.search_entities("框架")
        assert len(results) >= 1

    def test_search_by_type(self, semantic):
        semantic.add_entity("Python", "language", "")
        semantic.add_entity("Redis", "database", "")

        results = semantic.search_entities("", entity_type="language")
        assert len(results) == 1
        assert results[0]["name"] == "Python"

    def test_get_related(self, semantic):
        semantic.add_entity("MeowAI", "project", "")
        semantic.add_entity("Claude", "model", "")
        semantic.add_relation("MeowAI", "Claude", "uses")

        related = semantic.get_related("MeowAI")
        assert len(related) == 1
        assert related[0]["name"] == "Claude"

    def test_update_entity(self, semantic):
        semantic.add_entity("test", "concept", "原始描述")
        semantic.add_entity("test", "concept", "更新描述")

        entity = semantic.get_entity("test")
        assert entity["description"] == "更新描述"

    def test_relation_to_missing_entity(self, semantic):
        with pytest.raises(ValueError):
            semantic.add_relation("不存在A", "不存在B", "relates_to")


# === Procedural 记忆测试 ===

class TestProceduralMemory:
    def test_store_procedure(self, procedural):
        pid = procedural.store_procedure(
            "TDD 开发",
            category="development",
            steps=["写测试", "实现", "重构"],
            trigger_conditions=["写代码", "新功能"]
        )
        assert pid > 0

    def test_record_use(self, procedural):
        pid = procedural.store_procedure("测试流程", steps=["step1"])
        procedural.record_use(pid, success=True)
        procedural.record_use(pid, success=True)
        procedural.record_use(pid, success=False)

        results = procedural.get_by_category("workflow")
        assert len(results) == 1
        assert results[0]["success_count"] == 2
        assert results[0]["fail_count"] == 1

    def test_search_procedure(self, procedural):
        procedural.store_procedure("代码审查流程", steps=["review"])
        procedural.store_procedure("部署流程", steps=["deploy"])

        results = procedural.search("审查")
        assert len(results) == 1
        assert "审查" in results[0]["name"]

    def test_best_practices(self, procedural):
        p1 = procedural.store_procedure("好流程", steps=["good"])
        p2 = procedural.store_procedure("差流程", steps=["bad"])

        for _ in range(5):
            procedural.record_use(p1, success=True)
        for _ in range(3):
            procedural.record_use(p2, success=False)

        best = procedural.get_best_practices(min_successes=3)
        assert len(best) == 1
        assert best[0]["name"] == "好流程"

    def test_empty_category(self, procedural):
        results = procedural.get_by_category("nonexistent")
        assert len(results) == 0


# === MemoryService 统一服务测试 ===

class TestMemoryService:
    def test_store_and_build_context(self, service):
        service.store_episode("t1", "user", "排序算法怎么实现？", importance=5)
        service.semantic.add_entity("快速排序", "algorithm", "O(n log n) 排序算法")

        context = service.build_context("排序")
        assert "排序" in context
        assert "快速排序" in context

    def test_build_context_empty(self, service):
        context = service.build_context("什么都没有")
        assert context == ""

    def test_build_context_with_thread(self, service):
        service.store_episode("thread1", "user", "重要决定", importance=8)
        context = service.build_context("决定", thread_id="thread1")
        assert "重要决定" in context

    def test_full_workflow(self, service):
        """完整工作流：存储 → 检索 → 构建上下文"""
        # 存储对话
        service.store_episode("t1", "user", "用 React 写前端", importance=3)
        service.store_episode("t1", "assistant", "好的，开始写组件", cat_id="orange", importance=2)

        # 存储知识
        service.semantic.add_entity("React", "framework", "前端框架")
        service.semantic.add_entity("组件", "concept", "UI 构建块")
        service.semantic.add_relation("React", "组件", "uses")

        # 存储经验
        pid = service.procedural.store_procedure(
            "前端开发流程",
            category="development",
            steps=["设计组件", "写代码", "测试"]
        )
        service.procedural.record_use(pid, success=True)

        # 构建上下文
        context = service.build_context("React 前端")
        assert "React" in context


# === FTS5 搜索测试 ===

class TestFTS5Search:
    def test_episodic_fts5_search(self, episodic):
        """FTS5 search returns results ranked by relevance"""
        episodic.store("t1", "user", "React 是一个前端框架", importance=3)
        episodic.store("t2", "user", "今天讨论了 Vue 框架", importance=3)
        episodic.store("t3", "user", "React 组件设计模式", importance=5)

        results = episodic.search("React")
        assert len(results) == 2
        # Higher importance result should rank first
        assert results[0]["importance"] == 5

    def test_episodic_fts5_empty_search(self, episodic):
        """FTS5 search returns empty for no matches"""
        episodic.store("t1", "user", "Hello world")
        results = episodic.search("不存在的内容xyz")
        assert len(results) == 0

    def test_semantic_fts5_search(self, semantic):
        """Semantic FTS5 search across name and description"""
        semantic.add_entity("TypeScript", "language", "JavaScript 的超集，添加了类型系统")
        semantic.add_entity("Python", "language", "通用编程语言")

        results = semantic.search_entities("类型")
        assert len(results) >= 1

    def test_procedural_fts5_search(self, procedural):
        """Procedural FTS5 search across name and steps"""
        procedural.store_procedure(
            "代码审查", steps=["阅读代码", "提出建议", "确认修改"]
        )
        procedural.store_procedure(
            "部署", steps=["构建镜像", "推送 registry"]
        )

        results = procedural.search("审查")
        assert len(results) == 1
        assert "审查" in results[0]["name"]

    def test_fts5_delete_sync(self, episodic):
        """FTS5 index is synced on delete"""
        eid = episodic.store("t1", "user", "unique_marker_text_abc")
        results = episodic.search("unique_marker_text_abc")
        assert len(results) == 1

        conn = episodic.db._get_conn()
        conn.execute("DELETE FROM episodic WHERE id = ?", (eid,))
        conn.commit()
        conn.close()

        # After delete, re-search. Note: with content= mode, we need to manually
        # notify FTS5 of the deletion. Since the trigger handles it, the FTS index
        # should be updated.
        results = episodic.search("unique_marker_text_abc")
        assert len(results) == 0
