import pytest
from src.cats.orange.service import OrangeService


@pytest.mark.asyncio
async def test_orange_simple_conversation():
    service = OrangeService()
    response = await service.chat("你好阿橘")
    assert response is not None
    assert len(response) > 0
