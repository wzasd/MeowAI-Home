"""Manifest Router - 基于 manifest.yaml 自动路由技能"""
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml


class ManifestRouter:
    """技能路由器 - 基于 manifest.yaml 自动匹配"""

    def __init__(self, manifest_path: Path):
        """
        初始化路由器

        Args:
            manifest_path: manifest.yaml 文件路径
        """
        self.manifest_path = Path(manifest_path)
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> Dict[str, Any]:
        """加载 manifest.yaml"""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")

        with open(self.manifest_path, encoding='utf-8') as f:
            return yaml.safe_load(f)

    def route(self, message: str) -> List[Dict[str, Any]]:
        """
        路由用户消息到匹配的技能

        Args:
            message: 用户消息

        Returns:
            匹配的技能列表（按优先级排序）
        """
        matches = []

        for skill_id, skill_data in self.manifest.get("skills", {}).items():
            triggers = skill_data.get("triggers", [])

            # 检查是否匹配任何触发器
            for trigger in triggers:
                if self._match_trigger(message, trigger):
                    matches.append({
                        "skill_id": skill_id,
                        "priority": skill_data.get("priority", 0),
                        "next": skill_data.get("next"),
                        **skill_data
                    })
                    break  # 一个技能匹配一次即可

        # 按优先级排序（高优先级在前）
        matches.sort(key=lambda x: x.get("priority", 0), reverse=True)
        return matches

    def _match_trigger(self, message: str, trigger: str) -> bool:
        """
        检查消息是否匹配触发器

        Args:
            message: 用户消息
            trigger: 触发词

        Returns:
            是否匹配
        """
        # 简单的大小写不敏感字符串匹配
        return trigger.lower() in message.lower()

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定技能

        Args:
            skill_id: 技能 ID

        Returns:
            技能数据（如果存在）
        """
        return self.manifest.get("skills", {}).get(skill_id)

    def list_all_skills(self) -> List[Dict[str, Any]]:
        """
        列出所有技能

        Returns:
            所有技能列表
        """
        skills = []
        for skill_id, skill_data in self.manifest.get("skills", {}).items():
            skills.append({
                "skill_id": skill_id,
                **skill_data
            })
        return skills
