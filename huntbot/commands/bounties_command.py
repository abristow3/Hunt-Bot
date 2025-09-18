import discord
from discord import app_commands
import logging
from discord.ext.commands import Bot
from typing import Optional
from huntbot.cogs.Bounties import BountiesCog

logger = logging.getLogger(__name__)

async def fetch_cog(interaction: discord.Interaction, discord_bot: Bot) -> Optional[BountiesCog]:
    cog: Optional[BountiesCog] = discord_bot.get_cog("BountiesCog")
    if not cog:
        await interaction.response.send_message("Bounty Cog is not loaded or active.", ephemeral=True)
        return
    else:
        return cog

async def check_user_roles(interaction: discord.Interaction) -> bool:
    if not any(role.name.lower() == "admin" for role in getattr(interaction.user, "roles", [])):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return False
    else:
        return True


async def current_bounty(interaction: discord.Interaction, discord_bot: Bot) -> None:
    cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot)
    if cog is None:
        return
    
    message = cog.bounty_description or "No bounty currently available"
    clean_message = message.replace("@everyone ", "")
    await interaction.response.send_message(f"**Current Bounty:**\n{clean_message}", ephemeral=True)

async def update_bounty_image(interaction: discord.Interaction, discord_bot: Bot, url: str) -> None:
    cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot)
    if cog is None:
        return
    
    authorized = await check_user_roles(interaction=interaction)
    if not authorized:
        return

    response = await cog.update_embed_url(new_url=url)
    await interaction.response.send_message(response, ephemeral=True)

async def update_bounty_description(interaction: discord.Interaction, description: str, discord_bot: Bot):
    cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot)
    if cog is None:
        return
    
    authorized = await check_user_roles(interaction=interaction)
    if not authorized:
        return

    response = await cog.update_embed_description(new_desc=description)
    await interaction.response.send_message(response, ephemeral=True)

def register_bounties_commands(tree: app_commands.CommandTree, discord_bot: Bot) -> None:
    @tree.command(name="bounty", description="List current active bounty")
    async def bounty_cmd(interaction: discord.Interaction):
        await current_bounty(interaction, discord_bot=discord_bot)

    @tree.command(name="update_bounty_image", description="Update the embedded image in the Bounty")
    @app_commands.describe(image_url="The new image URL")
    async def update_bounty_image_cmd(interaction: discord.Interaction, image_url: str):
        await update_bounty_image(interaction, discord_bot=discord_bot, url=image_url)
    
    @tree.command(name="update_bounty_description", description="Update the description in the current bounty message")
    @app_commands.describe(new_description="The new bounty description")
    async def update_bounty_description_cmd(interaction: discord.Interaction, new_description: str):
        await update_bounty_description(interaction, discord_bot=discord_bot, description=new_description)
