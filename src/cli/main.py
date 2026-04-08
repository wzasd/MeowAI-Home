import click
import asyncio
from src.router.agent_router import AgentRouter
from src.cli.thread_commands import thread_cli, get_cat_mention


@click.group()
@click.version_option(version='0.3.0', prog_name='meowai')
def cli():
    """MeowAI Home - 温馨的流浪猫AI收容所 🐱"""
    pass


# 注册 thread 命令
cli.add_command(thread_cli)


@cli.command()
@click.option('--cat', default=None, help='覆盖默认猫（@dev/@review/@research）')
@click.option('--thread', 'thread_id', help='指定 thread ID')
def chat(cat: str, thread_id: str):
    """与猫猫开始对话"""
    from src.thread import ThreadManager

    manager = ThreadManager()
    router = AgentRouter()

    # 确定使用的 thread
    if thread_id:
        if not manager.switch(thread_id):
            click.echo(f"❌ Thread 不存在: {thread_id}")
            return
        thread = manager.get_current()
    else:
        thread = manager.get_current()
        if not thread:
            click.echo("🐱 还没有 thread，正在创建...")
            thread = manager.create("默认会话")
            manager.switch(thread.id)

    # 确定使用的猫
    cat_id = cat.lstrip('@') if cat else thread.current_cat_id

    # 显示状态
    click.echo(f"\n🐱 Thread: {thread.name} | 猫: @{get_cat_mention(cat_id)}")
    click.echo(f"   历史: {len(thread.messages)}条消息")
    click.echo("   (按 Ctrl+C 退出)\n")

    try:
        while True:
            message = click.prompt("你", type=str)

            # 如果没有 @mention，添加默认
            if '@' not in message:
                message = f"@{cat_id} {message}"

            # 添加用户消息到 thread
            thread.add_message("user", message)

            # 路由消息
            try:
                agents = router.route_message(message)

                for agent_info in agents:
                    service = agent_info["service"]
                    name = agent_info["name"]
                    breed_id = agent_info["breed_id"]

                    click.echo(f"\n{name}: ", nl=False)

                    # 构建包含历史上下文的系统提示
                    system_prompt = build_thread_aware_prompt(
                        service, thread, breed_id
                    )

                    # 流式响应
                    async def stream_response():
                        chunks = []
                        async for chunk in service.chat_stream(message, system_prompt):
                            chunks.append(chunk)
                            click.echo(chunk, nl=False)
                        click.echo()
                        return "".join(chunks)

                    response = asyncio.run(stream_response())

                    # 添加猫回复到 thread
                    thread.add_message("assistant", response, cat_id=breed_id)
                    click.echo()

                # 保存 thread
                manager.update_thread(thread)

            except Exception as e:
                click.echo(f"\n❌ 错误: {str(e)}\n")

    except KeyboardInterrupt:
        click.echo(f"\n\n🐱 再见喵～对话已保存到 thread: {thread.name}\n")
        manager.update_thread(thread)


def build_thread_aware_prompt(service, thread, breed_id):
    """构建包含 thread 历史的系统提示"""
    base_prompt = service.build_system_prompt()

    if not thread.messages:
        return base_prompt

    # 添加历史上下文（最近 10 条）
    history_lines = ["\n## 对话历史"]
    for msg in thread.messages[-10:]:
        if msg.role == "user":
            history_lines.append(f"用户: {msg.content}")
        else:
            cat_name = msg.cat_id or "猫"
            history_lines.append(f"{cat_name}: {msg.content[:100]}...")

    return base_prompt + "\n" + "\n".join(history_lines)


if __name__ == '__main__':
    cli()
