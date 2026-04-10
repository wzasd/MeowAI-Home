"""SymlinkManager - Symlink 管理器"""
from pathlib import Path
from typing import List


class SymlinkManager:
    """Symlink 管理器 - 持久化挂载技能"""

    def __init__(self):
        self.skills_dir = Path.home() / ".meowai" / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def create_skill_symlink(self, skill_id: str, source_path: Path) -> bool:
        """
        创建技能 symlink

        Args:
            skill_id: 技能 ID
            source_path: 技能源目录路径

        Returns:
            是否成功
        """
        target = self.skills_dir / skill_id

        # 如果已存在，先删除
        if target.exists() or target.is_symlink():
            target.unlink()

        # 创建 symlink（使用绝对路径）
        try:
            # 确保使用绝对路径
            abs_source = source_path.resolve()
            target.symlink_to(abs_source)
            return True
        except OSError as e:
            print(f"创建 symlink 失败: {e}")
            return False

    def remove_skill_symlink(self, skill_id: str) -> bool:
        """
        删除技能 symlink

        Args:
            skill_id: 技能 ID

        Returns:
            是否成功
        """
        target = self.skills_dir / skill_id

        if target.exists() or target.is_symlink():
            try:
                target.unlink()
                return True
            except OSError as e:
                print(f"删除 symlink 失败: {e}")
                return False

        return True  # 本来就不存在，也算成功

    def verify_symlink(self, skill_id: str) -> bool:
        """
        验证 symlink 完整性

        Args:
            skill_id: 技能 ID

        Returns:
            symlink 是否有效
        """
        target = self.skills_dir / skill_id

        # 检查是否存在
        if not target.exists():
            return False

        # 检查是否为 symlink
        if not target.is_symlink():
            return False

        # 检查目标是否存在
        try:
            resolved = target.resolve()
            return resolved.exists()
        except OSError:
            return False

    def list_installed_skills(self) -> List[str]:
        """
        列出已安装的技能

        Returns:
            技能 ID 列表
        """
        skills = []
        for item in self.skills_dir.iterdir():
            if item.is_symlink() or item.is_dir():
                skills.append(item.name)
        return sorted(skills)

    def get_skill_path(self, skill_id: str) -> Path:
        """
        获取技能 symlink 路径

        Args:
            skill_id: 技能 ID

        Returns:
            symlink 目标路径
        """
        return self.skills_dir / skill_id
