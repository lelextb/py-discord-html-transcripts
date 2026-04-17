"""
Discord Transcript Bot – Main entry point.
Initializes bot, loads configuration, sets up intents, and syncs slash commands.
"""

import discord
from discord import Intents

from config import config
from commands import transcript


class TranscriptBot(discord.Client):
    """Custom bot client with slash command support."""

    def __init__(self):
        intents = Intents.default()
        intents.message_content = True   # Required for reading message content
        intents.members = True           # Required for member-specific data (roles, join dates)
        intents.guilds = True            # Required for guild/channel access

        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        """Called before bot starts. Registers commands."""
        transcript.setup(self)
        # Sync commands to the specific guild (SERVER_ID from config)
        guild = discord.Object(id=config.server_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print(f"✅ Synced slash commands to guild {config.server_id}")

    async def on_ready(self):
        """Called when bot successfully connects to Discord."""
        print(f"✅ Logged in as {self.user} (ID: {self.user.id})")
        print(f"📁 Transcript directory: {config.transcript_dir}")
        print(f"⚙️ Max messages: {'unlimited' if config.max_messages == 0 else config.max_messages}")
        print(f"⏱️ Rate‑limit pacing: slowdown after {config.slowdown_threshold} messages, sleep {config.sleep_duration}s every {config.burst_size} messages")


def main():
    """Entry point: validate config and start bot."""
    if not config.discord_token or config.discord_token == "your_bot_token_here":
        print("❌ ERROR: DISCORD_TOKEN not set in .env file")
        print("   Copy .env.example to .env and fill in your bot token.")
        return

    if config.server_id == 0:
        print("❌ ERROR: SERVER_ID not set in .env file")
        print("   Copy .env.example to .env and fill in your server/guild ID.")
        return

    bot = TranscriptBot()
    try:
        bot.run(config.discord_token)
    except discord.LoginFailure:
        print("❌ ERROR: Invalid Discord token. Check your .env file.")
    except Exception as e:
        print(f"❌ Fatal error: {e}")


if __name__ == "__main__":
    main()