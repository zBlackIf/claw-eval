"""Feishu Bot - Main entry point."""
from __future__ import annotations

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Bot entry point - loads config and starts scheduler."""
    # TODO: implement scheduler startup
    logger.info("Bot starting...")
    logger.info("No scheduler configured yet.")


if __name__ == "__main__":
    main()
