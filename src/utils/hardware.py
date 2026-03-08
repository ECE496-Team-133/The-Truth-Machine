"""
Hardware detection for recommending the best local model.
Detects RAM, CPU, GPU (NVIDIA/Apple Metal/AMD), and OS.
"""

import os
import platform
import subprocess
import re
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class GPUInfo:
    vendor: str  # "nvidia", "apple", "amd", "none"
    name: str = ""
    vram_gb: float = 0.0
    metal_support: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass
class HardwareInfo:
    os_name: str  # "darwin", "linux", "windows"
    os_version: str
    arch: str  # "arm64", "x86_64"
    cpu_name: str
    cpu_cores: int
    cpu_threads: int
    ram_gb: float
    gpu: GPUInfo = field(default_factory=lambda: GPUInfo(vendor="none"))

    def to_dict(self):
        d = asdict(self)
        return d


def _get_cpu_name() -> str:
    system = platform.system().lower()
    try:
        if system == "darwin":
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                stderr=subprocess.DEVNULL, text=True
            ).strip()
            if out:
                return out
            # Apple Silicon doesn't have brand_string; use chip name
            out = subprocess.check_output(
                ["sysctl", "-n", "hw.model"],
                stderr=subprocess.DEVNULL, text=True
            ).strip()
            return out or "Unknown"
        elif system == "linux":
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
        elif system == "windows":
            out = subprocess.check_output(
                ["wmic", "cpu", "get", "name"],
                stderr=subprocess.DEVNULL, text=True
            )
            lines = [l.strip() for l in out.strip().split("\n") if l.strip() and l.strip() != "Name"]
            if lines:
                return lines[0]
    except Exception:
        pass
    return platform.processor() or "Unknown"


def _get_ram_gb() -> float:
    system = platform.system().lower()
    try:
        if system == "darwin":
            out = subprocess.check_output(
                ["sysctl", "-n", "hw.memsize"],
                stderr=subprocess.DEVNULL, text=True
            ).strip()
            return int(out) / (1024 ** 3)
        elif system == "linux":
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        kb = int(re.search(r"\d+", line).group())
                        return kb / (1024 ** 2)
        elif system == "windows":
            out = subprocess.check_output(
                ["wmic", "computersystem", "get", "totalphysicalmemory"],
                stderr=subprocess.DEVNULL, text=True
            )
            lines = [l.strip() for l in out.strip().split("\n") if l.strip() and l.strip() != "TotalPhysicalMemory"]
            if lines:
                return int(lines[0]) / (1024 ** 3)
    except Exception:
        pass

    # Fallback: try psutil
    try:
        import psutil
        return psutil.virtual_memory().total / (1024 ** 3)
    except ImportError:
        pass
    return 0.0


def _detect_nvidia_gpu() -> Optional[GPUInfo]:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        if out:
            parts = out.split(",")
            name = parts[0].strip()
            vram_mb = float(parts[1].strip())
            return GPUInfo(
                vendor="nvidia",
                name=name,
                vram_gb=round(vram_mb / 1024, 1),
            )
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return None


def _detect_apple_gpu() -> Optional[GPUInfo]:
    if platform.system().lower() != "darwin":
        return None
    try:
        arch = platform.machine().lower()
        if arch == "arm64":
            # Apple Silicon -- unified memory, Metal support
            out = subprocess.check_output(
                ["system_profiler", "SPDisplaysDataType"],
                stderr=subprocess.DEVNULL, text=True
            )
            chip_match = re.search(r"Chipset Model:\s*(.+)", out)
            name = chip_match.group(1).strip() if chip_match else "Apple Silicon GPU"
            # Unified memory: the GPU can use all RAM
            ram_gb = _get_ram_gb()
            return GPUInfo(
                vendor="apple",
                name=name,
                vram_gb=round(ram_gb, 1),
                metal_support=True,
            )
        else:
            # Intel Mac -- check for discrete GPU
            out = subprocess.check_output(
                ["system_profiler", "SPDisplaysDataType"],
                stderr=subprocess.DEVNULL, text=True
            )
            chip_match = re.search(r"Chipset Model:\s*(.+)", out)
            vram_match = re.search(r"VRAM.*?:\s*(\d+)\s*(MB|GB)", out, re.IGNORECASE)
            if chip_match:
                name = chip_match.group(1).strip()
                vram_gb = 0.0
                if vram_match:
                    val = float(vram_match.group(1))
                    unit = vram_match.group(2).upper()
                    vram_gb = val if unit == "GB" else val / 1024
                return GPUInfo(
                    vendor="apple",
                    name=name,
                    vram_gb=round(vram_gb, 1),
                    metal_support=True,
                )
    except Exception:
        pass
    return None


def _detect_amd_gpu() -> Optional[GPUInfo]:
    try:
        out = subprocess.check_output(
            ["rocm-smi", "--showmeminfo", "vram", "--csv"],
            stderr=subprocess.DEVNULL, text=True
        )
        if out:
            # Parse rocm-smi output for VRAM
            vram_match = re.search(r"(\d+)", out)
            vram_gb = int(vram_match.group(1)) / (1024 ** 3) if vram_match else 0
            name_out = subprocess.check_output(
                ["rocm-smi", "--showproductname", "--csv"],
                stderr=subprocess.DEVNULL, text=True
            )
            name = "AMD GPU"
            name_match = re.search(r"card\d+,(.+)", name_out)
            if name_match:
                name = name_match.group(1).strip()
            return GPUInfo(vendor="amd", name=name, vram_gb=round(vram_gb, 1))
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return None


def detect_hardware() -> HardwareInfo:
    """Detect system hardware capabilities."""
    system = platform.system().lower()
    cpu_count = os.cpu_count() or 1

    # Try to get physical core count
    try:
        import psutil
        physical_cores = psutil.cpu_count(logical=False) or cpu_count
    except ImportError:
        physical_cores = cpu_count

    gpu = _detect_nvidia_gpu() or _detect_apple_gpu() or _detect_amd_gpu()
    if gpu is None:
        gpu = GPUInfo(vendor="none")

    return HardwareInfo(
        os_name=system,
        os_version=platform.version(),
        arch=platform.machine(),
        cpu_name=_get_cpu_name(),
        cpu_cores=physical_cores,
        cpu_threads=cpu_count,
        ram_gb=round(_get_ram_gb(), 1),
        gpu=gpu,
    )


def hardware_summary(hw: HardwareInfo) -> str:
    """Return a human-readable summary of detected hardware."""
    lines = [
        f"OS:       {hw.os_name} ({hw.arch})",
        f"CPU:      {hw.cpu_name} ({hw.cpu_cores} cores / {hw.cpu_threads} threads)",
        f"RAM:      {hw.ram_gb:.1f} GB",
    ]
    if hw.gpu.vendor != "none":
        gpu_line = f"GPU:      {hw.gpu.name}"
        if hw.gpu.vram_gb > 0:
            gpu_line += f" ({hw.gpu.vram_gb:.1f} GB VRAM)"
        if hw.gpu.metal_support:
            gpu_line += " [Metal]"
        lines.append(gpu_line)
    else:
        lines.append("GPU:      None detected")
    return "\n".join(lines)
