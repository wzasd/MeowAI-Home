import click
import asyncio
from src.router.agent_router import AgentRouter


@click.group()
@click.version_option(version='0.2.0', prog_name='meowai')
def cli():
    """MeowAI Home - 温馨的流浪猫AI收容所 🐱"""
    pass


@cli.command()
@click.option('--cat', default='@dev', help='默认对话的猫猫（@dev/@review/@research）')
def chat(cat: str):
    """与猫猫开始对话"""
    router = AgentRouter()

    click.echo(f"🐱 正在启动与 {cat} 的对话...")
    click.echo("💡 提示：在消息中使用 @dev/@review/@research 来指定猫猫")
    click.echo("(按 Ctrl+C 退出对话)\n")

    try:
        while True:
            message = click.prompt("你", type=str)

            # If no @mention, add default
            if '@' not in message:
                message = f"{cat} {message}"

            # Route message
            try:
                agents = router.route_message(message)

                for agent_info in agents:
                    service = agent_info["service"]
                    name = agent_info["name"]

                    click.echo(f"\n{name}: ", nl=False)

                    # Stream response
                    async def stream_response():
                        chunks = []
                        async for chunk in service.chat_stream(message):
                            chunks.append(chunk)
                            click.echo(chunk, nl=False)
                        click.echo()  # Newline after response
                        return "".join(chunks)

                    asyncio.run(stream_response())
                    click.echo()

            except Exception as e:
                click.echo(f"\n❌ 错误: {str(e)}\n")

    except KeyboardInterrupt:
        click.echo(f"\n\n🐱 再见喵～下次再来找我玩！\n")


if __name__ == '__main__':
    cli()
