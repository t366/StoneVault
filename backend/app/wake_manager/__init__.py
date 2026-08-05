import asyncio
import time
from pathlib import Path

from ..config import Config


class WakeController:
    """冷区电源控制抽象。默认实现面向开发/容器环境：

    冷区即本地挂载目录，随时可用；真实 RK3566 环境可继承并重写
    wake()/sleep() 接入 hdparm/mount 等电源管理命令。
    """

    def __init__(self, mount_path: Path) -> None:
        self.mount_path = Path(mount_path)

    def is_available(self) -> bool:
        return self.mount_path.is_dir()

    async def wake(self) -> bool:
        return self.is_available()

    def sleep(self) -> None:
        return None


class WakeManager:
    """冷区按需唤醒管理器（需求 8.1、8.3）。

    - 同一防抖窗口内的并发请求共享同一次唤醒，仅触发一次 wake（属性 3）。
    - 唤醒等待超时后重试，全部失败则返回离线（需求 8.1、8.2）。
    - 所有持有者释放后才允许冷区休眠（需求 8.4）。
    """

    def __init__(
        self,
        controller: WakeController,
        debounce_seconds: float = 10.0,
        timeout_seconds: float = 30.0,
        retries: int = 2,
    ) -> None:
        self.controller = controller
        self.debounce_seconds = debounce_seconds
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self._lock = asyncio.Lock()
        self._holders = 0
        self._last_wake_at = 0.0

    @property
    def holders(self) -> int:
        return self._holders

    def is_mounted(self) -> bool:
        return self.controller.is_available()

    async def acquire(self) -> bool:
        """获取冷区访问权。冷区离线或唤醒失败时返回 False。"""
        async with self._lock:
            if not self.controller.is_available():
                return False
            now = time.monotonic()
            if self._holders > 0 or (now - self._last_wake_at) <= self.debounce_seconds:
                self._holders += 1
                return True
            if not await self._wake_with_retry():
                return False
            self._last_wake_at = time.monotonic()
            self._holders += 1
            return True

    def release(self) -> None:
        """释放冷区访问权；无持有者时允许休眠。"""
        if self._holders > 0:
            self._holders -= 1
        if self._holders == 0:
            self.controller.sleep()

    async def _wake_with_retry(self) -> bool:
        for _ in range(self.retries + 1):
            try:
                ok = await asyncio.wait_for(
                    self.controller.wake(), timeout=self.timeout_seconds
                )
                if ok:
                    return True
            except asyncio.TimeoutError:
                continue
        return False
