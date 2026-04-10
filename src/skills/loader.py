"""SkillLoader - 从磁盘加载 SKILL.md 文件"""

from pathlib import Path
from typing import Dict, Any, Tuple
import yaml


class SkillLoader:
    """技能加载器 - 从磁盘加载 SKILL.md"""

    def load_skill(self, skill_path: Path) -> Dict[str, Any]:
        """
        从磁盘加载技能

        Args:
            skill_path: 技能目录路径

        Returns:
            包含 metadata、content、path 的字典

        Raises:
            FileNotFoundError: SKILL.md 不存在
            ValueError: 缺少必需字段
        """
        skill_md = skill_path / "SKILL.md"

        if not skill_md.exists():
            raise FileNotFoundError(f"SKILL.md not found in {skill_path}")

        # 读取文件
        content = skill_md.read_text(encoding='utf-8')

        # 解析 frontmatter
        frontmatter, body = self._parse_skill_md(content)

        # 验证必需字段
        self._validate_frontmatter(frontmatter)

        return {
            "metadata": frontmatter,
            "content": body,
            "path": skill_path
        }

    def _parse_skill_md(self, content: str) -> Tuple[Dict[str, Any], str]:
        """
        解析 SKILL.md 的 frontmatter 和 body

        Args:
            content: SKILL.md 文件内容

        Returns:
            (frontmatter, body) 元组
        """
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()
                return frontmatter, body

        # 没有 frontmatter
        return {}, content

    def _validate_frontmatter(self, frontmatter: Dict[str, Any]):
        """
        验证 frontmatter 必需字段

        Args:
            frontmatter: YAML frontmatter

        Raises:
            ValueError: 缺少必需字段
        """
        required = ["name", "description"]
        missing = [f for f in required if f not in frontmatter]

        if missing:
            raise ValueError(f"Missing required fields: {missing}")
