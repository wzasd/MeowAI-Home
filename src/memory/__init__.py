"""
三层记忆系统 — Episodic / Semantic / Procedural

Episodic:  对话片段存储（谁说了什么、什么时候、重要度）
Semantic:  知识图谱（实体、关系、标签）
Procedural: 工作流模式（技能使用记录、经验教训）

存储: SQLite (~/.meowai/memory.db)
"""
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class MemoryDB:
    """记忆数据库 — 管理三层记忆的 SQLite 存储"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path.home() / ".meowai" / "memory.db")
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        conn = self._get_conn()
        # === Episodic 记忆（对话片段）===
        conn.execute("""
            CREATE TABLE IF NOT EXISTS episodic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                cat_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 0,
                tags TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodic_thread
            ON episodic(thread_id, importance DESC)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_episodic_cat
            ON episodic(cat_id, created_at DESC)
        """)

        # === Semantic 记忆（知识图谱）===
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL DEFAULT 'concept',
                description TEXT,
                attributes TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES entities(id),
                FOREIGN KEY (target_id) REFERENCES entities(id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_relations_source
            ON relations(source_id, relation_type)
        """)

        # === Procedural 记忆（工作流模式）===
        conn.execute("""
            CREATE TABLE IF NOT EXISTS procedures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT DEFAULT 'workflow',
                steps TEXT DEFAULT '[]',
                trigger_conditions TEXT DEFAULT '[]',
                outcomes TEXT DEFAULT '{}',
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                last_used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_procedures_category
            ON procedures(category, last_used_at DESC)
        """)

        # === FTS5 全文搜索索引 ===
        # Episodic FTS
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS episodic_fts USING fts5(
                content, tags,
                content='episodic', content_rowid='rowid'
            )
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS episodic_ai AFTER INSERT ON episodic BEGIN
                INSERT INTO episodic_fts(rowid, content, tags)
                VALUES (new.rowid, new.content, new.tags);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS episodic_ad AFTER DELETE ON episodic BEGIN
                INSERT INTO episodic_fts(episodic_fts, rowid, content, tags)
                VALUES('delete', old.rowid, old.content, old.tags);
            END
        """)

        # Entity FTS
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
                name, description,
                content='entities', content_rowid='rowid'
            )
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS entities_ai AFTER INSERT ON entities BEGIN
                INSERT INTO entities_fts(rowid, name, description)
                VALUES (new.rowid, new.name, new.description);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS entities_ad AFTER DELETE ON entities BEGIN
                INSERT INTO entities_fts(entities_fts, rowid, name, description)
                VALUES('delete', old.rowid, old.name, old.description);
            END
        """)

        # Procedure FTS
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS procedures_fts USING fts5(
                name, steps,
                content='procedures', content_rowid='rowid'
            )
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS procedures_ai AFTER INSERT ON procedures BEGIN
                INSERT INTO procedures_fts(rowid, name, steps)
                VALUES (new.rowid, new.name, new.steps);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS procedures_ad AFTER DELETE ON procedures BEGIN
                INSERT INTO procedures_fts(procedures_fts, rowid, name, steps)
                VALUES('delete', old.rowid, old.name, old.steps);
            END
        """)

        # === 键值记忆（向后兼容 Phase 4.3）===
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (key, category)
            )
        """)

        conn.commit()
        conn.close()


# =============================================
# Episodic Memory — 对话片段
# =============================================

class EpisodicMemory:
    """Episodic 记忆 — 对话片段存储"""

    def __init__(self, db: MemoryDB):
        self.db = db

    def store(
        self,
        thread_id: str,
        role: str,
        content: str,
        cat_id: str = None,
        importance: int = 0,
        tags: List[str] = None
    ) -> int:
        """存储对话片段"""
        conn = self.db._get_conn()
        cursor = conn.execute(
            """INSERT INTO episodic (thread_id, cat_id, role, content, importance, tags)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (thread_id, cat_id, role, content, importance, json.dumps(tags or []))
        )
        conn.commit()
        episode_id = cursor.lastrowid
        conn.close()
        return episode_id

    def recall_by_thread(
        self,
        thread_id: str,
        limit: int = 20,
        min_importance: int = 0
    ) -> List[Dict[str, Any]]:
        """按 Thread 检索对话片段"""
        conn = self.db._get_conn()
        rows = conn.execute(
            """SELECT id, thread_id, cat_id, role, content, importance, tags, created_at
               FROM episodic
               WHERE thread_id = ? AND importance >= ?
               ORDER BY importance DESC, created_at DESC LIMIT ?""",
            (thread_id, min_importance, limit)
        ).fetchall()
        conn.close()
        return [self._row_to_dict(r) for r in rows]

    def recall_by_cat(
        self,
        cat_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """按猫检索对话片段"""
        conn = self.db._get_conn()
        rows = conn.execute(
            """SELECT id, thread_id, cat_id, role, content, importance, tags, created_at
               FROM episodic WHERE cat_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (cat_id, limit)
        ).fetchall()
        conn.close()
        return [self._row_to_dict(r) for r in rows]

    def search(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """搜索对话片段（FTS5）"""
        conn = self.db._get_conn()
        try:
            rows = conn.execute(
                """SELECT e.id, e.thread_id, e.cat_id, e.role, e.content,
                          e.importance, e.tags, e.created_at
                   FROM episodic_fts fts
                   JOIN episodic e ON e.rowid = fts.rowid
                   WHERE episodic_fts MATCH ?
                   ORDER BY e.importance DESC, fts.rank
                   LIMIT ?""",
                (query, limit)
            ).fetchall()
            if not rows:
                raise ValueError("FTS5 returned no results, fallback to LIKE")
        except Exception:
            # FTS5 MATCH syntax error or empty results → fallback to LIKE
            rows = conn.execute(
                """SELECT id, thread_id, cat_id, role, content, importance, tags, created_at
                   FROM episodic WHERE content LIKE ?
                   ORDER BY importance DESC, created_at DESC LIMIT ?""",
                (f"%{query}%", limit)
            ).fetchall()
        conn.close()
        return [self._row_to_dict(r) for r in rows]

    def recall_important(self, limit: int = 10) -> List[Dict[str, Any]]:
        """检索重要片段"""
        conn = self.db._get_conn()
        rows = conn.execute(
            """SELECT id, thread_id, cat_id, role, content, importance, tags, created_at
               FROM episodic WHERE importance >= 5
               ORDER BY importance DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        conn.close()
        return [self._row_to_dict(r) for r in rows]

    def _row_to_dict(self, row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "thread_id": row["thread_id"],
            "cat_id": row["cat_id"],
            "role": row["role"],
            "content": row["content"],
            "importance": row["importance"],
            "tags": json.loads(row["tags"]),
            "created_at": row["created_at"]
        }


# =============================================
# Semantic Memory — 知识图谱
# =============================================

class SemanticMemory:
    """Semantic 记忆 — 知识图谱"""

    def __init__(self, db: MemoryDB):
        self.db = db

    def add_entity(
        self,
        name: str,
        entity_type: str = "concept",
        description: str = "",
        attributes: Dict[str, Any] = None
    ) -> int:
        """添加实体"""
        conn = self.db._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO entities (name, type, description, attributes)
                   VALUES (?, ?, ?, ?)""",
                (name, entity_type, description, json.dumps(attributes or {}))
            )
            conn.commit()
            entity_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            # 实体已存在，更新
            conn.execute(
                """UPDATE entities SET description = ?, attributes = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE name = ?""",
                (description, json.dumps(attributes or {}), name)
            )
            conn.commit()
            entity_id = conn.execute(
                "SELECT id FROM entities WHERE name = ?", (name,)
            ).fetchone()["id"]
        conn.close()
        return entity_id

    def add_relation(
        self,
        source_name: str,
        target_name: str,
        relation_type: str,
        strength: float = 1.0
    ) -> int:
        """添加关系"""
        conn = self.db._get_conn()
        # 获取实体 ID
        source = conn.execute(
            "SELECT id FROM entities WHERE name = ?", (source_name,)
        ).fetchone()
        target = conn.execute(
            "SELECT id FROM entities WHERE name = ?", (target_name,)
        ).fetchone()

        if not source or not target:
            conn.close()
            raise ValueError(f"Entity not found: {source_name} or {target_name}")

        cursor = conn.execute(
            """INSERT INTO relations (source_id, target_id, relation_type, strength)
               VALUES (?, ?, ?, ?)""",
            (source["id"], target["id"], relation_type, strength)
        )
        conn.commit()
        rel_id = cursor.lastrowid
        conn.close()
        return rel_id

    def get_entity(self, name: str) -> Optional[Dict[str, Any]]:
        """获取实体"""
        conn = self.db._get_conn()
        row = conn.execute(
            "SELECT id, name, type, description, attributes, created_at FROM entities WHERE name = ?",
            (name,)
        ).fetchone()
        if not row:
            conn.close()
            return None

        # 获取关系
        relations = conn.execute(
            """SELECT e.name, r.relation_type, r.strength
               FROM relations r JOIN entities e ON r.target_id = e.id
               WHERE r.source_id = ?""",
            (row["id"],)
        ).fetchall()

        conn.close()
        return {
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "description": row["description"],
            "attributes": json.loads(row["attributes"]),
            "relations": [
                {"target": r["name"], "type": r["relation_type"], "strength": r["strength"]}
                for r in relations
            ],
            "created_at": row["created_at"]
        }

    def search_entities(
        self,
        query: str,
        entity_type: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """搜索实体（FTS5）"""
        conn = self.db._get_conn()
        try:
            if entity_type:
                rows = conn.execute(
                    """SELECT e.id, e.name, e.type, e.description
                       FROM entities_fts fts
                       JOIN entities e ON e.rowid = fts.rowid
                       WHERE entities_fts MATCH ? AND e.type = ?
                       ORDER BY fts.rank
                       LIMIT ?""",
                    (query, entity_type, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT e.id, e.name, e.type, e.description
                       FROM entities_fts fts
                       JOIN entities e ON e.rowid = fts.rowid
                       WHERE entities_fts MATCH ?
                       ORDER BY fts.rank
                       LIMIT ?""",
                    (query, limit)
                ).fetchall()
            if not rows:
                raise ValueError("FTS5 returned no results, fallback to LIKE")
        except Exception:
            # FTS5 MATCH syntax error or empty results → fallback to LIKE
            if entity_type:
                rows = conn.execute(
                    """SELECT id, name, type, description FROM entities
                       WHERE (name LIKE ? OR description LIKE ?) AND type = ?
                       LIMIT ?""",
                    (f"%{query}%", f"%{query}%", entity_type, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT id, name, type, description FROM entities
                       WHERE name LIKE ? OR description LIKE ?
                       LIMIT ?""",
                    (f"%{query}%", f"%{query}%", limit)
                ).fetchall()
        conn.close()
        return [
            {"id": r["id"], "name": r["name"], "type": r["type"], "description": r["description"]}
            for r in rows
        ]

    def get_related(
        self,
        name: str,
        relation_type: str = None,
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """获取关联实体（支持多跳 BFS）"""
        conn = self.db._get_conn()
        entity = conn.execute(
            "SELECT id FROM entities WHERE name = ?", (name,)
        ).fetchone()
        if not entity:
            conn.close()
            return []

        start_id = entity["id"]
        visited = {start_id}
        results = []
        queue = [(start_id, 1)]

        while queue:
            current_id, depth = queue.pop(0)
            if depth > max_depth:
                continue

            if relation_type:
                rows = conn.execute(
                    """SELECT e.id, e.name, e.type, r.relation_type, r.strength
                       FROM relations r JOIN entities e ON r.target_id = e.id
                       WHERE r.source_id = ? AND r.relation_type = ?""",
                    (current_id, relation_type)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT e.id, e.name, e.type, r.relation_type, r.strength
                       FROM relations r JOIN entities e ON r.target_id = e.id
                       WHERE r.source_id = ?""",
                    (current_id,)
                ).fetchall()

            for row in rows:
                results.append({
                    "name": row["name"], "type": row["type"],
                    "relation": row["relation_type"], "strength": row["strength"],
                    "depth": depth,
                })
                if row["id"] not in visited:
                    visited.add(row["id"])
                    queue.append((row["id"], depth + 1))

        conn.close()
        return results


# =============================================
# Procedural Memory — 工作流模式
# =============================================

class ProceduralMemory:
    """Procedural 记忆 — 工作流模式"""

    def __init__(self, db: MemoryDB):
        self.db = db

    def store_procedure(
        self,
        name: str,
        category: str = "workflow",
        steps: List[str] = None,
        trigger_conditions: List[str] = None,
        outcomes: Dict[str, Any] = None
    ) -> int:
        """存储工作流模式"""
        conn = self.db._get_conn()
        cursor = conn.execute(
            """INSERT INTO procedures (name, category, steps, trigger_conditions, outcomes)
               VALUES (?, ?, ?, ?, ?)""",
            (name, category, json.dumps(steps or []),
             json.dumps(trigger_conditions or []),
             json.dumps(outcomes or {}))
        )
        conn.commit()
        proc_id = cursor.lastrowid
        conn.close()
        return proc_id

    def record_use(self, procedure_id: int, success: bool = True):
        """记录使用结果"""
        conn = self.db._get_conn()
        if success:
            conn.execute(
                """UPDATE procedures SET success_count = success_count + 1, last_used_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (procedure_id,)
            )
        else:
            conn.execute(
                """UPDATE procedures SET fail_count = fail_count + 1, last_used_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (procedure_id,)
            )
        conn.commit()
        conn.close()

    def get_by_category(self, category: str, limit: int = 20) -> List[Dict[str, Any]]:
        """按分类查询"""
        conn = self.db._get_conn()
        rows = conn.execute(
            """SELECT id, name, category, steps, trigger_conditions, outcomes,
                      success_count, fail_count, last_used_at, created_at
               FROM procedures WHERE category = ?
               ORDER BY last_used_at DESC LIMIT ?""",
            (category, limit)
        ).fetchall()
        conn.close()
        return [self._row_to_dict(r) for r in rows]

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索工作流（FTS5）"""
        conn = self.db._get_conn()
        try:
            rows = conn.execute(
                """SELECT p.id, p.name, p.category, p.steps, p.trigger_conditions,
                          p.outcomes, p.success_count, p.fail_count, p.last_used_at, p.created_at
                   FROM procedures_fts fts
                   JOIN procedures p ON p.rowid = fts.rowid
                   WHERE procedures_fts MATCH ?
                   ORDER BY p.success_count DESC
                   LIMIT ?""",
                (query, limit)
            ).fetchall()
            if not rows:
                raise ValueError("FTS5 returned no results, fallback to LIKE")
        except Exception:
            # FTS5 MATCH syntax error or empty results → fallback to LIKE
            rows = conn.execute(
                """SELECT id, name, category, steps, trigger_conditions, outcomes,
                          success_count, fail_count, last_used_at, created_at
                   FROM procedures WHERE name LIKE ? OR steps LIKE ?
                   ORDER BY success_count DESC LIMIT ?""",
                (f"%{query}%", f"%{query}%", limit)
            ).fetchall()
        conn.close()
        return [self._row_to_dict(r) for r in rows]

    def get_best_practices(self, min_successes: int = 3, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最佳实践（成功率最高的模式）"""
        conn = self.db._get_conn()
        rows = conn.execute(
            """SELECT id, name, category, steps, trigger_conditions, outcomes,
                      success_count, fail_count, last_used_at, created_at
               FROM procedures WHERE success_count >= ?
               ORDER BY (CAST(success_count AS REAL) / (success_count + fail_count + 1)) DESC
               LIMIT ?""",
            (min_successes, limit)
        ).fetchall()
        conn.close()
        return [self._row_to_dict(r) for r in rows]

    def _row_to_dict(self, row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "steps": json.loads(row["steps"]),
            "trigger_conditions": json.loads(row["trigger_conditions"]),
            "outcomes": json.loads(row["outcomes"]),
            "success_count": row["success_count"],
            "fail_count": row["fail_count"],
            "last_used_at": row["last_used_at"],
            "created_at": row["created_at"]
        }

    def find_by_name_category(self, name: str, category: str) -> Optional[Dict[str, Any]]:
        """Find procedure by exact name+category match for deduplication."""
        conn = self.db._get_conn()
        row = conn.execute(
            """SELECT id, name, category, steps, success_count, fail_count
               FROM procedures WHERE name = ? AND category = ?""",
            (name, category)
        ).fetchone()
        conn.close()
        if row:
            return {
                "id": row["id"], "name": row["name"], "category": row["category"],
                "success_count": row["success_count"], "fail_count": row["fail_count"],
            }
        return None


# =============================================
# MemoryService — 统一检索服务
# =============================================

class MemoryService:
    """
    统一记忆服务 — 整合三层记忆

    使用方式:
        service = MemoryService()
        context = service.build_context("用户问题")  # 自动检索相关记忆
        service.store_episode(thread_id, role, content)  # 自动存储对话
    """

    def __init__(self, db_path: str = None):
        self.db = MemoryDB(db_path)
        self.episodic = EpisodicMemory(self.db)
        self.semantic = SemanticMemory(self.db)
        self.procedural = ProceduralMemory(self.db)

    def store_episode(
        self,
        thread_id: str,
        role: str,
        content: str,
        cat_id: str = None,
        importance: int = 0,
        tags: List[str] = None
    ) -> int:
        """存储对话片段到 Episodic 记忆"""
        return self.episodic.store(thread_id, role, content, cat_id, importance, tags)

    def build_context(
        self,
        query: str,
        thread_id: str = None,
        max_items: int = 5
    ) -> str:
        """
        构建记忆上下文（注入系统提示）

        自动从三层记忆中检索与 query 相关的内容
        """
        parts = []

        # 拆分搜索词，每个词单独搜索
        keywords = query.replace("的", " ").split()
        all_episodes = []
        all_entities = []
        all_procedures = []

        for kw in keywords:
            if len(kw) < 2:
                continue
            all_episodes.extend(self.episodic.search(kw, limit=max_items))
            all_entities.extend(self.semantic.search_entities(kw, limit=3))
            all_procedures.extend(self.procedural.search(kw, limit=2))

        # 去重
        seen_ep = set()
        seen_ent = set()
        episodes = []
        for ep in all_episodes:
            if ep["id"] not in seen_ep:
                seen_ep.add(ep["id"])
                episodes.append(ep)
        entities = []
        for ent in all_entities:
            if ent["id"] not in seen_ent:
                seen_ent.add(ent["id"])
                entities.append(ent)

        # 1. Episodic
        if episodes:
            parts.append("## 相关对话记忆")
            for ep in episodes[:3]:
                cat = ep["cat_id"] or "user"
                parts.append(f"- [{cat}] {ep['content'][:100]}")

        # 2. Semantic
        if entities:
            parts.append("\n## 相关知识")
            for ent in entities:
                desc = ent.get("description", "")[:80]
                parts.append(f"- **{ent['name']}** ({ent['type']}): {desc}")

        # 3. Procedural
        if all_procedures:
            parts.append("\n## 相关经验")
            for proc in all_procedures[:2]:
                success_rate = proc["success_count"] / max(proc["success_count"] + proc["fail_count"], 1)
                parts.append(f"- **{proc['name']}** (成功率: {success_rate:.0%})")

        # 4. Thread 特定记忆
        if thread_id:
            thread_episodes = self.episodic.recall_by_thread(thread_id, limit=3, min_importance=3)
            if thread_episodes:
                parts.append("\n## 本会话重要记忆")
                for ep in thread_episodes:
                    cat = ep["cat_id"] or "user"
                    parts.append(f"- [{cat}] {ep['content'][:100]}")

        if not parts:
            return ""

        return "\n".join(parts)
