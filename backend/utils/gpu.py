"""GPU 状态采集。优先使用 nvidia-ml-py，回退 pynvml。非 NVIDIA 环境返回空值。"""
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


def _get_nvml():
    """Try nvidia-ml-py first, then pynvml."""
    try:
        import pynvml as nvml
        return nvml
    except ImportError:
        pass
    try:
        import nvidia_ml_py as nvml
        return nvml
    except ImportError:
        pass
    return None


def get_gpu_status(gpu_index: int = 0) -> GPUStatus:
    nvml = _get_nvml()
    if nvml is None:
        return GPUStatus(available=False, error="nvidia-ml-py or pynvml not installed")

    try:
        nvml.nvmlInit()
        handle = nvml.nvmlDeviceGetHandleByIndex(gpu_index)
        info = nvml.nvmlDeviceGetMemoryInfo(handle)
        util = nvml.nvmlDeviceGetUtilizationRates(handle)
        temp = nvml.nvmlDeviceGetTemperature(handle, nvml.NVML_TEMPERATURE_GPU)
        nvml.nvmlShutdown()
        return GPUStatus(
            available=True,
            total_memory_gb=info.total / 1024**3,
            used_memory_gb=info.used / 1024**3,
            utilization_pct=util.gpu,
            temperature_c=temp,
        )
    except Exception as e:
        return GPUStatus(available=False, error=str(e))
