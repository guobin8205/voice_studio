"""wetext 占位实现（替代 kaldifst 的 TN）。

为什么存在：
- VoxCPM2 的 voxcpm.utils.text_normalize 在 normalize=True 时实例化 wetext.Normalizer
- wetext 依赖 kaldifst，而 kaldifst 在 Python 3.14 + Windows AMD64 上没有预编译 wheel
- 为了避免编译 kaldifst，这里提供一个简化的 Normalizer，做基本的标点和数字清理

局限：
- 不做完整的中文文本归一化（kaldifst 会把"123"转成"一百二十三"等）
- 如果业务需要严格的 TN，请在 Python 3.10/3.11/3.12/3.13 上装真正的 wetext
"""
import re


class Normalizer:
    """简化版 Normalizer：签名兼容 wetext.Normalizer。

    wetext 真实实现基于 kaldifst 做分词/数字转写/标点处理；
    本 stub 只做最小限度的清理，让 VoxCPM2 在 normalize=True 时不崩。
    """

    def __init__(self, lang="zh", operator="tn", remove_erhua=False, **kwargs):
        self.lang = lang
        self.operator = operator
        self.remove_erhua = remove_erhua

    def normalize(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        # 基本清理：去多余空白
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        # 去掉 markdown 残留的标记
        text = re.sub(r"[*_`#]+", "", text)
        # 中文场景下把全角空格转半角
        text = text.replace("\u3000", " ")
        # 儿化音处理（如果启用）：去掉结尾多余的"儿"
        if self.remove_erhua and self.lang == "zh":
            text = re.sub(r"儿(?=[，。！？、,\s]|$)", "", text)
        return text
