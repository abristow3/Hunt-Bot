import discord
from discord import app_commands
import logging

logger = logging.getLogger(__name__)


async def current_score(interaction: discord.Interaction, discord_bot):
    """Handles the /score command to display the current score."""
    cog = discord_bot.get_cog("ScoreCog")
    if not cog:
        logger.warning("ScoreCog not found when executing /score")
        await interaction.response.send_message("No score to display.", ephemeral=True)
        return

    message = getattr(cog, 'score_message', None)
    if not message:
        await interaction.response.send_message("Score is currently unavailable.", ephemeral=True)
        return

    await interaction.response.send_message(message, ephemeral=True)


def register_score_commands(tree: app_commands.CommandTree, discord_bot):
    @tree.command(name="score", description="List current score")
    async def score_cmd(interaction: discord.Interaction):
        await current_score(interaction, discord_bot=discord_bot)
