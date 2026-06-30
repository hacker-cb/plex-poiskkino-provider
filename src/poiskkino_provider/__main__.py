"""Console entry point: ``python -m poiskkino_provider`` / ``poiskkino-provider``."""

from __future__ import annotations

import logging

import uvicorn

from .config import Settings
from .logging_config import configure_logging

logger = logging.getLogger(__name__)


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    if not settings.api_token:
        logger.warning("POISKKINO_API_TOKEN is empty — set it before serving real requests")
    logger.info("Starting PoiskKino provider on %s:%s", settings.host, settings.port)
    uvicorn.run(
        "poiskkino_provider.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
