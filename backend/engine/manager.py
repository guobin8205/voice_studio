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

            if self._loaded:
                self._unload_current()

            adapter = self._models[name]
            adapter.load(size)
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
