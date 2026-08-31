"""
Testes Unitarios para o Barramento de Eventos (EventBus).
"""

import pytest
import asyncio
from app.core.event_bus import EventBus, EventType, Event


def test_sync_event_subscription():
    bus = EventBus()
    received_data = []

    def handler(event: Event):
        received_data.append(event.data.get("msg"))

    bus.subscribe(EventType.USER_SPEECH_STARTED, handler)
    bus.publish(EventType.USER_SPEECH_STARTED, {"msg": "hello"})

    assert len(received_data) == 1
    assert received_data[0] == "hello"


@pytest.mark.asyncio
async def test_async_event_subscription():
    bus = EventBus()
    received_data = []

    async def async_handler(event: Event):
        received_data.append(event.data.get("count"))

    bus.subscribe(EventType.AI_RESPONSE_FINISHED, async_handler)
    await bus.publish_async(EventType.AI_RESPONSE_FINISHED, {"count": 42})

    assert len(received_data) == 1
    assert received_data[0] == 42
