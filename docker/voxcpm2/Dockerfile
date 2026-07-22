# VoxCPM2 standalone container
# 基于 qwen3-tts:with-voxcpm（已装 voxcpm + kaldifst + 所有依赖）
# 提供简洁的 OpenAI 兼容 TTS API，专门服务 VoxCPM2 推理

FROM qwen3-tts:with-voxcpm

WORKDIR /app/voxcpm2-server

# 拷贝服务代码
COPY server.py /app/voxcpm2-server/server.py

ENV HOST=0.0.0.0
ENV PORT=8881
ENV VOXCPM2_MODEL_PATH=/app/models/voxcpm2
ENV PYTHONUNBUFFERED=1

EXPOSE 8881

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8881/health || exit 1

CMD ["python", "/app/voxcpm2-server/server.py"]
