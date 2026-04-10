import asyncio
from typing import AsyncIterator, Callable, List, Optional
from src.models.types import AgentMessage


async def merge_streams(
    streams: List[AsyncIterator[AgentMessage]],
    on_error: Optional[Callable[[Exception], None]] = None,
) -> AsyncIterator[AgentMessage]:
    if len(streams) == 1:
        try:
            async for msg in streams[0]:
                yield msg
        except Exception as e:
            if on_error:
                on_error(e)
        return

    tasks: dict = {}

    async def _next_item(idx: int):
        return await streams[idx].__anext__()

    for i in range(len(streams)):
        task = asyncio.create_task(_next_item(i))
        tasks[task] = i

    while tasks:
        done, _ = await asyncio.wait(tasks.keys(), return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            idx = tasks.pop(task)
            try:
                msg = task.result()
                yield msg
                new_task = asyncio.create_task(_next_item(idx))
                tasks[new_task] = idx
            except StopAsyncIteration:
                pass
            except Exception as e:
                if on_error:
                    on_error(e)
