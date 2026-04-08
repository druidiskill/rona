from __future__ import annotations

import logging
import signal
import subprocess
import sys
import time
from pathlib import Path

from app.bootstrap import configure_logging


ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)


def _start_entrypoint(module_name: str, name: str) -> tuple[str, subprocess.Popen]:
    proc = subprocess.Popen([sys.executable, "-m", module_name], cwd=str(ROOT))
    return name, proc


def _terminate_process(proc: subprocess.Popen, name: str, timeout: float = 10.0) -> None:
    if proc.poll() is not None:
        return
    logger.info("Останавливаем %s...", name)
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        logger.warning("%s не завершился вовремя, принудительное завершение.", name)
        proc.kill()
        proc.wait(timeout=5)


def run() -> int:
    configure_logging()
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
        logger.info("Запуск VK и Telegram ботов...")
        processes.append(_start_entrypoint("app.entrypoints.vk", "VK бот"))
        processes.append(_start_entrypoint("app.entrypoints.tg", "Telegram бот"))

        def _handle_sigint(_signum, _frame):
            raise KeyboardInterrupt

        signal.signal(signal.SIGINT, _handle_sigint)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _handle_sigint)

        while True:
            for name, proc in processes:
                code = proc.poll()
                if code is not None:
                    logger.error("%s завершился с кодом %s.", name, code)
                    _stop_all()
                    return code if code != 0 else 1
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Остановка по Ctrl+C...")
        _stop_all()
        return 0
    except Exception:
        logger.exception("Ошибка при запуске entrypoint all")
        _stop_all()
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
