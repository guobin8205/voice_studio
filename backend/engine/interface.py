from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ModelCapability(Enum):
    VOICE_DESIGN = "voice_design"
    VOICE_CLONE = "voice_clone"
    EMOTION_CONTROL = "emotion_control"


@dataclass
class TTSInput:
    text: str
    language: str = "zh"
    dialect: Optional[str] = None
    prompt: Optional[str] = None
    emotion: Optional[str] = None
    reference_audio: Optional[str] = None
    speed: float = 1.0
    pitch: float = 0.0
    temperature: float = 0.4
    top_p: float = 0.9


@dataclass
class TTSOutput:
    audio_path: str
    duration_seconds: float
    sample_rate: int
    waveform_data: list[float] = field(default_factory=list)


@dataclass
class ModelInfo:
    name: str
    display_name: str
    sizes: list[str]
    capabilities: list[ModelCapability]
    supported_languages: list[str]
    supported_dialects: list[str]


class ModelInterface(ABC):
    """每个 TTS 模型需要实现的统一接口"""

    @abstractmethod
    def get_info(self) -> ModelInfo:
        """返回模型元信息"""
        ...

    @abstractmethod
    def load(self, size: str) -> None:
        """加载模型到 GPU，size 如 '1.7B'"""
        ...

    @abstractmethod
    def unload(self) -> None:
        """卸载模型释放显存"""
        ...

    @abstractmethod
    def is_loaded(self) -> bool:
        """是否已加载"""
        ...

    @abstractmethod
    def generate(self, input: TTSInput) -> TTSOutput:
        """提示词驱动生成"""
        ...

    @abstractmethod
    def clone(self, input: TTSInput) -> TTSOutput:
        """参考音频驱动克隆"""
        ...

    @abstractmethod
    def extract_embedding(self, audio_path: str) -> str:
        """从音频提取说话人嵌入，返回存储路径"""
        ...
