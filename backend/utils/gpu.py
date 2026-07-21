"""GPU 状态采集，使用 pynvml（NVIDIA GPU）。非 NVIDIA 环境返回空值。"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class GPUStatus:
    available: bool
    total_memory_gb: float = 0.0
    used_memory_gb: float = 0.0
    utilization_pct: float = 0.0
    temperature_c: float = 0.0
    error: Optional[str] = None


def get_gpu_status(gpu_index: int = 0) -> GPUStatus:
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        pynvml.nvmlShutdown()
        return GPUStatus(
            available=True,
            total_memory_gb=info.total / 1024**3,
            used_memory_gb=info.used / 1024**3,
            utilization_pct=util.gpu,
            temperature_c=temp,
        )
    except Exception as e:
        return GPUStatus(available=False, error=str(e))
