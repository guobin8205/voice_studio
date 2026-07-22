"""Docker 容器切换器

管理两个互斥的 TTS 容器：
- qwen3-tts（端口 8880）：CustomVoice 1.7B
- voxcpm2-server（端口 8881）：VoxCPM2 2B

显存约束（12GB 装不下两个同时常驻），所以同时只能跑一个。
Windows 后端调用前会通过这个模块确保正确的容器在跑。

切换 = stop 旧的 + start 新的 + 等待 healthy（~30-60s）。
"""
import os
import time
import json
import subprocess
import urllib.request
import urllib.error
import threading
from typing import Optional


# 容器配置
CONTAINERS = {
    "qwen3tts": {
        "container_name": "qwen3-tts",
        "port": 8880,
        "model_name": "qwen3-tts",
    },
    "voxcpm2": {
        "container_name": "voxcpm2-server",
        "port": 8881,
        "model_name": "voxcpm2",
    },
}

# 切换锁定，避免并发切换
_switch_lock = threading.Lock()
# 当前激活的容器 key（None 表示未知/未初始化）
_active_container: Optional[str] = None


def _docker(args: list, timeout: int = 30) -> tuple:
    """同步执行 docker 命令，返回 (returncode, stdout, stderr)。"""
    cmd = ["docker"] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "timeout"
    except FileNotFoundError:
        return 1, "", "docker not found"


def is_docker_available() -> bool:
    """检查 docker 命令是否可用。"""
    rc, _, _ = _docker(["--version"])
    return rc == 0


def get_container_status(name: str) -> str:
    """返回容器状态：running / exited / missing。"""
    rc, out, _ = _docker(["ps", "-a", "--filter", f"name=^{name}$", "--format", "{{.Status}}"])
    if rc != 0 or not out:
        return "missing"
    if out.startswith("Up"):
        return "running"
    return "exited"


def is_container_healthy(port: int, timeout: float = 2.0) -> bool:
    """通过 /health 端点检查容器是否就绪。"""
    try:
        req = urllib.request.Request(f"http://localhost:{port}/health", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # VoxCPM2 用 backend.ready，qwen3-tts 用 backend.ready
        return bool(data.get("backend", {}).get("ready"))
    except Exception:
        return False


def wait_for_healthy(port: int, container_name: str, max_wait: int = 120) -> bool:
    """等待容器健康，最长 max_wait 秒。"""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        if is_container_healthy(port):
            return True
        # 检查容器是否还活着（避免对死容器空等）
        if get_container_status(container_name) != "running":
            return False
        time.sleep(2)
    return False


def switch_to(target: str, max_wait: int = 120) -> tuple:
    """切换到目标容器，返回 (success, message)。

    如果目标容器已经在跑且健康，立即返回。
    否则停掉另一个容器，启动目标容器，等待 healthy。
    """
    global _active_container

    if target not in CONTAINERS:
        return False, f"Unknown container: {target}"

    with _switch_lock:
        target_cfg = CONTAINERS[target]
        target_name = target_cfg["container_name"]
        target_port = target_cfg["port"]

        # 快速路径：目标已经在跑且健康
        if _active_container == target and is_container_healthy(target_port):
            return True, f"{target} already active"
        if is_container_healthy(target_port):
            _active_container = target
            return True, f"{target} already active (re-detected)"

        # 停掉其它容器（释放显存）
        for key, cfg in CONTAINERS.items():
            if key == target:
                continue
            other_name = cfg["container_name"]
            if get_container_status(other_name) == "running":
                print(f"[switcher] stopping {other_name}...", flush=True)
                rc, _, err = _docker(["stop", other_name], timeout=30)
                if rc != 0:
                    print(f"[switcher] WARN stop {other_name} failed: {err}", flush=True)

        # 启动目标容器
        target_status = get_container_status(target_name)
        if target_status == "missing":
            return False, f"Container {target_name} not created. Run create-container first."
        if target_status != "running":
            print(f"[switcher] starting {target_name}...", flush=True)
            rc, _, err = _docker(["start", target_name], timeout=30)
            if rc != 0:
                return False, f"docker start {target_name} failed: {err}"

        # 等待 healthy
        print(f"[switcher] waiting for {target_name} healthy (up to {max_wait}s)...", flush=True)
        if not wait_for_healthy(target_port, target_name, max_wait=max_wait):
            return False, f"{target_name} failed to become healthy within {max_wait}s"

        _active_container = target
        return True, f"{target} activated"


def ensure_active(target: str, max_wait: int = 120) -> tuple:
    """确保 target 容器是激活的，返回 (success, message)。"""
    return switch_to(target, max_wait=max_wait)


def get_active() -> Optional[str]:
    """返回当前激活的容器 key（None 表示未知）。"""
    return _active_container
