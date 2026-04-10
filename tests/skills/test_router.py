"""ManifestRouter tests"""
import pytest
from pathlib import Path
import yaml

from src.skills.router import ManifestRouter


@pytest.fixture
def sample_manifest(tmp_path):
    """创建测试用 manifest.yaml"""
    manifest_data = {
        "skills": {
            "tdd": {
                "description": "TDD workflow",
                "triggers": ["写代码", "TDD", "test first"],
                "next": ["quality-gate"]
            },
            "quality-gate": {
                "description": "Quality gate",
                "triggers": ["开发完了", "自检"],
                "next": ["request-review"]
            },
            "brainstorm": {
                "description": "Brainstorming",
                "triggers": ["brainstorm", "讨论"]
            }
        }
    }

    manifest_file = tmp_path / "manifest.yaml"
    with open(manifest_file, 'w') as f:
        yaml.dump(manifest_data, f)

    return manifest_file


def test_load_manifest(sample_manifest):
    """测试加载 manifest.yaml"""
    router = ManifestRouter(sample_manifest)

    assert "tdd" in router.manifest["skills"]
    assert "quality-gate" in router.manifest["skills"]
    assert "brainstorm" in router.manifest["skills"]


def test_route_by_trigger(sample_manifest):
    """测试根据触发词路由"""
    router = ManifestRouter(sample_manifest)

    # 匹配单个技能
    matches = router.route("帮我写代码")
    assert len(matches) == 1
    assert matches[0]["skill_id"] == "tdd"

    # 匹配另一个技能
    matches = router.route("开发完了，准备review")
    assert len(matches) == 1
    assert matches[0]["skill_id"] == "quality-gate"


def test_route_no_match(sample_manifest):
    """测试无匹配"""
    router = ManifestRouter(sample_manifest)

    matches = router.route("随便聊聊")
    assert len(matches) == 0


def test_route_case_insensitive(sample_manifest):
    """测试大小写不敏感"""
    router = ManifestRouter(sample_manifest)

    matches = router.route("帮我 TDD")
    assert len(matches) == 1
    assert matches[0]["skill_id"] == "tdd"


def test_get_skill(sample_manifest):
    """测试获取单个技能"""
    router = ManifestRouter(sample_manifest)

    skill = router.get_skill("tdd")
    assert skill is not None
    assert skill["description"] == "TDD workflow"
    assert "写代码" in skill["triggers"]


def test_get_nonexistent_skill(sample_manifest):
    """测试获取不存在的技能"""
    router = ManifestRouter(sample_manifest)

    skill = router.get_skill("nonexistent")
    assert skill is None


def test_list_all_skills(sample_manifest):
    """测试列出所有技能"""
    router = ManifestRouter(sample_manifest)

    skills = router.list_all_skills()
    assert len(skills) == 3

    skill_ids = [s["skill_id"] for s in skills]
    assert "tdd" in skill_ids
    assert "quality-gate" in skill_ids
    assert "brainstorm" in skill_ids


def test_route_returns_next_field(sample_manifest):
    """测试返回 next 字段"""
    router = ManifestRouter(sample_manifest)

    matches = router.route("帮我写代码")
    assert len(matches) == 1
    assert "next" in matches[0]
    assert matches[0]["next"] == ["quality-gate"]
