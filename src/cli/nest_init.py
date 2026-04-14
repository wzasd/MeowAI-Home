import click
from pathlib import Path
from typing import Any, Dict, List

from src.cli.claude_md_writer import write_neowai_block
from src.config.nest_config import load_nest_config, save_nest_config
from src.config.nest_registry import NestRegistry
from src.models.cat_registry import CatRegistry


def _build_cats_block(valid_cats: List[str], cat_registry: CatRegistry) -> str:
    lines = ["## NeowAI Cats"]
    for cat_id in valid_cats:
        cat = cat_registry.get(cat_id)
        parts = [f"- **{cat.name}** ({cat_id})"]
        if getattr(cat, "role_description", None):
            parts.append(f"  - 角色：{cat.role_description}")
        if getattr(cat, "personality", None):
            parts.append(f"  - 性格：{cat.personality}")
        capabilities = getattr(cat, "capabilities", None) or []
        if capabilities:
            parts.append(f"  - 能力：{', '.join(capabilities)}")
        permissions = getattr(cat, "permissions", None) or []
        if permissions:
            parts.append(f"  - 权限：{', '.join(permissions)}")
        lines.append("\n".join(parts))
    return "\n\n".join(lines)


def run_nest_init(interactive: bool = True) -> None:
    project_path = Path.cwd()
    config_path = project_path / ".neowai" / "config.json"
    claude_md_path = project_path / "CLAUDE.md"

    cat_registry = CatRegistry()
    try:
        from src.models.registry_init import initialize_registries

        initialize_registries(str(project_path / "cat-config.json"))
    except FileNotFoundError:
        pass
    except Exception as e:
        click.echo(f"  ⚠️ 加载 cat-config.json 时出错: {e}")

    valid_cats: Dict[str, Any] = {cid: None for cid in cat_registry.get_all_ids()}
    if not valid_cats:
        click.echo("⚠️  当前目录没有可用的 cat-config.json，无法初始化 NeowAI 项目。")
        return

    registry = NestRegistry()
    already_initialized = registry.is_registered(str(project_path)) or config_path.exists()

    if not already_initialized:
        click.echo(f"🐱 正在初始化 NeowAI 猫窝: {project_path}")
        cfg, warnings = load_nest_config(
            config_path,
            project_name=project_path.name,
            valid_cats=valid_cats,
            interactive=interactive,
        )
        if warnings:
            for w in warnings:
                click.echo(f"  ⚠️ {w}")
        try:
            block = _build_cats_block(cfg.cats, cat_registry)
            write_neowai_block(claude_md_path, block)
            click.echo("  ✅ CLAUDE.md 已更新")
        except OSError as e:
            click.echo(f"  ⚠️ CLAUDE.md 写入失败: {e}，后续调用将使用临时 system prompt")
        registry.register(str(project_path))
        click.echo("  ✅ 初始化完成！")
        click.echo("\n  你可以通过 `neowai start` 启动服务，")
        click.echo("  或 `neowai chat` 开始命令行对话。")
    else:
        cfg, warnings = load_nest_config(
            config_path,
            project_name=project_path.name,
            valid_cats=valid_cats,
            interactive=False,
        )
        if warnings and interactive:
            click.echo("⚠️  config.json 存在一些问题：")
            for w in warnings:
                click.echo(f"  - {w}")
            if click.confirm("是否自动修复并保存？"):
                save_nest_config(config_path, cfg)
                click.echo("✅ 已修复")

        click.echo(f"🐱 项目已激活: {project_path}")
        click.echo(f"   默认猫: {cfg.default_cat}")
        click.echo(f"   可用猫: {', '.join(cfg.cats)}")
        if not warnings:
            click.echo("\n  提示: 使用 `neowai start` 启动服务 或 `neowai chat` 开始对话")
