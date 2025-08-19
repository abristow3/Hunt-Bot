import discord
from discord import app_commands
import logging

logger = logging.getLogger(__name__)


async def current_bounty(interaction: discord.Interaction, discord_bot):
    cog = discord_bot.get_cog("BountiesCog")
    if not cog:
        await interaction.response.send_message("No bounty to display.")
        return

    message = cog.message
    await interaction.response.send_message(f"**Current Bounty:**\n{message}", ephemeral=True)


def register_bounties_commands(tree: app_commands.CommandTree, discord_bot):
    @tree.command(name="bounty", description="List current active bounty")
    async def bounty_cmd(interaction: discord.Interaction):
        await current_bounty(interaction, discord_bot=discord_bot)
