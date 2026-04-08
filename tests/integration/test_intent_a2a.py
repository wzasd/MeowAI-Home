import pytest
from click.testing import CliRunner
from src.cli.main import cli
from src.collaboration.intent_parser import parse_intent


def test_intent_ideate():
    """测试 ideate intent"""
    result = parse_intent("帮我设计 #ideate", cat_count=2)
    assert result.intent == "ideate"
    assert result.explicit is True


def test_intent_execute():
    """测试 execute intent"""
    result = parse_intent("帮我实现 #execute", cat_count=2)
    assert result.intent == "execute"
    assert result.explicit is True


def test_intent_auto_infer():
    """测试自动推断"""
    # 多猫默认 ideate
    result = parse_intent("帮我看看", cat_count=2)
    assert result.intent == "ideate"

    # 单猫默认 execute
    result = parse_intent("帮我看看", cat_count=1)
    assert result.intent == "execute"


def test_critique_mode():
    """测试 critique 标签"""
    result = parse_intent("检查代码 #critique", cat_count=1)
    assert "critique" in result.prompt_tags
