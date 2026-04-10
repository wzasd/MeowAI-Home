import click
from src.router.agent_router import AgentRouter
from src.cli.thread_commands import thread_cli, get_cat_mention, run_async
from src.collaboration.intent_parser import parse_intent
from src.collaboration.a2a_controller import A2AController


@click.group()
@click.version_option(version='0.3.2', prog_name='meowai')
def cli():
    """MeowAI Home - 温馨的流浪猫AI收容所 🐱"""
    pass


# 注册 thread 命令
cli.add_command(thread_cli)


# ========== Skill 命令组 ==========
@cli.group()
def skill():
    """技能管理命令"""
    pass


@skill.command()
def list():
    """列出所有可用技能"""
    from src.skills.router import ManifestRouter
    from pathlib import Path

    manifest_path = Path("skills/manifest.yaml")
    if not manifest_path.exists():
        click.echo("❌ manifest.yaml 不存在")
        click.echo("   请先创建 skills/manifest.yaml")
        return

    router = ManifestRouter(manifest_path)
    skills = router.list_all_skills()

    click.echo("\n📚 可用技能:\n")
    for skill_data in skills:
        desc = skill_data.get("description", "")
        if isinstance(desc, str):
            desc = desc.split("\n")[0]  # 只显示第一行

        click.echo(f"• {skill_data['skill_id']}: {desc}")
        if skill_data.get("triggers"):
            triggers = skill_data["triggers"][:3]
            click.echo(f"  触发词: {', '.join(triggers)}")
        click.echo()


@skill.command()
@click.argument('skill_id', required=False)
@click.option('--force', is_flag=True, help='强制安装，跳过安全检查')
def install(skill_id: str, force: bool):
    """安装技能（含安全审计）"""
    import asyncio
    from src.skills.installer import SkillInstaller
    from pathlib import Path

    installer = SkillInstaller()
    skills_dir = Path("skills")

    if not skills_dir.exists():
        click.echo("❌ skills/ 目录不存在")
        return

    if skill_id:
        # 安装单个技能
        skill_path = skills_dir / skill_id
        if not skill_path.exists():
            click.echo(f"❌ 技能未找到: {skill_id}")
            return

        asyncio.run(installer.install_skill(skill_id, skill_path, force))
    else:
        # 批量安装所有技能
        click.echo("📦 批量安装所有技能...\n")
        asyncio.run(installer.install_all_skills(skills_dir, force))


@skill.command()
@click.argument('skill_id')
def uninstall(skill_id: str):
    """卸载技能"""
    from src.skills.symlink_manager import SymlinkManager

    manager = SymlinkManager()
    success = manager.remove_skill_symlink(skill_id)

    if success:
        click.echo(f"✅ 技能 {skill_id} 已卸载")
    else:
        click.echo(f"❌ 卸载失败")


@skill.command()
@click.argument('skill_id', required=False)
def audit(skill_id: str):
    """审计技能安全性"""
    import asyncio
    from src.skills.security import SecurityAuditor
    from pathlib import Path

    auditor = SecurityAuditor()
    skills_dir = Path("skills")

    if not skills_dir.exists():
        click.echo("❌ skills/ 目录不存在")
        return

    if skill_id:
        # 审计单个技能
        skill_path = skills_dir / skill_id
        if not skill_path.exists():
            click.echo(f"❌ 技能未找到: {skill_id}")
            return

        report = asyncio.run(auditor.audit_skill(skill_path))
        report.print_summary()
    else:
        # 审计所有技能
        click.echo("🔍 审计所有技能...\n")

        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                report = asyncio.run(auditor.audit_skill(skill_dir))

                status = "✅" if report.passed else "❌"
                click.echo(f"{status} {skill_dir.name}: {len(report.issues)} 个问题")


# ========== Chat 命令 ==========


@cli.command()
@click.option('--cat', default=None, help='覆盖默认猫（@dev/@review/@research）')
@click.option('--thread', 'thread_id', help='指定 thread ID')
@click.option('--resume', is_flag=True, help='恢复上次会话')
def chat(cat: str, thread_id: str, resume: bool):
    """与猫猫开始对话"""
    from src.thread import ThreadManager

    manager = ThreadManager()
    router = AgentRouter()

    # 处理 --resume
    if resume:
        threads = run_async(manager.list())
        if threads:
            thread = threads[0]  # 最近更新的 thread
            manager.switch(thread.id)
            click.echo(f"🔄 恢复会话: {thread.name}")
            click.echo(f"   历史消息: {len(thread.messages)}条")
        else:
            click.echo("暂无历史会话，创建新 thread...")
            thread = run_async(manager.create("默认会话"))
            manager.switch(thread.id)
    # 处理 --thread
    elif thread_id:
        thread = run_async(manager.get(thread_id))
        if not thread:
            click.echo(f"❌ Thread 不存在: {thread_id}")
            return
        manager.switch(thread_id)
    else:
        # 默认行为：使用当前 thread 或创建新 thread
        thread = manager.get_current()
        if not thread:
            click.echo("🐱 还没有 thread，正在创建...")
            thread = run_async(manager.create("默认会话"))
            manager.switch(thread.id)

    # 确定使用的猫
    cat_id = cat.lstrip('@') if cat else thread.current_cat_id

    # 显示状态
    click.echo(f"\n🐱 Thread: {thread.name} | 猫: @{get_cat_mention(cat_id)}")
    click.echo(f"   历史: {len(thread.messages)}条消息")
    click.echo("💡 提示: 使用 #ideate 多猫并行讨论, #execute 串行接力执行")

    # 显示技能状态
    try:
        from src.skills.router import ManifestRouter
        from src.skills.symlink_manager import SymlinkManager
        from pathlib import Path as SkillPath
        manifest_path = SkillPath("skills/manifest.yaml")
        if manifest_path.exists():
            skill_router = ManifestRouter(manifest_path)
            total_skills = len(skill_router.list_all_skills())
            installed_skills = len(SymlinkManager().list_installed_skills())
            click.echo(f"📚 技能: {installed_skills}/{total_skills} 已安装")
    except Exception:
        pass

    click.echo("   (按 Ctrl+C 退出)\n")

    try:
        while True:
            message = click.prompt("你", type=str)

            # 如果没有 @mention，添加默认
            if '@' not in message:
                message = f"@{cat_id} {message}"

            # 路由消息获取 agents
            agents = router.route_message(message)

            # 解析 intent
            intent_result = parse_intent(message, len(agents))

            # 检查技能触发并显示提示
            try:
                from src.skills.router import ManifestRouter
                from pathlib import Path as SkillPath
                manifest_path = SkillPath("skills/manifest.yaml")
                if manifest_path.exists():
                    skill_router = ManifestRouter(manifest_path)
                    skill_matches = skill_router.route(intent_result.clean_message)
                    if skill_matches:
                        skill_name = skill_matches[0].get("name", skill_matches[0]["skill_id"])
                        click.echo(f"🎯 激活技能: {skill_name}")
            except Exception:
                pass

            # 显示模式信息
            if intent_result.explicit:
                mode_str = "并行讨论" if intent_result.intent == "ideate" else "串行接力"
                click.echo(f"🔄 模式: {mode_str} ({intent_result.intent})")

            if intent_result.prompt_tags:
                click.echo(f"🏷️  标签: {', '.join(intent_result.prompt_tags)}")

            # 添加用户消息到 thread（使用清理后的消息）
            thread.add_message("user", intent_result.clean_message)
            # 立即持久化用户消息（避免重复）
            run_async(manager.add_message(thread.id, thread.messages[-1]))

            # 使用 A2AController 执行协作
            try:
                controller = A2AController(agents)

                async def run_collaboration():
                    async for response in controller.execute(
                        intent_result,
                        intent_result.clean_message,
                        thread
                    ):
                        click.echo(f"\n{response.cat_name}: {response.content}\n")

                        # 添加回复到 thread
                        thread.add_message(
                            "assistant",
                            response.content,
                            cat_id=response.cat_id
                        )
                        # 立即持久化 assistant 消息（避免重复）
                        await manager.add_message(thread.id, thread.messages[-1])

                run_async(run_collaboration())

                # 保存 thread
                run_async(manager.update_thread(thread))

            except Exception as e:
                click.echo(f"\n❌ 错误: {str(e)}\n")

    except KeyboardInterrupt:
        click.echo(f"\n\n🐱 再见喵～对话已保存\n")
        run_async(manager.update_thread(thread))


if __name__ == '__main__':
    cli()
