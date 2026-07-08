"""Centralised logging configuration for the GitOps control helper."""

from __future__ import annotations

import logging

_CONFIGURED = False

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Configure root logging once and return the package logger.

    Args:
        level: Log level name (e.g. ``"INFO"``, ``"DEBUG"``).

    Returns:
        The ``gitops-platform`` logger instance.
    """
    global _CONFIGURED
    if not _CONFIGURED:
        logging.basicConfig(
            level=getattr(logging, level.upper(), logging.INFO),
            format=LOG_FORMAT,
            datefmt=DATE_FORMAT,
        )
        _CONFIGURED = True
    logger = logging.getLogger("gitops-platform")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``gitops-platform`` namespace."""
    return logging.getLogger(f"gitops-platform.{name}")
