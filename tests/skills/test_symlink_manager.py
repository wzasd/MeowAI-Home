"""SymlinkManager tests"""
import pytest
from pathlib import Path

from src.skills.symlink_manager import SymlinkManager


@pytest.fixture
def manager():
    """创建 SymlinkManager 实例"""
    return SymlinkManager()


@pytest.fixture
def sample_skill(tmp_path):
    """创建示例技能目录"""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: Test Skill
description: Test
---

# Test
""")

    return skill_dir


def test_create_skill_symlink(manager, sample_skill, tmp_path):
    """测试创建技能 symlink"""
    skill_id = "test-skill"

    # 创建 symlink
    success = manager.create_skill_symlink(skill_id, sample_skill)
    assert success is True

    # 验证 symlink 存在
    target = manager.skills_dir / skill_id
    assert target.exists()
    assert target.is_symlink()

    # 验证目标正确
    resolved = target.resolve()
    assert resolved == sample_skill.resolve()


def test_remove_skill_symlink(manager, sample_skill):
    """测试删除技能 symlink"""
    skill_id = "test-skill"

    # 先创建
    manager.create_skill_symlink(skill_id, sample_skill)

    # 再删除
    success = manager.remove_skill_symlink(skill_id)
    assert success is True

    # 验证 symlink 不存在
    target = manager.skills_dir / skill_id
    assert not target.exists()


def test_remove_nonexistent_symlink(manager):
    """测试删除不存在的 symlink"""
    success = manager.remove_skill_symlink("nonexistent")
    assert success is True  # 应该成功（本来就不存在）


def test_verify_symlink(manager, sample_skill):
    """测试验证 symlink"""
    skill_id = "test-skill"

    # 创建前验证
    assert manager.verify_symlink(skill_id) is False

    # 创建
    manager.create_skill_symlink(skill_id, sample_skill)

    # 创建后验证
    assert manager.verify_symlink(skill_id) is True


def test_verify_broken_symlink(manager, sample_skill):
    """测试验证损坏的 symlink"""
    skill_id = "broken-skill"

    # 创建 symlink
    manager.create_skill_symlink(skill_id, sample_skill)

    # 删除目标（使用 shutil.rmtree 删除非空目录）
    import shutil
    shutil.rmtree(sample_skill)

    # 验证 symlink 损坏
    assert manager.verify_symlink(skill_id) is False


def test_list_installed_skills(manager, sample_skill, tmp_path):
    """测试列出已安装的技能"""
    # 使用新的 manager 实例和干净的目录
    clean_manager = SymlinkManager()
    clean_manager.skills_dir = tmp_path / "clean-skills"
    clean_manager.skills_dir.mkdir(parents=True, exist_ok=True)

    # 初始应该为空
    skills = clean_manager.list_installed_skills()
    assert len(skills) == 0

    # 安装一个技能
    clean_manager.create_skill_symlink("skill1", sample_skill)

    # 列出技能
    skills = clean_manager.list_installed_skills()
    assert len(skills) == 1
    assert "skill1" in skills

    # 再安装一个
    skill2_dir = sample_skill.parent / "skill2"
    skill2_dir.mkdir()
    (skill2_dir / "SKILL.md").write_text("# Skill 2")
    clean_manager.create_skill_symlink("skill2", skill2_dir)

    # 再次列出
    skills = clean_manager.list_installed_skills()
    assert len(skills) == 2
    assert "skill1" in skills
    assert "skill2" in skills


def test_replace_existing_symlink(manager, sample_skill):
    """测试替换现有 symlink"""
    skill_id = "test-skill"

    # 创建第一个 symlink
    manager.create_skill_symlink(skill_id, sample_skill)
    target1 = manager.skills_dir / skill_id
    resolved1 = target1.resolve()

    # 创建新的目标
    new_skill_dir = sample_skill.parent / "new-skill"
    new_skill_dir.mkdir()
    (new_skill_dir / "SKILL.md").write_text("# New Skill")

    # 替换 symlink
    success = manager.create_skill_symlink(skill_id, new_skill_dir)
    assert success is True

    # 验证 symlink 指向新目标
    target2 = manager.skills_dir / skill_id
    resolved2 = target2.resolve()
    assert resolved2 == new_skill_dir.resolve()
    assert resolved2 != resolved1
