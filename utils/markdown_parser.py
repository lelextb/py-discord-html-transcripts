"""
Discord-flavored Markdown to HTML converter.
Handles standard markdown, mentions, emojis, and special Discord syntax.
"""

import re
from typing import Optional
from discord_markdown.discord_markdown import convert_to_html


class MarkdownParser:
    """
    Converts Discord message content to HTML that replicates Discord's rendering.
    """

    USER_MENTION_PATTERN = re.compile(r'<@!?(\d+)>')
    CHANNEL_MENTION_PATTERN = re.compile(r'<#(\d+)>')
    ROLE_MENTION_PATTERN = re.compile(r'<@&(\d+)>')
    CUSTOM_EMOJI_PATTERN = re.compile(r'<(a?):(\w+):(\d+)>')
    TIMESTAMP_PATTERN = re.compile(r'<t:(-?\d+)(?::([RrDdTtFf]))?>')

    def __init__(self, bot=None):
        self.bot = bot
        self._user_cache = {}
        self._channel_cache = {}
        self._role_cache = {}

    async def parse(self, content: str, guild=None) -> str:
        if not content:
            return ""

        # First, convert standard markdown (bold, italic, code, etc.)
        html = convert_to_html(content)

        # Then replace Discord-specific mentions, emojis, timestamps
        html = await self._replace_mentions(html, guild)
        html = self._replace_emojis(html)
        html = self._replace_timestamps(html)

        return html

    async def _replace_mentions(self, html: str, guild) -> str:
        # User mentions
        async def user_replacer(match):
            user_id = int(match.group(1))
            name = await self._get_user_name(user_id, guild)
            return f'<span class="mention mention-user">@{name}</span>'

        # Channel mentions
        async def channel_replacer(match):
            channel_id = int(match.group(1))
            name = await self._get_channel_name(channel_id, guild)
            return f'<span class="mention mention-channel">#{name}</span>'

        # Role mentions
        async def role_replacer(match):
            role_id = int(match.group(1))
            name = await self._get_role_name(role_id, guild)
            return f'<span class="mention mention-role">@{name}</span>'

        html = await self._async_sub(self.USER_MENTION_PATTERN, html, user_replacer)
        html = await self._async_sub(self.CHANNEL_MENTION_PATTERN, html, channel_replacer)
        html = await self._async_sub(self.ROLE_MENTION_PATTERN, html, role_replacer)

        return html

    async def _async_sub(self, pattern, text, async_replacer):
        matches = list(pattern.finditer(text))
        if not matches:
            return text
        result = text
        for match in reversed(matches):
            replacement = await async_replacer(match)
            start, end = match.span()
            result = result[:start] + replacement + result[end:]
        return result

    async def _get_user_name(self, user_id: int, guild) -> str:
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        name = "deleted-user"
        if self.bot:
            user = self.bot.get_user(user_id)
            if not user and guild:
                user = guild.get_member(user_id)
            if not user:
                try:
                    user = await self.bot.fetch_user(user_id)
                except:
                    pass
            if user:
                name = user.display_name if hasattr(user, 'display_name') else user.name
        self._user_cache[user_id] = name
        return name

    async def _get_channel_name(self, channel_id: int, guild) -> str:
        if channel_id in self._channel_cache:
            return self._channel_cache[channel_id]
        name = "deleted-channel"
        if guild:
            channel = guild.get_channel(channel_id)
            if channel:
                name = channel.name
        self._channel_cache[channel_id] = name
        return name

    async def _get_role_name(self, role_id: int, guild) -> str:
        if role_id in self._role_cache:
            return self._role_cache[role_id]
        name = "deleted-role"
        if guild:
            role = guild.get_role(role_id)
            if role:
                name = role.name
        self._role_cache[role_id] = name
        return name

    def _replace_emojis(self, html: str) -> str:
        def emoji_replacer(match):
            animated = match.group(1) == 'a'
            name = match.group(2)
            emoji_id = match.group(3)
            url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if animated else 'png'}?v=1"
            return f'<img class="custom-emoji" src="{url}" alt=":{name}:" title="{name}" draggable="false">'
        return self.CUSTOM_EMOJI_PATTERN.sub(emoji_replacer, html)

    def _replace_timestamps(self, html: str) -> str:
        def timestamp_replacer(match):
            timestamp = int(match.group(1))
            format_type = match.group(2) or 'f'
            from datetime import datetime
            dt = datetime.fromtimestamp(timestamp)
            formats = {
                't': '%H:%M', 'T': '%H:%M:%S', 'd': '%Y-%m-%d',
                'D': '%B %d, %Y', 'f': '%B %d, %Y %H:%M',
                'F': '%A, %B %d, %Y %H:%M', 'R': 'relative'
            }
            fmt = formats.get(format_type.lower(), '%Y-%m-%d %H:%M')
            if fmt == 'relative':
                formatted = dt.strftime('%Y-%m-%d %H:%M') + " (relative not supported)"
            else:
                formatted = dt.strftime(fmt)
            return f'<span class="timestamp">{formatted}</span>'
        return self.TIMESTAMP_PATTERN.sub(timestamp_replacer, html)