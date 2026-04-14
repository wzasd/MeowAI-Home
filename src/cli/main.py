import json
import click
from pathlib import Path
from src.models.cat_registry import CatRegistry
from src.models.agent_registry import AgentRegistry
from src.providers import PROVIDER_MAP
from src.cli.nest_init import run_nest_init
from src.cli.thread_commands import thread_cli, get_cat_mention, run_async
from src.collaboration.intent_parser import parse_intent
from src.collaboration.a2a_controller import A2AController


def bootstrap_registries(config_path: str = "cat-config.json"):
    """Load cat-config.json → CatRegistry + AgentRegistry with real providers."""
    cat_reg = CatRegistry()
    agent_reg = AgentRegistry()

    p = Path(config_path)
    if not p.exists():
        click.echo(f"❌ 配置文件不存在: {config_path}")
        raise SystemExit(1)

    with open(p) as f:
        config = json.load(f)

    breeds = config.get("breeds", [])
    cat_reg.load_from_breeds(breeds)

    for cat_id in cat_reg.get_all_ids():
        cat_cfg = cat_reg.get(cat_id)
        provider_cls = PROVIDER_MAP.get(cat_cfg.provider)
        if provider_cls:
            provider = provider_cls(cat_cfg)
            agent_reg.register(cat_id, provider)

    return cat_reg, agent_reg


@click.group()
@click.version_option(version='1.0.0', prog_name='meowai')
def cli():
    """MeowAI Home - 企业级多 Agent AI 协作平台"""
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


# ========== Service 命令 ==========


@cli.command()
@click.option('--api-only', is_flag=True, help='只启动 API，不启动前端')
@click.option('--port', default=8000, help='API 端口')
def start(api_only: bool, port: int):
    """启动 MeowAI Home 服务"""
    import subprocess
    import sys
    import os
    import signal as sig

    processes = []

    def cleanup(signum=None, frame=None):
        for p in processes:
            p.terminate()
        for p in processes:
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
        sys.exit(0)

    sig.signal(sig.SIGINT, cleanup)
    sig.signal(sig.SIGTERM, cleanup)

    # Load .env if present
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

    click.echo("🐱 启动 MeowAI Home...")

    # Start backend
    backend_cmd = [
        sys.executable, "-m", "uvicorn",
        "src.web.app:create_app", "--factory",
        "--host", "0.0.0.0", "--port", str(port),
    ]
    backend = subprocess.Popen(backend_cmd)
    processes.append(backend)
    click.echo(f"   API: http://localhost:{port}")

    # Start frontend if available
    if not api_only and Path("web/node_modules").is_dir():
        frontend = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd="web",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        processes.append(frontend)
        click.echo(f"   Web: http://localhost:5173")
    elif not api_only:
        click.echo("   Web: 未安装 (cd web && npm install)")

    click.echo("\n   按 Ctrl+C 停止\n")

    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        cleanup()


@cli.command()
@click.option('--api-only', is_flag=True, help='只启动 API，不启动前端')
@click.option('--port', default=8000, help='API 端口')
def dev(api_only: bool, port: int):
    """开发模式启动（带热重载）"""
    import subprocess
    import sys
    import os
    import signal as sig

    processes = []

    def cleanup(signum=None, frame=None):
        for p in processes:
            p.terminate()
        for p in processes:
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
        sys.exit(0)

    sig.signal(sig.SIGINT, cleanup)
    sig.signal(sig.SIGTERM, cleanup)

    # Load .env
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

    click.echo("🐱 启动 MeowAI Home (dev mode)...")

    backend = subprocess.Popen([
        sys.executable, "-m", "uvicorn",
        "src.web.app:create_app", "--factory",
        "--host", "0.0.0.0", "--port", str(port), "--reload",
    ])
    processes.append(backend)
    click.echo(f"   API: http://localhost:{port} (reload)")

    if not api_only and Path("web/node_modules").is_dir():
        frontend = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd="web",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        processes.append(frontend)
        click.echo(f"   Web: http://localhost:5173")

    click.echo("\n   按 Ctrl+C 停止\n")

    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        cleanup()


@cli.command()
def check():
    """检查运行环境"""
    import shutil
    import sys

    click.echo("🐱 MeowAI Home 环境检查\n")

    ok_count = 0
    warn_count = 0
    fail_count = 0

    def status(name, ok, detail, required=True):
        nonlocal ok_count, warn_count, fail_count
        if ok:
            click.echo(f"  ✓ {name}: {detail}")
            ok_count += 1
        elif required:
            click.echo(f"  ✗ {name}: {detail}")
            fail_count += 1
        else:
            click.echo(f"  - {name}: {detail}")
            warn_count += 1

    # Python
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    status("Python >= 3.10", sys.version_info >= (3, 10), py_ver)

    # cat-config.json
    config_ok = Path("cat-config.json").exists()
    status("cat-config.json", config_ok, "found" if config_ok else "missing")

    # .env
    env_ok = Path(".env").exists()
    status(".env", env_ok, "found" if env_ok else "not found (cp .env.example .env)", required=False)

    # data/
    data_ok = Path("data").is_dir()
    status("data/", True, "exists" if data_ok else "will be auto-created", required=False)

    # CLI tools
    click.echo("\n  AI CLI 工具:")
    for tool in ["claude", "codex", "gemini", "opencode"]:
        path = shutil.which(tool)
        if path:
            try:
                ver = subprocess.check_output(
                    [tool, "--version"], stderr=subprocess.DEVNULL, timeout=5
                ).decode().strip().split("\n")[0]
            except Exception:
                ver = "installed"
            click.echo(f"  ✓ {tool}: {ver}")
            ok_count += 1
        else:
            click.echo(f"  - {tool}: not installed")
            warn_count += 1

    # Web UI
    web_ok = Path("web/node_modules").is_dir()
    status("Web UI deps", web_ok, "installed" if web_ok else "run: cd web && npm install", required=False)

    # Summary
    click.echo(f"\n  {ok_count} ok, {warn_count} optional, {fail_count} missing")
    if fail_count == 0:
        click.echo("  ✅ 环境就绪，运行 meowai start 启动")
    else:
        click.echo("  ⚠️  请修复上述问题后重试")


# ========== Chat 命令 ==========


@cli.command()
@click.option('--cat', default=None, help='覆盖默认猫 (@opus/@sonnet/@codex/...)')
@click.option('--thread', 'thread_id', help='指定 thread ID')
@click.option('--resume', is_flag=True, help='恢复上次会话')
def chat(cat: str, thread_id: str, resume: bool):
    """与猫猫开始对话"""
    from src.thread import ThreadManager

    cat_reg, agent_reg = bootstrap_registries()

    manager = ThreadManager()

    # 处理 --resume
    if resume:
        threads = run_async(manager.list())
        if threads:
            thread = threads[0]
            manager.switch(thread.id)
            click.echo(f"🔄 恢复会话: {thread.name}")
            click.echo(f"   历史消息: {len(thread.messages)}条")
        else:
            click.echo("暂无历史会话，创建新 thread...")
            thread = run_async(manager.create("默认会话", project_path=str(Path.cwd())))
            manager.switch(thread.id)
    elif thread_id:
        thread = run_async(manager.get(thread_id))
        if not thread:
            click.echo(f"❌ Thread 不存在: {thread_id}")
            return
        manager.switch(thread_id)
    else:
        thread = manager.get_current()
        if not thread:
            click.echo("🐱 还没有 thread，正在创建...")
            thread = run_async(manager.create("默认会话", project_path=str(Path.cwd())))
            manager.switch(thread.id)

    # 解析 cat mention → cat_id
    if cat:
        cat_mention = cat.lstrip('@')
        mention_cat = cat_reg.get_by_mention(cat_mention)
        if mention_cat:
            cat_id = mention_cat.cat_id
        else:
            cat_id = cat_mention
    else:
        cat_id = thread.current_cat_id

    # 验证 cat_id 有对应的 provider
    if not agent_reg.has(cat_id):
        default_id = cat_reg.get_default_id()
        if default_id:
            cat_id = default_id
        else:
            click.echo(f"❌ 未找到 Agent: {cat_id}")
            return

    cat_config = cat_reg.get(cat_id)
    display_name = cat_config.display_name if cat_config else cat_id

    # 显示状态
    click.echo(f"\n🐱 Thread: {thread.name} | 猫: {display_name} (@{cat_id})")
    click.echo(f"   Provider: {cat_config.provider} | Model: {cat_config.default_model}")
    click.echo(f"   历史: {len(thread.messages)}条消息")
    click.echo("💡 提示: 使用 #ideate 多猫并行讨论, #execute 串行接力执行")

    # 显示可用猫
    all_ids = cat_reg.get_all_ids()
    available = [cid for cid in all_ids if agent_reg.has(cid)]
    if available:
        click.echo(f"   可用猫: {', '.join(f'@{cid}' for cid in available)}")

    click.echo("   (按 Ctrl+C 退出)\n")

    try:
        while True:
            message = click.prompt("你", type=str)

            # 如果没有 @mention，添加默认
            if '@' not in message:
                message = f"@{cat_id} {message}"

            # 使用 AgentRouterV2 解析 mentions
            from src.router.agent_router_v2 import AgentRouterV2
            router = AgentRouterV2(cat_reg, agent_reg)
            agents = router.route_message(message)

            if not agents:
                click.echo("❌ 没有匹配到任何猫")
                continue

            # 解析 intent
            intent_result = parse_intent(message, len(agents))

            # 检查技能触发
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

            # 显示将要调用的猫
            cat_names = [f"@{a['breed_id']}" for a in agents]
            click.echo(f"📤 调用: {', '.join(cat_names)}\n")

            # 添加用户消息到 thread
            thread.add_message("user", intent_result.clean_message)
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
                        cfg = cat_reg.try_get(response.cat_id)
                        name = cfg.display_name if cfg else response.cat_name
                        # Stream incremental chunks for typing effect
                        click.echo(f"\n{name}: ", nl=False)
                        click.echo(response.content, nl=False)

                        # Only persist final response to database
                        if getattr(response, 'is_final', False):
                            click.echo()  # New line after final chunk
                            thread.add_message(
                                "assistant",
                                response.content,
                                cat_id=response.cat_id
                            )
                            await manager.add_message(thread.id, thread.messages[-1])

                run_async(run_collaboration())
                run_async(manager.update_thread(thread))

            except Exception as e:
                click.echo(f"\n❌ 错误: {str(e)}\n")

    except KeyboardInterrupt:
        click.echo(f"\n\n🐱 再见喵～对话已保存\n")
        run_async(manager.update_thread(thread))


def main():
    import sys
    if len(sys.argv) == 1:
        run_nest_init(interactive=True)
    else:
        cli()


if __name__ == '__main__':
    main()
