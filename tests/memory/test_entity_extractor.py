"""Entity extractor tests"""
import pytest
from src.memory.entity_extractor import extract_entities


class TestExtractEntities:
    def test_preference(self):
        results = extract_entities("用户喜欢React，也常用Python")
        assert len(results) >= 1
        names = [r[0] for r in results]
        assert "React" in names
        types = [r[1] for r in results]
        assert "preference" in types

    def test_technology(self):
        results = extract_entities("项目使用 SQLite 数据库")
        assert len(results) >= 1
        names = [r[0] for r in results]
        assert "SQLite" in names
        types = [r[1] for r in results]
        assert "technology" in types

    def test_constraint(self):
        results = extract_entities("不能用jQuery")
        assert len(results) >= 1
        names = [r[0] for r in results]
        assert "jQuery" in names
        types = [r[1] for r in results]
        assert "constraint" in types

    def test_role(self):
        results = extract_entities("阿橘负责前端开发")
        assert len(results) >= 1
        names = [r[0] for r in results]
        assert "阿橘" in names
        types = [r[1] for r in results]
        assert "role" in types

    def test_multiple_entities(self):
        text = "用户喜欢React，项目使用SQLite，不能用jQuery"
        results = extract_entities(text)
        assert len(results) >= 3
        types = {r[1] for r in results}
        assert "preference" in types
        assert "technology" in types
        assert "constraint" in types

    def test_no_match(self):
        results = extract_entities("今天天气不错")
        assert len(results) == 0

    def test_empty_string(self):
        results = extract_entities("")
        assert len(results) == 0
