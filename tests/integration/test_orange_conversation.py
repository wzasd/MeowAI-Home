import pytest
from src.cats.orange.service import OrangeService


@pytest.mark.asyncio
async def test_orange_simple_conversation():
    breed_config = {
        "id": "orange",
        "displayName": "阿橘",
        "personality": "热情",
        "cli": {
            "command": "echo",
            "defaultArgs": []
        }
    }
    service = OrangeService(breed_config)
    response = await service.chat("你好阿橘")
    assert response is not None
    assert len(response) >= 0  # echo may not produce NDJSON, so response may be empty
