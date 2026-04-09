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


class TestWorkflowIntent:
    def test_brainstorm_tag(self):
        result = parse_intent("#brainstorm 给我方案", 3)
        assert result.workflow == "brainstorm"

    def test_parallel_tag(self):
        result = parse_intent("#parallel 分工实现", 3)
        assert result.workflow == "parallel"

    def test_autoplan_tag(self):
        result = parse_intent("#autoplan 实现登录", 3)
        assert result.workflow == "auto_plan"

    def test_autoplan_mention(self):
        result = parse_intent("@planner 实现登录", 3)
        assert result.workflow == "auto_plan"

    def test_auto_brainstorm_3plus_cats(self):
        result = parse_intent("@orange @inky @patch 给方案", 3)
        assert result.workflow == "brainstorm"
        assert result.explicit is False

    def test_no_workflow_1_cat(self):
        result = parse_intent("hello", 1)
        assert result.workflow is None

    def test_no_workflow_2_cats(self):
        result = parse_intent("@orange @inky hello", 2)
        assert result.workflow is None
        assert result.intent == "ideate"

    def test_explicit_intent_overrides_auto_workflow(self):
        result = parse_intent("#execute @orange @inky @patch 做这个", 3)
        assert result.workflow is None
        assert result.intent == "execute"
        assert result.explicit is True
