import discord
from discord import app_commands
import logging

logger = logging.getLogger(__name__)


async def current_daily(interaction: discord.Interaction, discord_bot=None):
    cog = discord_bot.get_cog("DailiesCog")
    if not cog:
        await interaction.response.send_message("Dailies cog is not loaded.")
        return

    message = cog.message
    await interaction.response.send_message(f"**Current Daily:**\n{message}")


def register_daily_commands(tree: app_commands.CommandTree, discord_bot):
    @tree.command(name="daily", description="List current active daily")
    async def daily_cmd(interaction: discord.Interaction):
        await current_daily(interaction, discord_bot=discord_bot)
