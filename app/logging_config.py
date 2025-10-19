import logging
import sys
import structlog
from structlog.types import Processor


def configure_logging(log_level: str = "INFO", is_debug: bool = False):
    """
    Configure structured logging for the entire application.

    - In debug mode, it uses a human-readable console renderer.
    - In production, it uses a JSON renderer.
    """

    # Basic configuration for standard logging (for third-party libraries)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Define structlog processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.UnicodeDecoder(),
    ]

    # Determine the final renderer based on the debug flag
    if is_debug:
        final_processor = structlog.dev.ConsoleRenderer(colors=True)
    else:
        final_processor = structlog.processors.JSONRenderer()

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            final_processor,
        ],
        # Use a standard library logger factory
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Use a wrapper class for compatibility with standard logging
        wrapper_class=structlog.stdlib.BoundLogger,
        # Cache the logger instance for performance
        cache_logger_on_first_use=True,
    )

    log_mode = "development (console)" if is_debug else "production (JSON)"
    # Use standard logging to report startup status. Avoid printing non-ASCII
    # characters (like emoji) which can cause UnicodeEncodeError on some
    # Windows consoles that use cp1252 encoding.
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured in {log_mode} mode with level: {log_level.upper()}")