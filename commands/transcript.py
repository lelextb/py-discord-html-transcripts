"""
Slash command /transcript for exporting a channel to HTML transcript.
Handles permission checks, message fetching, HTML generation, and DM delivery.
"""

import discord
from discord import app_commands

from config import config
from exporters.message_parser import MessageParser
from exporters.html_builder import HTMLBuilder


@app_commands.guild_only()
@app_commands.command(name="transcript", description="Export a text channel to a Discord-style HTML transcript")
async def transcript_command(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    """
    Export a text channel to a Discord-style HTML transcript and send via DM.
    
    Args:
        interaction: The slash command interaction
        channel: The channel to export
    """
    # Defer response immediately – exporting may take time
    await interaction.response.defer(ephemeral=True)

    # Permission checks
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        await interaction.followup.send(
            "❌ Cannot export this channel type. Use a text channel or thread.",
            ephemeral=True
        )
        return

    # Ensure bot has read permissions in target channel
    bot_member = interaction.guild.get_member(interaction.client.user.id)
    if not channel.permissions_for(bot_member).read_messages:
        await interaction.followup.send(
            f"❌ I don't have permission to read messages in {channel.mention}.",
            ephemeral=True
        )
        return

    # Warn user about large channel if needed
    parser = MessageParser(channel)
    warning = await parser.get_message_count_warning()
    if warning:
        await interaction.followup.send(warning, ephemeral=True)

    try:
        # Fetch messages with adaptive pacing
        limit = config.max_messages if config.max_messages > 0 else None
        messages = await parser.fetch_all_messages(limit=limit)

        if not messages:
            await interaction.followup.send(
                f"⚠️ No messages found in {channel.mention}. Transcript not created.",
                ephemeral=True
            )
            return

        # Build HTML transcript
        builder = HTMLBuilder(bot=interaction.client)
        output_path = await builder.build_transcript(
            guild_name=interaction.guild.name,
            channel_name=channel.name,
            messages=messages,
            channel_id=channel.id,
            guild_id=interaction.guild.id
        )

        # Send file via DM
        user = interaction.user
        try:
            with open(output_path, 'rb') as f:
                file = discord.File(f, filename=output_path.name)
                await user.send(
                    f"📄 Transcript for **#{channel.name}** in **{interaction.guild.name}**\n"
                    f"Messages: {len(messages)}",
                    file=file
                )
            await interaction.followup.send(
                f"✅ Transcript sent to your DMs. (Channel: {channel.mention})",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Cannot send you a DM. Please enable DMs from server members and try again.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to send DM: {str(e)}",
                ephemeral=True
            )

    except discord.Forbidden:
        await interaction.followup.send(
            f"❌ Missing permissions to read message history in {channel.mention}.",
            ephemeral=True
        )
    except discord.HTTPException as e:
        await interaction.followup.send(
            f"❌ Discord API error: {str(e)}",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(
            f"❌ Unexpected error: {str(e)}",
            ephemeral=True
        )


def setup(bot: discord.Client):
    """Register the transcript command with the bot's tree."""
    bot.tree.add_command(transcript_command)