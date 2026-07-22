"""使 backend.vendor 可作为包导入，并把 wetext stub 注册到 sys.modules。

这样 voxcpm.utils.text_normalize 中的 `from wetext import Normalizer`
会命中此处的 stub，而无需安装 kaldifst。
"""
import sys
import os

# 把本目录加到 sys.path 最前面，让 "import wetext" 找到 backend/vendor/wetext
_VENDOR_DIR = os.path.dirname(os.path.abspath(__file__))
if _VENDOR_DIR not in sys.path:
    sys.path.insert(0, _VENDOR_DIR)
