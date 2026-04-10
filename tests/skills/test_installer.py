"""SkillInstaller tests"""
import pytest
from pathlib import Path

from src.skills.installer import SkillInstaller


@pytest.fixture
def installer():
    """创建 SkillInstaller 实例"""
    return SkillInstaller()


@pytest.fixture
def skills_dir(tmp_path):
    """创建技能目录"""
    # 创建3个技能
    for i in range(1, 4):
        skill_dir = tmp_path / f"skill{i}"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(f"""---
name: Skill {i}
description: Test skill {i}
triggers:
  - "skill{i}"
---

# Skill {i}
""")

    return tmp_path


@pytest.mark.asyncio
async def test_install_single_skill(installer, skills_dir):
    """测试安装单个技能"""
    skill_path = skills_dir / "skill1"

    success = await installer.install_skill("skill1", skill_path)
    assert success is True

    # 验证已安装
    assert installer.symlink_manager.verify_symlink("skill1")


@pytest.mark.asyncio
async def test_install_skill_with_audit(installer, skills_dir, capsys):
    """测试安装技能时执行安全审计"""
    skill_path = skills_dir / "skill1"

    success = await installer.install_skill("skill1", skill_path, force=False)
    assert success is True

    # 应该有审计输出
    captured = capsys.readouterr()
    assert "安全审计" in captured.out or "Step 1/6" in captured.out


@pytest.mark.asyncio
async def test_install_skill_force_skip_audit(installer, skills_dir, capsys):
    """测试强制安装跳过安全审计"""
    skill_path = skills_dir / "skill1"

    success = await installer.install_skill("skill1", skill_path, force=True)
    assert success is True

    # 应该有跳过审计的提示
    captured = capsys.readouterr()
    assert "跳过安全审计" in captured.out or "force=True" in captured.out


@pytest.mark.asyncio
async def test_install_all_skills(installer, skills_dir):
    """测试批量安装所有技能"""
    results = await installer.install_all_skills(skills_dir)

    # 应该安装3个技能
    assert len(results) == 3
    assert all(success for success in results.values())

    # 验证所有技能都已安装
    installed = installer.symlink_manager.list_installed_skills()
    assert "skill1" in installed
    assert "skill2" in installed
    assert "skill3" in installed


@pytest.mark.asyncio
async def test_install_skill_with_invalid_path(installer, tmp_path):
    """测试安装不存在的技能"""
    nonexistent = tmp_path / "nonexistent"

    success = await installer.install_skill("nonexistent", nonexistent)
    assert success is False


@pytest.mark.asyncio
async def test_install_skill_missing_skill_md(installer, tmp_path):
    """测试安装缺少 SKILL.md 的技能"""
    skill_dir = tmp_path / "no-skill-md"
    skill_dir.mkdir()

    success = await installer.install_skill("no-skill-md", skill_dir)
    assert success is False


@pytest.mark.asyncio
async def test_install_summary(installer, skills_dir, capsys):
    """测试安装总结输出"""
    await installer.install_all_skills(skills_dir)

    captured = capsys.readouterr()
    assert "安装完成" in captured.out or "成功" in captured.out
