import discord
from discord import app_commands
import logging

logger = logging.getLogger(__name__)


async def current_daily(interaction: discord.Interaction, discord_bot=None):
    cog = discord_bot.get_cog("DailiesCog")
    if not cog:
        await interaction.response.send_message("No daily to display.")
        return

    message = cog.message
    await interaction.response.send_message(f"**Current Daily:**\n{message}", ephemeral=True)


def register_daily_commands(tree: app_commands.CommandTree, discord_bot):
    @tree.command(name="daily", description="List current active daily")
    async def daily_cmd(interaction: discord.Interaction):
        await current_daily(interaction, discord_bot=discord_bot)


async def complete_daily(interaction: discord.Interaction, discord_bot=None):
    cog = discord_bot.get_cog("DailiesCog")
    if not cog:
        await interaction.response.send_message("No daily to complete")
        return

    # TODO add this method to Dailies.py
    await cog.complete_daily_message(interaction)

def register_daily_commands(tree: app_commands.CommandTree, discord_bot):
    @tree.command(name="complete_daily", description="Posts the daily completion message for your team")
    @app_commands.describe(team_name="Choose your team")
    @app_commands.choices(
        team_name=[
            app_commands.Choice(name="Team Red", value="Team Red"),
            app_commands.Choice(name="Team Gold", value="Team Gold"),
        ]
    )
    async def complete_daily_cmd(interaction: discord.Interaction, team_name: app_commands.Choice[str]):
        # You can pass the team name to the function if needed
        await complete_daily(interaction, discord_bot=discord_bot)
