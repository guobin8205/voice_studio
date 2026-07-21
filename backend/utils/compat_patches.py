"""transformers 兼容层。

新版 transformers（4.53+）重构了内部 API：
- QuantizedCacheConfig 被合并到 QuantizedCache
- _crop_past_key_values 等私有函数被移除
- NEED_SETUP_CACHE_CLASSES_MAPPING、QUANT_BACKEND_CLASSES_MAPPING 等常量被移除

IndexTTS2 直接 import 这些 API 导致失败。
本 patch 在导入 indextts 之前执行，提供必要的别名。

如果仍有问题，建议用 Python 3.10 + transformers==4.52.1 单独 venv。
"""
import sys
import types


def _add_if_missing(module, name, value):
    """如果 module 没有 name 属性，则添加"""
    if not hasattr(module, name):
        setattr(module, name, value)


def patch_transformers_for_indextts():
    """打补丁让 IndexTTS2 在新版 transformers 上能导入（best-effort）"""
    # 1. transformers.cache_utils：QuantizedCacheConfig
    try:
        import transformers.cache_utils as cu
        if not hasattr(cu, 'QuantizedCacheConfig'):
            if hasattr(cu, 'QuantizedCache'):
                cu.QuantizedCacheConfig = cu.QuantizedCache
            else:
                class _Q:
                    def __init__(self, *a, **kw): pass
                cu.QuantizedCacheConfig = _Q
    except ImportError:
        pass

    # 2. transformers.generation.candidate_generator：_crop_past_key_values
    try:
        import transformers.generation.candidate_generator as cg
        if not hasattr(cg, '_crop_past_key_values'):
            def _stub_crop(*args, **kwargs):
                return args[-1] if len(args) >= 2 else kwargs.get('cache')
            cg._crop_past_key_values = _stub_crop
            import transformers.generation as gen
            gen._crop_past_key_values = _stub_crop
    except ImportError:
        pass

    # 3. transformers.generation.configuration_utils：缺失的常量
    try:
        import transformers.generation.configuration_utils as gcu
        _add_if_missing(gcu, 'NEED_SETUP_CACHE_CLASSES_MAPPING', {})
        _add_if_missing(gcu, 'QUANT_BACKEND_CLASSES_MAPPING', {})
        # 其他可能被移除的常量，提供空 dict 兜底
        for const in ('CACHE_CLASS_MAPPING', 'GENERATION_CONFIG_NAME'):
            _add_if_missing(gcu, const, {})
    except ImportError:
        pass


# 自动执行
patch_transformers_for_indextts()
