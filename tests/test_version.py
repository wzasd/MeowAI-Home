"""测试版本信息"""
from meowai.version import __version__


def test_version():
    """测试版本号格式正确"""
    assert __version__ == "0.1.0"
    assert isinstance(__version__, str)