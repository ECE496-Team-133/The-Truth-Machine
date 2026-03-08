"""
Interactive CLI setup for local model inference.

Run once:  python -m src.setup_local
"""

import sys
import time

from src.utils.hardware import detect_hardware, hardware_summary
from src.utils.local_model_manager import (
    is_ollama_installed,
    is_ollama_running,
    start_ollama,
    get_ollama_install_instructions,
    install_ollama_auto,
    recommend_model,
    is_model_installed,
    pull_model,
    get_all_model_options,
)
from src.utils.local_config import load_config, save_config, LocalModeConfig
from src.utils.openai_client import reset_client


def _banner():
    print()
    print("=" * 60)
    print("  The Truth Machine  --  Local Mode Setup")
    print("=" * 60)
    print()


def _confirm(prompt: str, default: bool = True) -> bool:
    suffix = " [Y/n] " if default else " [y/N] "
    answer = input(prompt + suffix).strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def setup() -> bool:
    """
    Interactive setup flow. Returns True if setup completed successfully.
    """
    _banner()

    # Step 1: Detect hardware
    print("Detecting hardware...\n")
    hw = detect_hardware()
    print(hardware_summary(hw))
    print()

    # Step 2: Recommend model
    rec = recommend_model(hw)
    print(f"Recommended model:  {rec.model_tag}  ({rec.description})")
    print(f"Reason:             {rec.reason}")
    if rec.alternatives:
        print("\nAlternatives (also compatible with your hardware):")
        for tag, desc in rec.alternatives:
            print(f"  - {tag}  ({desc})")
    print()

    # Let user pick
    if not _confirm(f"Use recommended model '{rec.model_tag}'?"):
        print("\nCompatible models for your hardware:\n")
        options = get_all_model_options(hw)
        compatible = [o for o in options if o["compatible"]]
        for i, opt in enumerate(compatible, 1):
            print(f"  {i}. {opt['model_tag']}  --  {opt['description']}  ({opt['param_size']})")
        print()

        while True:
            choice = input(f"Enter number (1-{len(compatible)}) or model tag: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(compatible):
                rec.model_tag = compatible[int(choice) - 1]["model_tag"]
                rec.description = compatible[int(choice) - 1]["description"]
                break
            # Allow typing a custom tag
            if choice:
                rec.model_tag = choice
                rec.description = "custom model"
                break
        print(f"\nSelected model: {rec.model_tag}\n")

    # Step 3: Check / install Ollama
    if not is_ollama_installed():
        print("Ollama is not installed.\n")
        print(get_ollama_install_instructions())
        if _confirm("Attempt automatic installation?"):
            success = install_ollama_auto()
            if not success:
                print("\nAutomatic install failed.")
                print("Please install Ollama manually, then re-run this setup.")
                print(get_ollama_install_instructions())
                return False
            print("Ollama installed successfully!\n")
        else:
            print("\nPlease install Ollama manually, then re-run this setup.")
            return False

    # Step 4: Ensure Ollama is running
    if not is_ollama_running():
        print("Ollama is installed but not running.")
        if _confirm("Start Ollama now?"):
            print("Starting Ollama server...")
            if not start_ollama():
                print(
                    "\nFailed to start Ollama automatically.\n"
                    "Please start it manually with:  ollama serve\n"
                    "Then re-run this setup."
                )
                return False
            print("Ollama is running!\n")
        else:
            print("\nPlease start Ollama manually, then re-run this setup.")
            return False

    # Step 5: Pull model
    if is_model_installed(rec.model_tag):
        print(f"Model '{rec.model_tag}' is already downloaded.\n")
    else:
        print(f"Model '{rec.model_tag}' needs to be downloaded.\n")
        if _confirm(f"Download '{rec.model_tag}' now?"):
            success = pull_model(rec.model_tag)
            if not success:
                print(f"\nFailed to download '{rec.model_tag}'.")
                print(f"You can try manually:  ollama pull {rec.model_tag}")
                return False
            print(f"Model '{rec.model_tag}' is ready!\n")
        else:
            print(
                f"\nYou can download it later with:  ollama pull {rec.model_tag}\n"
                "Re-run this setup after downloading."
            )
            return False

    # Step 6: Save config
    cfg = LocalModeConfig(
        enabled=True,
        model_tag=rec.model_tag,
        ollama_base_url="http://localhost:11434",
        setup_completed=True,
        hardware_summary=hardware_summary(hw),
    )
    save_config(cfg)
    reset_client()

    print("=" * 60)
    print("  Setup complete!  Local mode is now active.")
    print(f"  Model:  {rec.model_tag}")
    print(f"  Server: http://localhost:11434")
    print("=" * 60)
    print()
    print("The system will now use your local model instead of the OpenAI API.")
    print("To switch back to API mode, run:  python -m src.setup_local --disable")
    print("To reconfigure, run:              python -m src.setup_local --reset")
    print()
    return True


def disable_local_mode():
    """Switch back to API mode without deleting the config."""
    cfg = load_config()
    cfg.enabled = False
    save_config(cfg)
    reset_client()
    print("Local mode disabled. The system will use the OpenAI API.")


def enable_local_mode():
    """Re-enable a previously configured local setup."""
    cfg = load_config()
    if not cfg.setup_completed:
        print("No previous setup found. Running setup...")
        setup()
        return
    cfg.enabled = True
    save_config(cfg)
    reset_client()
    print(f"Local mode re-enabled. Using model: {cfg.model_tag}")


def show_status():
    """Print current configuration status."""
    cfg = load_config()
    print()
    if cfg.setup_completed:
        mode = "LOCAL" if cfg.enabled else "API (local setup exists)"
        print(f"  Mode:     {mode}")
        print(f"  Model:    {cfg.model_tag}")
        print(f"  Ollama:   {cfg.ollama_base_url}")
        if cfg.hardware_summary:
            print(f"\n  Hardware at setup time:")
            for line in cfg.hardware_summary.split("\n"):
                print(f"    {line}")
    else:
        print("  No local setup configured. Using OpenAI API.")
        print("  Run:  python -m src.setup_local  to set up local mode.")
    print()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Set up The Truth Machine for local model inference."
    )
    parser.add_argument("--disable", action="store_true", help="Switch to API mode")
    parser.add_argument("--enable", action="store_true", help="Re-enable local mode")
    parser.add_argument("--reset", action="store_true", help="Reset config and run setup again")
    parser.add_argument("--status", action="store_true", help="Show current config")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.disable:
        disable_local_mode()
    elif args.enable:
        enable_local_mode()
    elif args.reset:
        from src.utils.local_config import reset_config
        reset_config()
        reset_client()
        print("Config reset. Running setup...\n")
        setup()
    else:
        existing = load_config()
        if existing.setup_completed and existing.enabled:
            print(f"\nLocal mode is already configured (model: {existing.model_tag}).")
            if _confirm("Re-run setup?", default=False):
                setup()
            else:
                show_status()
        else:
            setup()


if __name__ == "__main__":
    main()
