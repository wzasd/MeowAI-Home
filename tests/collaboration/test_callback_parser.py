import pytest
from src.collaboration.callback_parser import (
    parse_callbacks,
    strip_callback_markers,
    ToolCall,
    CallbackParseResult
)


def test_parse_single_callback():
    """测试解析单个回调"""
    content = """Hello!

<mcp:post_message>
{"content": "This is a test message"}
</mcp:post_message>

Goodbye!"""

    result = parse_callbacks(content)

    assert "Hello!" in result.clean_content
    assert "Goodbye!" in result.clean_content
    assert "post_message" not in result.clean_content
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "post_message"
    assert result.tool_calls[0].params["content"] == "This is a test message"


def test_parse_multiple_callbacks():
    """测试解析多个回调"""
    content = """Start
<mcp:search_files>{"query": "class"}</mcp:search_files>
Middle
<mcp:post_message>{"content": "Done"}</mcp:post_message>
End"""

    result = parse_callbacks(content)

    assert len(result.tool_calls) == 2
    assert result.tool_calls[0].tool_name == "search_files"
    assert result.tool_calls[1].tool_name == "post_message"


def test_parse_target_cats():
    """测试解析 targetCats"""
    content = """I found the issue.

<mcp:targetCats>
{"cats": ["inky", "patch"]}
</mcp:targetCats>"""

    result = parse_callbacks(content)

    assert result.targetCats == ["inky", "patch"]
    assert "targetCats" not in result.clean_content


def test_parse_no_callbacks():
    """测试没有回调的内容"""
    content = "This is a plain message without callbacks."

    result = parse_callbacks(content)

    assert result.clean_content == content
    assert len(result.tool_calls) == 0
    assert len(result.targetCats) == 0


def test_parse_invalid_json():
    """测试无效的 JSON 回调"""
    content = "Hello\n<mcp:post_message>{invalid json}</mcp:post_message>\nWorld"

    result = parse_callbacks(content)

    # 无效 JSON 应该保留在内容中
    assert "{invalid json}" in result.clean_content
    assert len(result.tool_calls) == 0


def test_strip_callback_markers():
    """测试仅移除标记"""
    content = """Text
<mcp:tool>{"a": 1}</mcp:tool>
More text"""

    result = strip_callback_markers(content)

    assert "<mcp:tool>" not in result
    assert "Text" in result
    assert "More text" in result


def test_case_insensitive():
    """测试大小写不敏感"""
    content = '<mcp:POST_MESSAGE>{"content": "test"}</mcp:POST_MESSAGE>'

    result = parse_callbacks(content)

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "post_message"
