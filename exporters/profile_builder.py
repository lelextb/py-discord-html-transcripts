"""
Profile modal builder for Discord-style user profiles.
Generates HTML fragment for the modal and provides badge/role resolution.
Supports animated banners (GIF/MP4), full role color rendering, and local badge assets.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import discord

from config import config


class ProfileBuilder:
    """
    Constructs user profile data and HTML fragments for the transcript modal.
    Handles badge mapping, role color formatting, and banner URL (including GIFs).
    Supports local asset paths for custom badges like 'quest'.
    """

    # Discord CDN badge icon URLs (official assets) – static for most badges
    BADGE_ICONS = {
        'staff': 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/discordstaff.svg',
        'partner': 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/discordpartner.svg',
        'hypesquad': 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/hypesquadevents.svg',
        'hypesquad_bravery': 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/hypesquadbravery.svg',
        'hypesquad_brilliance': 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/hypesquadbrilliance.svg',
        'hypesquad_balance': 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/hypesquadbalance.svg',
        'early_supporter': 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/discordearlysupporter.svg',
        'bug_hunter': 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/discordbughunter1.svg',
        'bug_hunter_level_2': 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/discordbughunter2.svg',
        'verified_bot_developer': 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/discordbotdev.svg',
        'premium': 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/discordnitro.svg',
        'discord_certified_moderator': 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/discordmod.svg',
        'active_developer': 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/activedeveloper.svg',
        'orb': 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/orb.svg',
        'supportcommands': 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/supportscommands.svg'
    }

    @classmethod
    def _get_badge_icon_url(cls, flag_name: str) -> str:
        """
        Resolve badge icon URL dynamically.
        For 'quest' badge, uses a local asset path defined in config.
        For all others, returns the static URL from BADGE_ICONS.
        """
        if flag_name == 'quest':
            quest_icon_path = getattr(config, 'quest_badge_path', None)
            if quest_icon_path and Path(quest_icon_path).exists():
                return str(Path(quest_icon_path).resolve())
            else:
                default_path = Path(__file__).parent.parent / "assets" / "quest.png"
                if default_path.exists():
                    return str(default_path.resolve())
                return 'https://raw.githubusercontent.com/mezotv/discord-badges/7228546b5ad48561eee7c88d193304f133d52058/assets/quest.png'
        return cls.BADGE_ICONS.get(flag_name, '')

    @staticmethod
    async def get_profile_data(
        user: discord.User,
        member: Optional[discord.Member] = None,
        bot: Optional[discord.Client] = None
    ) -> Dict[str, Any]:
        """
        Extract all profile information for a user.
        
        Args:
            user: Discord user object
            member: Optional member object (for guild-specific data like roles, joined_at)
            bot: Optional bot client (for fetching user banner)
        
        Returns:
            Dictionary containing profile data.
        """
        # Avatar: prefer guild avatar, fallback to user avatar, then default
        avatar_url = str(member.guild_avatar.url) if member and member.guild_avatar else (
            str(user.avatar.url) if user.avatar else "https://cdn.discordapp.com/embed/avatars/0.png"
        )
        if "avatars/0.png" not in avatar_url:
            avatar_url = avatar_url.replace(".webp", ".png?size=256")

        # Banner: requires fetch_user if bot provided
        banner_url = None
        if bot:
            try:
                fetched = await bot.fetch_user(user.id)
                if fetched.banner:
                    banner_url = fetched.banner.url
                    if banner_url.endswith('.gif'):
                        banner_url = banner_url + "?size=512"
            except:
                pass

        # Badges from user public flags
        badges = []
        if hasattr(user, 'public_flags') and user.public_flags:
            flags = user.public_flags
            # Standard flags from BADGE_ICONS
            for flag_name in ProfileBuilder.BADGE_ICONS.keys():
                if getattr(flags, flag_name, False):
                    badge_name = {
                        'hypesquad_bravery': 'HypeSquad Bravery',
                        'hypesquad_brilliance': 'HypeSquad Brilliance',
                        'hypesquad_balance': 'HypeSquad Balance',
                        'bug_hunter_level_2': 'Bug Hunter Level 2',
                        'verified_bot_developer': 'Verified Bot Developer',
                        'discord_certified_moderator': 'Certified Moderator',
                        'active_developer': 'Active Developer'
                    }.get(flag_name, flag_name.replace('_', ' ').title())
                    badges.append({'name': badge_name, 'icon_url': ProfileBuilder._get_badge_icon_url(flag_name)})
            
            # Handle 'quest' badge: check for quest_completed attribute (custom)
            # Modern discord.py may expose quest completion as a user attribute.
            if hasattr(user, 'quest_completed') and user.quest_completed:
                badges.append({'name': 'Quest Completed', 'icon_url': ProfileBuilder._get_badge_icon_url('quest')})

        # Roles (exclude @everyone)
        roles = []
        if member:
            for role in member.roles:
                if role.name != "@everyone":
                    color_hex = f"#{role.color.value:06x}" if role.color.value else "#2b2d31"
                    if role.color.value:
                        r, g, b = ((role.color.value >> 16) & 0xFF), ((role.color.value >> 8) & 0xFF), (role.color.value & 0xFF)
                        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                        text_color = '#000000' if luminance > 0.8 else '#ffffff'
                    else:
                        text_color = '#ffffff'
                    roles.append({
                        'name': role.name,
                        'color': color_hex,
                        'text_color': text_color,
                        'position': role.position
                    })
            roles.sort(key=lambda r: r['position'], reverse=True)

        joined_at = ""
        if member and member.joined_at:
            joined_at = member.joined_at.strftime("%B %d, %Y")
        elif user.created_at:
            joined_at = user.created_at.strftime("%B %d, %Y")

        display_name = member.display_name if member else (user.global_name or user.name)

        return {
            'id': str(user.id),
            'name': display_name,
            'avatar_url': avatar_url,
            'banner_url': banner_url,
            'badges': badges,
            'roles': roles,
            'joined_at': joined_at,
            'created_at': user.created_at.strftime("%B %d, %Y") if user.created_at else ""
        }

    @staticmethod
    def build_modal_html(profile_data: Dict[str, Any]) -> str:
        """Generate the HTML for the profile modal (optional)."""
        banner_style = f"background-image: url('{profile_data['banner_url']}');" if profile_data['banner_url'] else "background-color: #2b2d31;"
        badges_html = ''.join(
            f'<img class="badge-icon" src="{b["icon_url"]}" alt="{b["name"]}" title="{b["name"]}">'
            for b in profile_data['badges']
        )
        roles_html = ''.join(
            f'<span class="role-badge" style="background-color: {r["color"]}; color: {r["text_color"]};">{r["name"]}</span>'
            for r in profile_data['roles']
        )
        return f'''
        <div class="modal-content">
            <div class="modal-banner" style="{banner_style}"></div>
            <div class="modal-avatar">
                <img src="{profile_data['avatar_url']}" alt="Avatar">
            </div>
            <div class="modal-user-info">
                <div>
                    <span class="modal-user-name">{profile_data['name']}</span>
                </div>
                <div class="modal-badges">{badges_html}</div>
                <div class="modal-roles">{roles_html}</div>
            </div>
            <div class="modal-footer">
                <span>Joined: {profile_data['joined_at']}</span>
            </div>
        </div>
        '''

    @staticmethod
    def profile_to_json(profile_data: Dict[str, Any]) -> str:
        """Return JSON representation of profile data for embedding in HTML data attributes."""
        data = profile_data.copy()
        data['banner_url'] = data['banner_url'] or ''
        return json.dumps(data)