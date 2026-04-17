"""
HTML transcript builder using Jinja2 templating.
Renders Discord-style HTML from message data with full profile support.
Includes aggressive caching and throttling to avoid API rate limits.
"""

import json
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
import discord

from config import config
from utils.markdown_parser import MarkdownParser

logger = logging.getLogger(__name__)


class HTMLBuilder:
    """Generates complete HTML transcripts from Discord message data."""

    def __init__(self, bot=None):
        self.bot = bot
        self.markdown_parser = MarkdownParser(bot=bot)
        self.template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.env.filters['filesizeformat'] = self._filesize_filter
        self.env.filters['discord_timestamp'] = self._format_timestamp

        # Cache for user data (avatar, banner, bio, global_name)
        self._user_cache = {}
        # Track last fetch time to throttle
        self._last_fetch_time = 0
        self._fetch_delay = 0.5  # seconds between fetch_user calls

    @staticmethod
    def _filesize_filter(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    @staticmethod
    def _format_timestamp(dt: datetime) -> str:
        """Convert datetime to Discord-style relative/absolute timestamp."""
        now = datetime.now(timezone.utc)
        dt_utc = dt.astimezone(timezone.utc)
        diff = now - dt_utc
        
        if diff.days == 0:
            return f"Today at {dt.strftime('%I:%M %p').lstrip('0')}"
        elif diff.days == 1:
            return f"Yesterday at {dt.strftime('%I:%M %p').lstrip('0')}"
        else:
            return dt.strftime("%m/%d/%Y %I:%M %p").lstrip('0')

    async def _fetch_user_data(self, user_id: int) -> Dict[str, Any]:
        """Fetch user data with caching and rate‑limit throttling."""
        if user_id in self._user_cache:
            return self._user_cache[user_id]

        # Throttle requests to avoid hitting rate limits
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_fetch_time
        if elapsed < self._fetch_delay:
            await asyncio.sleep(self._fetch_delay - elapsed)

        self._last_fetch_time = asyncio.get_event_loop().time()
        try:
            user = await self.bot.fetch_user(user_id)
            data = {
                'banner_url': user.banner.url if user.banner else '',
                'bio': getattr(user, 'bio', '') or getattr(user, 'about', ''),
                'global_name': user.global_name or user.name,
                'avatar_url': str(user.avatar.url) if user.avatar else ''
            }
        except Exception as e:
            logger.warning(f"Failed to fetch user {user_id}: {e}")
            data = {'banner_url': '', 'bio': '', 'global_name': '', 'avatar_url': ''}

        self._user_cache[user_id] = data
        return data

    async def build_transcript(
        self,
        guild_name: str,
        channel_name: str,
        messages: List[discord.Message],
        channel_id: int,
        guild_id: int
    ) -> Path:
        """Build HTML transcript from a list of Discord messages."""
        message_data = []
        for msg in messages:
            try:
                msg_dict = await self._serialize_message(msg)
                message_data.append(msg_dict)
            except Exception as e:
                logger.error(f"Failed to serialize message {msg.id}: {e}")
                message_data.append({
                    'author_id': '0',
                    'author_name': 'Unknown User',
                    'author_username': 'unknown',
                    'author_global_name': '',
                    'author_avatar': 'https://cdn.discordapp.com/embed/avatars/0.png',
                    'author_banner': '',
                    'author_badges_json': '[]',
                    'author_roles_json': '[]',
                    'author_joined_at': '',
                    'author_pronouns': '',
                    'author_status': 'offline',
                    'author_color': '#ffffff',
                    'author_about_me_html': '',
                    'timestamp': datetime.now(),
                    'html_content': '<em>[Message could not be loaded]</em>',
                    'attachments': [],
                    'embeds': [],
                    'components': []
                })

        template = self.env.get_template("transcript_template.html")
        export_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        html_content = template.render(
            guild_name=guild_name,
            channel_name=channel_name,
            message_count=len(messages),
            export_date=export_date,
            messages=message_data
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcript_{guild_id}_{channel_id}_{timestamp}.html"
        output_path = config.transcript_dir / filename

        import aiofiles
        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            await f.write(html_content)

        return output_path

    async def _serialize_message(self, msg: discord.Message) -> Dict[str, Any]:
        """Convert a discord.Message to a dictionary for the template."""
        # --- Replace mentions with HTML spans BEFORE markdown parsing ---
        content = msg.content
        
        # User mentions
        for user in msg.mentions:
            display_name = user.display_name if hasattr(user, 'display_name') else (user.global_name or user.name)
            mention_html = f'<span class="mention mention-user">@{display_name}</span>'
            content = content.replace(f'<@{user.id}>', mention_html)
            content = content.replace(f'<@!{user.id}>', mention_html)
        
        # Role mentions
        for role in msg.role_mentions:
            mention_html = f'<span class="mention mention-role">@{role.name}</span>'
            content = content.replace(f'<@&{role.id}>', mention_html)
        
        # Channel mentions
        for channel in msg.channel_mentions:
            mention_html = f'<span class="mention mention-channel">#{channel.name}</span>'
            content = content.replace(f'<#{channel.id}>', mention_html)

        # --- Now parse markdown (bold, italic, code, etc.) ---
        html_content = ""
        if content:
            try:
                html_content = await self.markdown_parser.parse(content, guild=msg.guild)
            except Exception as e:
                logger.error(f"Markdown parsing failed for message {msg.id}: {e}")
                html_content = content

        # Author data
        author = msg.author
        member = msg.guild.get_member(author.id) if msg.guild else None

        # Highest role color
        author_color = "#ffffff"
        if member and member.roles:
            top_role = max(member.roles, key=lambda r: r.position)
            if top_role.color.value:
                author_color = f"#{top_role.color.value:06x}"

        # Avatar URL – prefer guild avatar, then user avatar, then default
        avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"
        try:
            if member and member.guild_avatar:
                avatar_url = str(member.guild_avatar.url)
            elif author.avatar:
                avatar_url = str(author.avatar.url)
        except Exception:
            pass

        # Banner, bio, global name – use cached fetch_user data if bot available
        banner_url = ""
        about_me_raw = ""
        global_name = author.global_name or author.name
        if self.bot:
            user_data = await self._fetch_user_data(author.id)
            banner_url = user_data.get('banner_url', '')
            about_me_raw = user_data.get('bio', '')
            global_name = user_data.get('global_name', global_name)

        # Badges (from public_flags, no API call needed)
        badges = []
        if hasattr(author, 'public_flags') and author.public_flags:
            flags = author.public_flags
            badge_map = {
                'staff': ('Staff', 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/discordstaff.svg'),
                'partner': ('Partner', 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/discordpartner.svg'),
                'hypesquad': ('HypeSquad', 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/hypesquadevents.svg'),
                'hypesquad_bravery': ('Bravery', 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/hypesquadbravery.svg'),
                'hypesquad_brilliance': ('Brilliance', 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/hypesquadbrilliance.svg'),
                'hypesquad_balance': ('Balance', 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/hypesquadbalance.svg'),
                'early_supporter': ('Early Supporter', 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/discordearlysupporter.svg'),
                'bug_hunter': ('Bug Hunter', 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/discordbughunter1.svg'),
                'bug_hunter_level_2': ('Bug Hunter Level 2', 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/discordbughunter2.svg'),
                'verified_bot_developer': ('Verified Bot Developer', 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/discordbotdev.svg'),
                'premium': ('Nitro', 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/discordnitro.svg'),
                'discord_certified_moderator': ('Certified Moderator', 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/discordmod.svg')
            }
            for flag_name, (badge_name, icon_url) in badge_map.items():
                if getattr(flags, flag_name, False):
                    badges.append({'name': badge_name, 'icon_url': icon_url})
            if hasattr(author, 'quest_completed') and author.quest_completed:
                quest_url = getattr(config, 'quest_badge_path', None)
                if quest_url and Path(quest_url).exists():
                    icon = str(Path(quest_url).resolve())
                else:
                    icon = 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/quest.png'
                badges.append({'name': 'Quest Completed', 'icon_url': icon})

        # Roles (for tooltip)
        roles = []
        if member:
            for role in member.roles:
                if role.name != "@everyone":
                    color_hex = f"#{role.color.value:06x}" if role.color.value else "#2b2d31"
                    text_color = '#000000' if role.color and role.color.value and (0.299 * ((role.color.value >> 16) & 0xFF) + 0.587 * ((role.color.value >> 8) & 0xFF) + 0.114 * (role.color.value & 0xFF)) / 255 > 0.8 else '#ffffff'
                    roles.append({
                        'name': role.name,
                        'color': color_hex,
                        'text_color': text_color,
                        'position': role.position
                    })
            roles.sort(key=lambda r: r['position'], reverse=True)

        # Joined at (server join date)
        joined_at = ""
        if member and member.joined_at:
            joined_at = member.joined_at.strftime("%B %d, %Y")
        elif author.created_at:
            joined_at = author.created_at.strftime("%B %d, %Y")

        # Pronouns
        pronouns = ""
        if hasattr(author, 'pronouns') and author.pronouns:
            pronouns = author.pronouns
        elif member and hasattr(member, 'pronouns') and member.pronouns:
            pronouns = member.pronouns

        # Status
        status = "offline"
        if member:
            if member.status == discord.Status.online:
                status = "online"
            elif member.status == discord.Status.idle:
                status = "idle"
            elif member.status == discord.Status.dnd:
                status = "dnd"
            else:
                status = "offline"

        # About Me HTML
        about_me_html = ""
        if about_me_raw:
            try:
                about_me_html = await self.markdown_parser.parse(about_me_raw, guild=msg.guild)
            except Exception:
                about_me_html = about_me_raw.replace("\n", "<br>")

        # Display name and username
        display_name = member.display_name if member else (global_name or author.name)
        username = author.name

        # Attachments
        attachments = []
        for att in msg.attachments:
            attachments.append({
                'url': att.url,
                'filename': att.filename,
                'size': att.size
            })

        # Embeds
        embeds = []
        for embed in msg.embeds:
            embed_dict = {
                'title': embed.title,
                'description': embed.description,
                'color': f"#{embed.color.value:06x}" if embed.color else "#5865f2",
                'fields': []
            }
            for field in embed.fields:
                embed_dict['fields'].append({
                    'name': field.name,
                    'value': field.value
                })
            embeds.append(embed_dict)

        # Components (buttons)
        components = []
        if msg.components:
            for component_row in msg.components:
                for component in component_row.children:
                    if component.type == 2:  # Button
                        style_map = {1: 'primary', 2: 'secondary', 3: 'success', 4: 'danger', 5: 'link'}
                        components.append({
                            'label': component.label or component.custom_id or 'Button',
                            'style': style_map.get(component.style, 'secondary')
                        })

        return {
            'author_id': str(author.id),
            'author_name': display_name,
            'author_username': username,
            'author_global_name': global_name,
            'author_avatar': avatar_url,
            'author_banner': banner_url,
            'author_badges_json': json.dumps(badges),
            'author_roles_json': json.dumps(roles),
            'author_joined_at': joined_at,
            'author_pronouns': pronouns,
            'author_status': status,
            'author_color': author_color,
            'author_about_me_html': about_me_html,
            'timestamp': msg.created_at,
            'html_content': html_content,
            'attachments': attachments,
            'embeds': embeds,
            'components': components
        }