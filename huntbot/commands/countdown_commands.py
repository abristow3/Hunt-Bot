from typing import Optional
import discord
from discord import app_commands
import logging
from huntbot.HuntBot import HuntBot
from string import Template
from discord.ext.commands import Bot
from datetime import datetime
from huntbot.commands.command_utils import fetch_cog
from huntbot.cogs.Countdown import CountdownCog

logger = logging.getLogger(__name__)

countdown_template = Template("""
The Hunt $action in: $hours Hours and $minutes Minutes
""")

async def current_countdown(interaction: discord.Interaction, hunt_bot: HuntBot, discord_bot: Bot) -> None:
    """Displays the current time until the Hunt begins or ends, stored in the Countdown Cog"""
    cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot, cog_name="CountdownCog", cog_type=CountdownCog)
    if cog is None:
        await interaction.response.send_message("CountdownCog is not available or misconfigured.", ephemeral=True)
        return

    
    if hunt_bot.start_datetime.tzinfo is None:
        logger.warning("[Countdown Commands] Hunt start_datetime is naive (no timezone)")
        await interaction.response.send_message("Countdown time is not properly configured. Yell at Druid.", ephemeral=True)
        return

    # Get current time in the same timezone as start_datetime
    current_time = datetime.now(hunt_bot.start_datetime.tzinfo)

    if not hunt_bot.started:
        action = "begins"
        delta = hunt_bot.start_datetime - current_time
    else:
        action = "ends"
        delta = hunt_bot.end_datetime - current_time

    # If the hunt has ended, set both to 0 to avoid exception
    if delta.total_seconds() <= 0:
        hours, minutes = 0, 0
    else:
        total_minutes = int(delta.total_seconds() // 60)
        hours, minutes = divmod(total_minutes, 60)

    # Create message and send
    message = countdown_template.substitute(action=action, hours=hours, minutes=minutes)
    await interaction.response.send_message(message, ephemeral=True)


def register_countdown_commands(tree: app_commands.CommandTree, hunt_bot: HuntBot, discord_bot: Bot) -> None:
    @tree.command(name="countdown", description="Show time remaining until the Hunt starts or ends")
    async def countdown_cmd(interaction: discord.Interaction):
        logger.info("[Countdown Commands] /countdown command called")
        await current_countdown(interaction=interaction, discord_bot=discord_bot, hunt_bot=hunt_bot)
