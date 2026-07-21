from fastapi import APIRouter
from backend.utils.gpu import get_gpu_status
from backend.api.models import manager

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
async def system_status():
    gpu = get_gpu_status()
    loaded = manager.get_loaded_model()
    return {
        "gpu": {
            "available": gpu.available,
            "total_gb": round(gpu.total_memory_gb, 1),
            "used_gb": round(gpu.used_memory_gb, 1),
            "utilization_pct": gpu.utilization_pct,
            "temperature_c": gpu.temperature_c,
        },
        "model": {
            "name": loaded[0] if loaded else None,
            "size": loaded[1] if loaded else None,
            "loaded": loaded is not None,
        },
    }
