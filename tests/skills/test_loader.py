"""SkillLoader tests"""
import pytest
from pathlib import Path

from src.skills.loader import SkillLoader


@pytest.fixture
def valid_skill(tmp_path):
    """创建有效的测试技能"""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: Test Skill
description: A test skill for unit testing
triggers:
  - "test"
  - "测试"
---

# Test Skill Content

This is the body of the test skill.
""")

    return skill_dir


@pytest.fixture
def invalid_skill_missing_fields(tmp_path):
    """创建缺少必需字段的技能"""
    skill_dir = tmp_path / "invalid-skill"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: Invalid Skill
---

# Missing description field
""")

    return skill_dir


@pytest.fixture
def skill_no_frontmatter(tmp_path):
    """创建没有 frontmatter 的技能"""
    skill_dir = tmp_path / "no-frontmatter"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""# No Frontmatter

Just markdown content without YAML frontmatter.
""")

    return skill_dir


def test_load_valid_skill(valid_skill):
    """测试加载有效技能"""
    loader = SkillLoader()
    skill_data = loader.load_skill(valid_skill)

    assert skill_data["metadata"]["name"] == "Test Skill"
    assert skill_data["metadata"]["description"] == "A test skill for unit testing"
    assert "test" in skill_data["metadata"]["triggers"]
    assert "Test Skill Content" in skill_data["content"]
    assert skill_data["path"] == valid_skill


def test_load_nonexistent_skill(tmp_path):
    """测试加载不存在的技能"""
    loader = SkillLoader()
    nonexistent = tmp_path / "nonexistent"

    with pytest.raises(FileNotFoundError, match="SKILL.md not found"):
        loader.load_skill(nonexistent)


def test_load_skill_missing_required_fields(invalid_skill_missing_fields):
    """测试加载缺少必需字段的技能"""
    loader = SkillLoader()

    with pytest.raises(ValueError, match="Missing required fields"):
        loader.load_skill(invalid_skill_missing_fields)


def test_load_skill_no_frontmatter(skill_no_frontmatter):
    """测试加载没有 frontmatter 的技能应该失败"""
    loader = SkillLoader()

    # 没有 frontmatter 应该抛出异常（缺少必需字段）
    with pytest.raises(ValueError, match="Missing required fields"):
        loader.load_skill(skill_no_frontmatter)


def test_parse_frontmatter(valid_skill):
    """测试解析 frontmatter"""
    loader = SkillLoader()
    skill_md = valid_skill / "SKILL.md"
    content = skill_md.read_text()

    frontmatter, body = loader._parse_skill_md(content)

    assert frontmatter["name"] == "Test Skill"
    assert frontmatter["description"] == "A test skill for unit testing"
    assert "Test Skill Content" in body


def test_validate_frontmatter_valid():
    """测试验证有效的 frontmatter"""
    loader = SkillLoader()
    frontmatter = {
        "name": "Test",
        "description": "Test description"
    }

    # 应该不抛出异常
    loader._validate_frontmatter(frontmatter)


def test_validate_frontmatter_missing_name():
    """测试验证缺少 name 字段"""
    loader = SkillLoader()
    frontmatter = {
        "description": "Test description"
    }

    with pytest.raises(ValueError, match="Missing required fields"):
        loader._validate_frontmatter(frontmatter)


def test_validate_frontmatter_missing_description():
    """测试验证缺少 description 字段"""
    loader = SkillLoader()
    frontmatter = {
        "name": "Test"
    }

    with pytest.raises(ValueError, match="Missing required fields"):
        loader._validate_frontmatter(frontmatter)
