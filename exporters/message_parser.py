"""
Message fetcher with adaptive rate‑limit protection using configuration.
Implements configurable slowdown threshold and burst pacing.
"""

import asyncio
from typing import List, Optional, AsyncIterator, Union
import discord

from config import config


class MessageParser:
    """
    Handles async retrieval of channel messages with built‑in backoff.
    Respects config values:
        slowdown_threshold (default 45)  → messages before enabling delays
        burst_size (default 30)          → messages per batch before sleep
        sleep_duration (default 1.0)     → seconds to sleep per burst
    """

    def __init__(self, channel: Union[discord.TextChannel, discord.Thread]):
        self.channel = channel
        self._message_cache: List[discord.Message] = []

        # Load adaptive pacing from global config
        self.slowdown_threshold = config.slowdown_threshold
        self.burst_size = config.burst_size
        self.sleep_duration = config.sleep_duration

    async def fetch_all_messages(self, limit: Optional[int] = None) -> List[discord.Message]:
        """
        Retrieve all messages from the channel.
        If `limit` is None, fetches unlimited (Discord pagination).
        Implements adaptive sleep when total > slowdown_threshold.
        """
        self._message_cache.clear()
        count = 0

        async for message in self.channel.history(limit=limit, oldest_first=True):
            self._message_cache.append(message)
            count += 1

            if count > self.slowdown_threshold and count % self.burst_size == 0:
                await asyncio.sleep(self.sleep_duration)

        return self._message_cache

    async def fetch_messages_streaming(
        self, limit: Optional[int] = None
    ) -> AsyncIterator[discord.Message]:
        """
        Generator that yields messages one by one with the same pacing.
        Useful for large channels to avoid building full list in memory.
        """
        count = 0
        async for message in self.channel.history(limit=limit, oldest_first=True):
            yield message
            count += 1
            if count > self.slowdown_threshold and count % self.burst_size == 0:
                await asyncio.sleep(self.sleep_duration)

    def get_cached_messages(self) -> List[discord.Message]:
        """Return messages from last fetch_all_messages() call."""
        return self._message_cache.copy()

    async def get_approximate_message_count(self) -> int:
        """
        Quick estimate of total messages in channel (not exact, but useful for warnings).
        Uses the first 100 messages from newest to oldest as a rough gauge.
        """
        count = 0
        async for _ in self.channel.history(limit=100, oldest_first=False):
            count += 1
        if count == 100:
            async for _ in self.channel.history(limit=101, oldest_first=False):
                if count == 100:
                    count = 101
                break
        return count

    async def get_message_count_warning(self) -> Optional[str]:
        """
        Returns a warning string if the channel likely contains more than
        slowdown_threshold messages, to be sent to user before starting export.
        """
        approx = await self.get_approximate_message_count()
        if approx > self.slowdown_threshold:
            return (
                f"⚠️ Channel has approximately {approx}+ messages. "
                f"The bot will pace itself (sleep {self.sleep_duration}s every {self.burst_size} messages) "
                f"to avoid rate limits. This may take a while."
            )
        return None