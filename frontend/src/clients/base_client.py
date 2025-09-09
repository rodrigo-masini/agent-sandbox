# ==============================================
# BASE CLIENT IMPLEMENTATION
# ==============================================

import asyncio
import logging


class BaseClient:
    """Base client with retry logic and error handling."""

    def __init__(
        self, timeout: int = 300, max_retries: int = 3, retry_delay: float = 1.0
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(self.__class__.__name__)

    async def retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry."""
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                wait_time = self.retry_delay * (2**attempt)
                self.logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)

    def log_error(self, message: str, error: Exception):
        """Log error with context."""
        self.logger.error(f"{message}: {error}", exc_info=True)
