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
