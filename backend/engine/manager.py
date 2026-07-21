import time
import threading
from typing import Optional
from backend.engine.interface import ModelInterface, ModelInfo
from backend.config import IDLE_UNLOAD_SECONDS


class ModelManager:
    def __init__(self):
        self._models: dict[str, ModelInterface] = {}
        self._loaded: Optional[tuple[str, str, ModelInterface]] = None
        self._last_used: float = 0.0
        self._lock = threading.Lock()
        self._idle_timer: Optional[threading.Timer] = None

    def register(self, name: str, adapter: ModelInterface) -> None:
        self._models[name] = adapter

    def get_available_models(self) -> list[ModelInfo]:
        return [m.get_info() for m in self._models.values()]

    def get_loaded_model(self) -> Optional[tuple[str, str]]:
        with self._lock:
            if self._loaded:
                return (self._loaded[0], self._loaded[1])
            return None

    def load(self, name: str, size: str) -> ModelInterface:
        with self._lock:
            if name not in self._models:
                raise ValueError(f"Unknown model: {name}")

            if self._loaded and self._loaded[0] == name and self._loaded[1] == size:
                self._last_used = time.time()
                self._start_idle_timer()
                return self._loaded[2]

            # 取出 adapter 引用后释放锁，让长时加载不阻塞其他查询
            adapter = self._models[name]
            need_unload = self._loaded
            self._loaded = None  # 标记为切换中

        # 在锁外执行卸载和加载（可能耗时数分钟）
        if need_unload:
            _, _, old_adapter = need_unload
            try:
                old_adapter.unload()
            except Exception:
                pass
            if self._idle_timer:
                self._idle_timer.cancel()
                self._idle_timer = None

        adapter.load(size)

        with self._lock:
            self._loaded = (name, size, adapter)
            self._last_used = time.time()
            self._start_idle_timer()
        return adapter

    def _unload_current(self) -> None:
        if self._loaded:
            name, size, adapter = self._loaded
            adapter.unload()
            self._loaded = None
        if self._idle_timer:
            self._idle_timer.cancel()
            self._idle_timer = None

    def _start_idle_timer(self) -> None:
        if self._idle_timer:
            self._idle_timer.cancel()
        self._idle_timer = threading.Timer(IDLE_UNLOAD_SECONDS, self._idle_check)
        self._idle_timer.daemon = True
        self._idle_timer.start()

    def _idle_check(self) -> None:
        with self._lock:
            if self._loaded and (time.time() - self._last_used) >= IDLE_UNLOAD_SECONDS:
                self._unload_current()

    def unload(self) -> None:
        with self._lock:
            self._unload_current()

    def touch(self) -> None:
        with self._lock:
            self._last_used = time.time()
