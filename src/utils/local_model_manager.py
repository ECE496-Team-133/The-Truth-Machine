"""
Local model manager: Ollama installation, model recommendation, and model lifecycle.
"""

import subprocess
import shutil
import sys
import platform
import requests
from dataclasses import dataclass, asdict
from typing import Optional

from .hardware import HardwareInfo


# Model tiers ordered by capability.
# Each entry: (model_tag, min_ram_gb, description, param_size)
MODEL_TIERS = [
    # Small models (4-8 GB RAM)
    ("qwen2.5:3b",     4,  "Qwen 2.5 3B - lightweight, good multilingual",        "3B"),
    ("llama3.2:3b",    4,  "Llama 3.2 3B - Meta's compact model",                 "3B"),
    ("phi3:mini",      4,  "Phi-3 Mini - Microsoft's efficient model",             "3.8B"),

    # Medium models (8-16 GB RAM)
    ("llama3.1:8b",    8,  "Llama 3.1 8B - strong general purpose",               "8B"),
    ("mistral:7b",     8,  "Mistral 7B - fast and capable",                        "7B"),
    ("qwen2.5:7b",     8,  "Qwen 2.5 7B - strong reasoning",                      "7B"),
    ("gemma2:9b",      8,  "Gemma 2 9B - Google's open model",                     "9B"),

    # Large models (16-32 GB RAM)
    ("llama3.1:70b-q4_0",  24, "Llama 3.1 70B (Q4) - near-GPT-4 quality",         "70B"),
    ("qwen2.5:32b",        24, "Qwen 2.5 32B - excellent reasoning",               "32B"),
    ("mixtral:8x7b",       24, "Mixtral 8x7B - mixture of experts",                "8x7B"),

    # XL models (48+ GB RAM)
    ("llama3.1:70b",   48, "Llama 3.1 70B - full precision, top-tier",             "70B"),
    ("qwen2.5:72b",    48, "Qwen 2.5 72B - frontier open model",                   "72B"),
]

OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434"


@dataclass
class ModelRecommendation:
    model_tag: str
    description: str
    param_size: str
    min_ram_gb: int
    reason: str
    alternatives: list  # list of (model_tag, description) tuples

    def to_dict(self):
        return asdict(self)


def is_ollama_installed() -> bool:
    """Check if the ollama binary is on PATH."""
    return shutil.which("ollama") is not None


def is_ollama_running(base_url: str = OLLAMA_DEFAULT_BASE_URL) -> bool:
    """Check if the Ollama server is responding."""
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def start_ollama() -> bool:
    """Attempt to start the Ollama server (background). Returns True on success."""
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Give it a moment to start
        import time
        for _ in range(10):
            time.sleep(1)
            if is_ollama_running():
                return True
        return False
    except Exception:
        return False


def get_ollama_install_instructions() -> str:
    """Return platform-specific Ollama install instructions."""
    system = platform.system().lower()
    if system == "darwin":
        return (
            "Install Ollama on macOS:\n"
            "  Option 1: brew install ollama\n"
            "  Option 2: Download from https://ollama.com/download/mac\n"
        )
    elif system == "linux":
        return (
            "Install Ollama on Linux:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh\n"
        )
    elif system == "windows":
        return (
            "Install Ollama on Windows:\n"
            "  Download from https://ollama.com/download/windows\n"
        )
    return "Visit https://ollama.com for installation instructions.\n"


def install_ollama_auto() -> bool:
    """
    Attempt automated Ollama installation.
    Returns True if successful, False if manual install is needed.
    """
    system = platform.system().lower()
    try:
        if system == "darwin":
            if shutil.which("brew"):
                print("Installing Ollama via Homebrew...")
                subprocess.check_call(
                    ["brew", "install", "ollama"],
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
                return is_ollama_installed()
        elif system == "linux":
            print("Installing Ollama via install script...")
            subprocess.check_call(
                ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            return is_ollama_installed()
    except Exception as e:
        print(f"Automated installation failed: {e}")
    return False


def recommend_model(hw: HardwareInfo) -> ModelRecommendation:
    """
    Recommend the best model based on detected hardware.

    Strategy:
    - Apple Silicon: unified memory means GPU can use all RAM; prefer larger models
    - NVIDIA GPU: use VRAM as the primary constraint
    - CPU-only: conservative, use RAM minus ~4 GB headroom for the OS
    """
    if hw.gpu.vendor == "apple" and hw.gpu.metal_support:
        # Unified memory -- Ollama uses Metal acceleration automatically.
        # Leave ~4 GB headroom for OS + apps.
        available_gb = hw.ram_gb - 4
    elif hw.gpu.vendor == "nvidia" and hw.gpu.vram_gb > 0:
        available_gb = hw.gpu.vram_gb
    else:
        # CPU-only or AMD without ROCm -- be conservative
        available_gb = hw.ram_gb - 6

    # Walk the tiers and pick the largest model that fits
    best = None
    alternatives = []
    for model_tag, min_ram, desc, param_size in MODEL_TIERS:
        if min_ram <= available_gb:
            if best is not None:
                alternatives.append((best[0], best[2]))
            best = (model_tag, min_ram, desc, param_size)

    if best is None:
        # Fallback to smallest model
        entry = MODEL_TIERS[0]
        return ModelRecommendation(
            model_tag=entry[0],
            description=entry[2],
            param_size=entry[3],
            min_ram_gb=entry[1],
            reason=f"Fallback: only {available_gb:.0f} GB available, using smallest model",
            alternatives=[],
        )

    model_tag, min_ram, desc, param_size = best
    reason_parts = [f"{available_gb:.0f} GB available"]
    if hw.gpu.vendor == "apple":
        reason_parts.append("Apple Silicon with Metal acceleration")
    elif hw.gpu.vendor == "nvidia":
        reason_parts.append(f"NVIDIA {hw.gpu.name}")
    else:
        reason_parts.append("CPU inference")

    # Keep only the last 3 alternatives (closest in capability)
    alternatives = alternatives[-3:]
    alternatives.reverse()

    return ModelRecommendation(
        model_tag=model_tag,
        description=desc,
        param_size=param_size,
        min_ram_gb=min_ram,
        reason=", ".join(reason_parts),
        alternatives=alternatives,
    )


def list_installed_models(base_url: str = OLLAMA_DEFAULT_BASE_URL) -> list[dict]:
    """List models currently downloaded in Ollama."""
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("models", [])
    except Exception:
        pass
    return []


def _normalize_model_name(name: str) -> str:
    """Strip :latest suffix and lowercase for comparison."""
    name = name.strip().lower()
    if name.endswith(":latest"):
        name = name[: -len(":latest")]
    return name


def is_model_installed(model_tag: str, base_url: str = OLLAMA_DEFAULT_BASE_URL) -> bool:
    """Check if a specific model is already pulled."""
    models = list_installed_models(base_url)
    target = _normalize_model_name(model_tag)
    for m in models:
        name = _normalize_model_name(m.get("name", "") or m.get("model", ""))
        if name == target:
            return True
        # Handle partial match: "llama3.1" matches "llama3.1:8b"
        if ":" in target and name == target.split(":")[0]:
            continue  # base without tag isn't a match
        if ":" not in target and name.split(":")[0] == target:
            return True
    return False


def pull_model(model_tag: str, base_url: str = OLLAMA_DEFAULT_BASE_URL) -> bool:
    """
    Pull a model via the Ollama API. Streams progress to stdout.
    Returns True on success.
    """
    try:
        print(f"Pulling model '{model_tag}'... (this may take a while)")
        r = requests.post(
            f"{base_url}/api/pull",
            json={"name": model_tag, "stream": True},
            stream=True,
            timeout=600,
        )
        r.raise_for_status()

        import json as _json
        last_status = ""
        for line in r.iter_lines():
            if line:
                try:
                    data = _json.loads(line)
                    status = data.get("status", "")
                    if status != last_status:
                        # Show download progress
                        total = data.get("total", 0)
                        completed = data.get("completed", 0)
                        if total > 0:
                            pct = (completed / total) * 100
                            print(f"  {status}: {pct:.1f}%", end="\r")
                        else:
                            print(f"  {status}")
                        last_status = status
                except Exception:
                    pass

        print()  # newline after progress
        return is_model_installed(model_tag, base_url)
    except Exception as e:
        print(f"Failed to pull model: {e}")
        return False


def get_all_model_options(hw: HardwareInfo) -> list[dict]:
    """Return all model options that could run on this hardware, with compatibility info."""
    if hw.gpu.vendor == "apple" and hw.gpu.metal_support:
        available_gb = hw.ram_gb - 4
    elif hw.gpu.vendor == "nvidia" and hw.gpu.vram_gb > 0:
        available_gb = hw.gpu.vram_gb
    else:
        available_gb = hw.ram_gb - 6

    options = []
    for model_tag, min_ram, desc, param_size in MODEL_TIERS:
        options.append({
            "model_tag": model_tag,
            "description": desc,
            "param_size": param_size,
            "min_ram_gb": min_ram,
            "compatible": min_ram <= available_gb,
        })
    return options
