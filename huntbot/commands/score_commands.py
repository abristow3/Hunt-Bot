import discord
from discord import app_commands
import logging
from discord.ext.commands import Bot
from huntbot.commands.command_utils import fetch_cog

logger = logging.getLogger(__name__)

async def current_score(interaction: discord.Interaction, discord_bot: Bot) -> None:
    """Displays the current score stored in the Score Cog"""
    cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot, cog_name="ScoreCog")
    if cog is None:
        return

    message = getattr(cog, 'score_message', None)
    if not message:
        await interaction.response.send_message("Score is currently unavailable.", ephemeral=True)
        return

    await interaction.response.send_message(message, ephemeral=True)

def register_score_commands(tree: app_commands.CommandTree, discord_bot: Bot) -> None:
    @tree.command(name="score", description="List current score")
    async def score_cmd(interaction: discord.Interaction):
        logger.info("[Score Commands] /score command called")
        await current_score(interaction, discord_bot=discord_bot)
