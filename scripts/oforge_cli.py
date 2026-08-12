#!/usr/bin/env python3
"""Canonical command-line entry point for oFORGE Designer."""

from __future__ import annotations

import sys

from opool_cli import build_parser, config_from_args, main


__all__ = ["build_parser", "config_from_args", "main"]


if __name__ == "__main__":
    sys.exit(main())
