from __future__ import annotations

import asyncio
import logging
import logging.config
import os
import sys
import threading


LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"


def _resolve_level(level: int | str | None) -> int:
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    if isinstance(level, int):
        return level
    resolved = getattr(logging, str(level).upper(), None)
    return resolved if isinstance(resolved, int) else logging.INFO


def _install_exception_hooks() -> None:
    def _sys_excepthook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.getLogger("uncaught").critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    def _threading_excepthook(args):
        if issubclass(args.exc_type, KeyboardInterrupt):
            return
        logging.getLogger("uncaught.thread").critical(
            "Unhandled exception in thread %s",
            args.thread.name if args.thread else "<unknown>",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _sys_excepthook
    if hasattr(threading, "excepthook"):
        threading.excepthook = _threading_excepthook


def install_asyncio_exception_handler(loop: asyncio.AbstractEventLoop) -> None:
    def _handler(_loop: asyncio.AbstractEventLoop, context: dict) -> None:
        exc = context.get("exception")
        message = context.get("message", "Unhandled asyncio exception")
        if exc is not None:
            logging.getLogger("asyncio").error(message, exc_info=exc)
        else:
            logging.getLogger("asyncio").error("%s | context=%r", message, context)

    loop.set_exception_handler(_handler)


def configure_logging(level: int | str | None = None) -> None:
    resolved_level = _resolve_level(level)
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": LOG_FORMAT,
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": resolved_level,
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {
                "level": resolved_level,
                "handlers": ["console"],
            },
        }
    )
    logging.captureWarnings(True)
    _install_exception_hooks()
