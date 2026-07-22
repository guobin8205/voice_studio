"""transformers 兼容补丁（best-effort）。

历史背景：IndexTTS2 直接 import 了新版 transformers（4.53+）中被移除的内部 API：
- QuantizedCacheConfig（已合并到 QuantizedCache）
- _crop_past_key_values（私有函数被移除）
- NEED_SETUP_CACHE_CLASSES_MAPPING、QUANT_BACKEND_CLASSES_MAPPING（常量被移除）

IndexTTS2 已从项目中移除（与 qwen-tts 的 transformers 版本不兼容）。
保留本模块仅为兼容旧调用方（main.py 仍 import patch_transformers_for_indextts），
新代码不应再依赖它。
"""
import sys
import types


def _add_if_missing(module, name, value):
    """如果 module 没有 name 属性，则添加"""
    if not hasattr(module, name):
        setattr(module, name, value)


def patch_transformers_for_indextts():
    """历史兼容入口：现在只做 no-op，避免污染 transformers 全局状态。

    保留函数是为了让 main.py 旧调用 `from backend.utils.compat_patches
    import patch_transformers_for_indextts` 不报错。
    """
    return None
