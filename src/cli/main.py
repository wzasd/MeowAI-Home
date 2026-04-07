import click


@click.group()
@click.version_option(version='0.1.0', prog_name='meowai')
def cli():
    """MeowAI Home - 温馨的流浪猫AI收容所 🐱"""
    pass


@cli.command()
@click.option('--cat', default='阿橘', help='选择要对话的猫猫')
def chat(cat: str):
    """与猫猫开始对话"""
    click.echo(f"🐱 正在启动与 {cat} 的对话...")
    click.echo(f"喵～我是{cat}！有什么可以帮你的吗？")
    click.echo("(按 Ctrl+C 退出对话)")

    try:
        while True:
            message = click.prompt("你", type=str)
            # TODO: 实现真实的对话逻辑
            click.echo(f"{cat}: 喵～收到！这个我熟！")
    except KeyboardInterrupt:
        click.echo(f"\n{cat}: 再见喵～下次再来找我玩！")


if __name__ == '__main__':
    cli()
