"""SkillInstaller - 技能安装器（批量安装 + 安全审计）"""
from pathlib import Path
from typing import Dict
import asyncio

from src.skills.loader import SkillLoader
from src.skills.symlink_manager import SymlinkManager
from src.skills.security import SecurityAuditor


class SkillInstaller:
    """技能安装器 - 批量安装 + 安全审计"""

    def __init__(self):
        self.loader = SkillLoader()
        self.symlink_manager = SymlinkManager()
        self.security_auditor = SecurityAuditor()

    async def install_skill(
        self,
        skill_id: str,
        skill_path: Path,
        force: bool = False
    ) -> bool:
        """
        安装单个技能（含安全审计）

        Args:
            skill_id: 技能 ID
            skill_path: 技能目录路径
            force: 是否跳过安全审计

        Returns:
            是否安装成功
        """
        # 1. 加载技能
        try:
            skill_data = self.loader.load_skill(skill_path)
            print(f"✅ 加载技能: {skill_id}")
        except FileNotFoundError as e:
            print(f"❌ 加载技能失败: {e}")
            return False
        except ValueError as e:
            print(f"❌ 技能格式错误: {e}")
            return False
        except Exception as e:
            print(f"❌ 加载技能失败: {e}")
            return False

        # 2. 安全审计（除非 force=True）
        if not force:
            print(f"🔍 执行安全审计: {skill_id}...")
            report = await self.security_auditor.audit_skill(skill_path)

            report.print_summary()

            if not report.passed:
                print(f"\n❌ 安全审计未通过，使用 --force 强制安装")
                return False
        else:
            print(f"⚠️  跳过安全审计 (force=True)")

        # 3. 创建 symlink
        success = self.symlink_manager.create_skill_symlink(skill_id, skill_path)

        if success:
            print(f"✅ 技能 {skill_id} 安装成功\n")
        else:
            print(f"❌ 技能 {skill_id} 安装失败\n")

        return success

    async def install_all_skills(
        self,
        skills_dir: Path,
        force: bool = False
    ) -> Dict[str, bool]:
        """
        批量安装所有技能

        Args:
            skills_dir: 技能目录
            force: 是否跳过安全审计

        Returns:
            {skill_id: success} 字典
        """
        results = {}

        # 遍历技能目录
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skill_id = skill_dir.name
                print(f"\n{'='*60}")
                print(f"安装技能: {skill_id}")
                print(f"{'='*60}")

                results[skill_id] = await self.install_skill(
                    skill_id,
                    skill_dir,
                    force
                )

        # 打印总结
        self._print_install_summary(results)

        return results

    def _print_install_summary(self, results: Dict[str, bool]):
        """打印安装总结"""
        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)

        print(f"\n{'='*60}")
        print(f"📊 安装完成: {success_count}/{total_count} 成功")
        print(f"{'='*60}")

        if success_count < total_count:
            print("\n❌ 失败的技能:")
            for skill_id, success in results.items():
                if not success:
                    print(f"  - {skill_id}")
        else:
            print("\n🎉 所有技能安装成功！")
