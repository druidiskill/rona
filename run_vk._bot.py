#!/usr/bin/env python3
"""Cross-platform launcher for running VK and Telegram bots together."""

from __future__ import annotations

import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _start_bot(script_name: str) -> subprocess.Popen:
    script_path = ROOT / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Не найден файл запуска: {script_path}")
    return subprocess.Popen([sys.executable, str(script_path)], cwd=str(ROOT))


def _terminate_process(proc: subprocess.Popen, name: str, timeout: float = 10.0) -> None:
    if proc.poll() is not None:
        return
    print(f"Останавливаем {name}...")
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"{name} не завершился вовремя, принудительное завершение.")
        proc.kill()
        proc.wait(timeout=5)


def run() -> int:
    processes: list[tuple[str, subprocess.Popen]] = []
    stopping = False

    def _stop_all() -> None:
        nonlocal stopping
        if stopping:
            return
        stopping = True
        for name, proc in processes:
            _terminate_process(proc, name)

    try:
        print("Запуск VK и Telegram ботов...")
        processes.append(("VK бот", _start_bot("run_vk_bot.py")))
        processes.append(("Telegram бот", _start_bot("run_telegram_bot.py")))

        def _handle_sigint(_signum, _frame):
            raise KeyboardInterrupt

        signal.signal(signal.SIGINT, _handle_sigint)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _handle_sigint)

        while True:
            for name, proc in processes:
                code = proc.poll()
                if code is not None:
                    print(f"{name} завершился с кодом {code}.")
                    _stop_all()
                    return code if code != 0 else 1
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\nОстановка по Ctrl+C...")
        _stop_all()
        return 0
    except Exception as e:
        print(f"Ошибка при запуске: {e}")
        _stop_all()
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
