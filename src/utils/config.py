import yaml
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str = "config/cat-config.yaml") -> Dict[str, Any]:
    """加载YAML配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典

    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: YAML解析错误
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_cat_config(cat_name: str, config_path: str = "config/cat-config.yaml") -> Dict[str, Any]:
    """获取特定猫的配置

    Args:
        cat_name: 猫的名字
        config_path: 配置文件路径

    Returns:
        猫的配置字典

    Raises:
        ValueError: 找不到指定名字的猫
    """
    config = load_config(config_path)
    for cat in config["cats"]:
        if cat["name"] == cat_name:
            return cat
    raise ValueError(f"Cat not found: {cat_name}")
