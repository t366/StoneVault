import asyncio

from app.wake_manager import WakeManager


class FakeController:
    def __init__(self, available: bool = True):
        self.available = available
        self.wake_calls = 0
        self.sleep_calls = 0

    def is_available(self) -> bool:
        return self.available

    async def wake(self) -> bool:
        self.wake_calls += 1
        return self.available

    def sleep(self) -> None:
        self.sleep_calls += 1


def _manager(controller, debounce: float = 10.0, timeout: float = 1.0, retries: int = 2):
    return WakeManager(controller, debounce_seconds=debounce, timeout_seconds=timeout, retries=retries)


async def test_concurrent_requests_share_single_wake():
    """属性 3：同一防抖窗口内并发请求仅触发一次唤醒。"""
    controller = FakeController()
    manager = _manager(controller)

    results = await asyncio.gather(*[manager.acquire() for _ in range(5)])
    assert results == [True] * 5
    assert controller.wake_calls == 1
    assert manager.holders == 5

    for _ in range(5):
        manager.release()
    assert manager.holders == 0
    assert controller.sleep_calls == 1


async def test_debounce_window_suppresses_reacquire():
    controller = FakeController()
    manager = _manager(controller, debounce=30.0)

    assert await manager.acquire() is True
    manager.release()

    assert await manager.acquire() is True
    manager.release()
    assert controller.wake_calls == 1


async def test_wake_after_window_expires():
    controller = FakeController()
    manager = _manager(controller, debounce=0.0)

    assert await manager.acquire() is True
    manager.release()
    assert await manager.acquire() is True
    manager.release()
    assert controller.wake_calls == 2


async def test_wake_retries_on_timeout():
    class FailingController(FakeController):
        async def wake(self) -> bool:
            self.wake_calls += 1
            await asyncio.sleep(0.5)
            return True

    controller = FailingController()
    manager = _manager(controller, timeout=0.05, retries=2)
    assert await manager.acquire() is False
    assert controller.wake_calls == 3


async def test_offline_controller_returns_false():
    controller = FakeController(available=False)
    manager = _manager(controller)
    assert await manager.acquire() is False
    assert controller.wake_calls == 0


async def test_holders_block_sleep():
    controller = FakeController()
    manager = _manager(controller)
    await manager.acquire()
    await manager.acquire()
    manager.release()
    assert controller.sleep_calls == 0
    assert manager.holders == 1
    manager.release()
    assert controller.sleep_calls == 1
