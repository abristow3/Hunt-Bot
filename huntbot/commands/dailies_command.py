import discord
from discord import app_commands
import logging
from discord.ext.commands import Bot
from typing import Optional
from huntbot.cogs.Dailies import DailiesCog

logger = logging.getLogger(__name__)

async def fetch_cog(interaction: discord.Interaction, discord_bot: Bot) -> Optional[DailiesCog]:
    cog: Optional[DailiesCog] = discord_bot.get_cog("DailiesCog")
    if not cog:
        await interaction.response.send_message("Daily Cog is not loaded or active.", ephemeral=True)
        return
    else:
        return cog


async def current_daily(interaction: discord.Interaction, discord_bot: Bot) -> None:
    cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot)
    if cog is None:
        return

    message = cog.daily_description or "No daily currently available"
    clean_message = message.replace("@everyone ", "")
    await interaction.response.send_message(f"**Current Daily:**\n{clean_message}", ephemeral=True)

async def update_daily_image(interaction: discord.Interaction, discord_bot: Bot, url: str) -> None:
    cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot)
    if cog is None:
        return
    
    response = await cog.update_embed_url(new_url=url)
    await interaction.response.send_message(response, ephemeral=True)

async def update_daily_description(interaction: discord.Interaction, description: str, discord_bot: Bot):
    cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot)
    if cog is None:
        return
    
    response = await cog.update_embed_description(new_desc=description)
    await interaction.response.send_message(response, ephemeral=True)

def register_daily_commands(tree: app_commands.CommandTree, discord_bot) -> None:
    @tree.command(name="daily", description="List current active daily")
    async def daily_cmd(interaction: discord.Interaction):
        await current_daily(interaction, discord_bot=discord_bot)
    
    @tree.command(name="update_daily_image", description="Update the embedded image in the daily")
    @app_commands.describe(image_url="The new image URL")
    async def update_daily_image_cmd(interaction: discord.Interaction, image_url: str):
        await update_daily_image(interaction, discord_bot=discord_bot, url=image_url)
    
    @tree.command(name="update_daily_description", description="Update the description in the current daily message")
    @app_commands.describe(new_description="The new daily description")
    async def update_daily_description_cmd(interaction: discord.Interaction, new_description: str):
        await update_daily_description(interaction, discord_bot=discord_bot, description=new_description)

