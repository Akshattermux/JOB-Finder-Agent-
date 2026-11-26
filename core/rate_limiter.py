import asyncio
import time
from typing import List


class GeminiRateLimiter:
    """
    Async Sliding Window Rate Limiter for Gemini API.
    Maintains call timestamps to respect Requests Per Minute (RPM) limits on the free tier.
    """
    def __init__(self, rpm_limit: int = 14):
        self.rpm_limit = rpm_limit
        self.window_seconds = 60.0
        self.call_timestamps: List[float] = []
        self._lock = asyncio.Lock()

    async def wait_if_needed(self):
        """Paces execution to stay strictly within the RPM limit."""
        async with self._lock:
            now = time.time()
            # Remove timestamps outside the 60-second window
            self.call_timestamps = [t for t in self.call_timestamps if now - t < self.window_seconds]

            if len(self.call_timestamps) >= self.rpm_limit:
                # Calculate sleep duration to free up the oldest slot
                oldest = self.call_timestamps[0]
                sleep_time = self.window_seconds - (now - oldest) + 0.5  # 0.5s safety buffer
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                # Re-clean after sleep
                now = time.time()
                self.call_timestamps = [t for t in self.call_timestamps if now - t < self.window_seconds]

            self.call_timestamps.append(time.time())
