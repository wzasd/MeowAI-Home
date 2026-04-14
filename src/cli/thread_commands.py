import click
import asyncio
from datetime import datetime
from pathlib import Path
from src.thread import ThreadManager


def run_async(coro):
    """运行异步协程，兼容已有事件循环的情况"""
    try:
        loop = asyncio.get_running_loop()
        # 如果已经在事件循环中，使用 ensure_future
        import nest_asyncio
        nest_asyncio.apply()
        return asyncio.run(coro)
    except RuntimeError:
        # 没有运行的事件循环，直接使用 asyncio.run
        return asyncio.run(coro)


def format_thread(thread, is_current=False):
    """格式化 thread 显示"""
    prefix = "* " if is_current else "  "
    status = " [已归档]" if thread.is_archived else ""
    msg_count = len(thread.messages)
    time_str = thread.updated_at.strftime("%m-%d %H:%M")
    return f"{prefix}{thread.id} | {thread.name}{status} | {msg_count}条消息 | {time_str}"


@click.group(name="thread")
def thread_cli():
    """Thread 多会话管理"""
    pass


@thread_cli.command(name="create")
@click.argument("name")
@click.option("--cat", default="@dev", help="默认使用的猫 (@dev/@review/@research)")
@click.option("--project-path", default=lambda: str(Path.cwd()), help="项目目录路径（默认为当前目录）")
def create_thread(name, cat, project_path):
    """创建新 thread"""
    manager = ThreadManager()

    # 解析 cat mention
    cat_map = {"@dev": "orange", "@review": "inky", "@research": "patch"}
    cat_id = cat_map.get(cat, "orange")

    thread = run_async(manager.create(name, current_cat_id=cat_id, project_path=project_path))
    manager.switch(thread.id)  # 自动切换到新 thread

    click.echo(f"✅ 创建 thread: {thread.name} ({thread.id})")
    click.echo(f"   默认猫: {cat}")
    click.echo(f"   项目路径: {project_path}")
    click.echo(f"   已自动切换到此 thread")


@thread_cli.command(name="list")
@click.option("--all", "-a", is_flag=True, help="显示所有 threads（包括归档）")
def list_threads(all):
    """列出所有 threads"""
    manager = ThreadManager()
    threads = run_async(manager.list(include_archived=all))
    current = manager.get_current()

    if not threads:
        click.echo("暂无 thread，使用 `meowai thread create <name>` 创建")
        return

    click.echo(f"\n{'ID':<10} {'名称':<20} {'状态':<10} {'消息数':<8} {'更新时间'}")
    click.echo("-" * 70)

    for thread in threads:
        current_mark = " *" if current and thread.id == current.id else ""
        status = "已归档" if thread.is_archived else "活跃"
        time_str = thread.updated_at.strftime("%m-%d %H:%M")
        click.echo(f"{thread.id}{current_mark:<3} {thread.name:<20} {status:<10} {len(thread.messages):<8} {time_str}")

    click.echo()


@thread_cli.command(name="switch")
@click.argument("thread_id")
def switch_thread(thread_id):
    """切换到指定 thread"""
    manager = ThreadManager()

    if manager.switch(thread_id):
        thread = manager.get_current()
        click.echo(f"✅ 已切换到: {thread.name} ({thread.id})")
        click.echo(f"   消息数: {len(thread.messages)}")
        click.echo(f"   默认猫: @{get_cat_mention(thread.current_cat_id)}")
    else:
        click.echo(f"❌ Thread 不存在: {thread_id}")
        click.echo("   使用 `meowai thread list` 查看所有 threads")


@thread_cli.command(name="rename")
@click.argument("thread_id")
@click.argument("new_name")
def rename_thread(thread_id, new_name):
    """重命名 thread"""
    manager = ThreadManager()

    if run_async(manager.rename(thread_id, new_name)):
        click.echo(f"✅ 已重命名为: {new_name}")
    else:
        click.echo(f"❌ Thread 不存在: {thread_id}")


@thread_cli.command(name="delete")
@click.argument("thread_id")
@click.option("--force", is_flag=True, help="强制删除，不提示")
def delete_thread(thread_id, force):
    """删除 thread"""
    manager = ThreadManager()
    thread = run_async(manager.get(thread_id))

    if not thread:
        click.echo(f"❌ Thread 不存在: {thread_id}")
        return

    if not force:
        click.confirm(f"确定删除 thread '{thread.name}'? 此操作不可撤销。", abort=True)

    run_async(manager.delete(thread_id))
    click.echo(f"✅ 已删除: {thread.name}")


@thread_cli.command(name="archive")
@click.argument("thread_id")
def archive_thread(thread_id):
    """归档 thread"""
    manager = ThreadManager()
    thread = run_async(manager.get(thread_id))

    if not thread:
        click.echo(f"❌ Thread 不存在: {thread_id}")
        return

    run_async(manager.archive(thread_id))
    click.echo(f"✅ 已归档: {thread.name}")
    click.echo("   使用 `meowai thread list --all` 查看")


@thread_cli.command(name="info")
def thread_info():
    """显示当前 thread 信息"""
    manager = ThreadManager()
    thread = manager.get_current()

    if not thread:
        click.echo("当前没有活跃的 thread")
        click.echo("使用 `meowai thread create <name>` 创建，或 `meowai thread switch <id>` 切换")
        return

    click.echo(f"\n当前 Thread: {thread.name}")
    click.echo(f"  ID: {thread.id}")
    click.echo(f"  消息数: {len(thread.messages)}")
    click.echo(f"  默认猫: @{get_cat_mention(thread.current_cat_id)}")
    click.echo(f"  状态: {'已归档' if thread.is_archived else '活跃'}")
    click.echo(f"  创建时间: {thread.created_at.strftime('%Y-%m-%d %H:%M')}")
    click.echo(f"  更新时间: {thread.updated_at.strftime('%Y-%m-%d %H:%M')}")


def get_cat_mention(cat_id: str) -> str:
    """获取 cat 的 mention 名称"""
    try:
        from src.cli.main import bootstrap_registries
        cat_reg, _ = bootstrap_registries()
        cfg = cat_reg.try_get(cat_id)
        if cfg:
            return cfg.display_name or cat_id
    except Exception:
        pass
    return cat_id
