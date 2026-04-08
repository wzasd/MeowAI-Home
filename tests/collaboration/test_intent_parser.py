import pytest
from src.collaboration.intent_parser import (
    IntentParser,
    parse_intent,
    VALID_INTENTS,
    VALID_PROMPT_TAGS,
)


def test_explicit_ideate():
    """测试显式 #ideate"""
    result = parse_intent("帮我设计架构 #ideate", cat_count=2)
    assert result.intent == "ideate"
    assert result.explicit is True


def test_explicit_execute():
    """测试显式 #execute"""
    result = parse_intent("实现这个功能 #execute", cat_count=2)
    assert result.intent == "execute"
    assert result.explicit is True


def test_auto_infer_ideate():
    """测试自动推断 ideate (>=2 猫)"""
    result = parse_intent("帮我看看这个", cat_count=2)
    assert result.intent == "ideate"
    assert result.explicit is False


def test_auto_infer_execute():
    """测试自动推断 execute (1 猫)"""
    result = parse_intent("帮我写代码", cat_count=1)
    assert result.intent == "execute"
    assert result.explicit is False


def test_critique_tag():
    """测试 #critique 标签"""
    result = parse_intent("检查这段代码 #critique", cat_count=1)
    assert "critique" in result.prompt_tags


def test_clean_message():
    """测试清理后的消息"""
    result = parse_intent("帮我设计 #ideate #critique", cat_count=2)
    assert "#ideate" not in result.clean_message
    assert "#critique" not in result.clean_message
    assert "帮我设计" in result.clean_message


def test_multiple_tags():
    """测试多个标签"""
    result = parse_intent("帮我看看 #ideate #critique", cat_count=2)
    assert result.intent == "ideate"
    assert "critique" in result.prompt_tags


def test_case_insensitive():
    """测试大小写不敏感"""
    result = parse_intent("帮我 #IDEATE #CRITIQUE", cat_count=2)
    assert result.intent == "ideate"
    assert "critique" in result.prompt_tags
