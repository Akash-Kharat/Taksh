import asyncio
import httpx
from typing import Callable, Any
from app.core.logger import system_logger

async def execute_with_retry(
    async_func: Callable[[], Any],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0
) -> Any:
    """Executes an async function with exponential backoff retries for transient failures."""
    delay = initial_delay
    
    for attempt in range(1, max_retries + 2): # attempt 1 to max_retries + 1 (total max_retries retries)
        try:
            return await async_func()
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            if attempt > max_retries:
                system_logger.error(f"Transient network failure on attempt {attempt}: {e}. No retries left.")
                raise e
            system_logger.warning(f"Transient network failure on attempt {attempt}: {e}. Retrying in {delay}s...")
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code in (429, 503):
                if attempt > max_retries:
                    system_logger.error(f"Transient HTTP {status_code} failure on attempt {attempt}: {e}. No retries left.")
                    raise e
                system_logger.warning(f"Transient HTTP {status_code} failure on attempt {attempt}: {e}. Retrying in {delay}s...")
            else:
                # Permanent failure (like 400, 401, 403, 404) -> do not retry
                system_logger.error(f"Permanent HTTP {status_code} error: {e}. Failing fast.")
                raise e
        except Exception as e:
            # Other unhandled exception -> fail fast
            system_logger.error(f"Unhandled provider error: {e}. Failing fast.")
            raise e
            
        await asyncio.sleep(delay)
        delay *= backoff_factor
