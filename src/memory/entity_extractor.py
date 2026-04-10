"""正则实体提取器 — 从文本中提取偏好、技术、约束、角色"""
import re
from typing import List, Tuple

ENTITY_PATTERNS = [
    # 偏好类: "用户喜欢/偏好/习惯 React"
    (r'用户(?:喜欢|偏好|习惯(?:用)?|常用)\s*(\w+)', 'preference'),
    # 技术类: "项目使用/采用/基于 {X} 框架/库/工具"
    (r'项目(?:使用|采用|基于)\s*(\w+)(?:\s*(?:框架|库|工具|语言|数据库))?', 'technology'),
    # 约束类: "不能用/不要用/避免 {X}"
    (r'(?:不能用|不要用|避免)\s*(\w+)', 'constraint'),
    # 角色类: "{X} 负责/擅长 {Y}"
    (r'(\w+)(?:负责|擅长)\s*(.+?)(?:[。，,;\n]|$)', 'role'),
]


def extract_entities(text: str) -> List[Tuple[str, str, str]]:
    """从文本中提取实体。

    Returns:
        List of (name, entity_type, description) tuples.
    """
    if not text:
        return []

    results = []
    for pattern, entity_type in ENTITY_PATTERNS:
        for match in re.finditer(pattern, text):
            name = match.group(1)
            description = match.group(0)
            results.append((name, entity_type, description))
    return results
