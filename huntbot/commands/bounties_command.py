import discord
from discord import app_commands
import logging
from discord.ext.commands import Bot
from typing import Optional
from huntbot.cogs.Bounties import BountiesCog
from huntbot.HuntBot import HuntBot

logger = logging.getLogger(__name__)

async def fetch_cog(interaction: discord.Interaction, discord_bot: Bot) -> Optional[BountiesCog]:
    cog: Optional[BountiesCog] = discord_bot.get_cog("BountiesCog")
    if not cog:
        await interaction.response.send_message("Bounty Cog is not loaded or active.", ephemeral=True)
        return
    else:
        return cog

async def check_user_roles(interaction: discord.Interaction, authorized_roles: list) -> bool:
    user_roles = [role.name.lower() for role in getattr(interaction.user, "roles", [])]
    authorized_roles = [role.lower() for role in authorized_roles]

    if any(role in user_roles for role in authorized_roles):
        return True
    else:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return False


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
    
    authorized_roles = ["admin", "staff", "helper"]
    authorized = await check_user_roles(interaction=interaction, authorized_roles=authorized_roles)
    if not authorized:
        return

    response = await cog.update_embed_url(new_url=url)
    await interaction.response.send_message(response, ephemeral=True)

async def update_bounty_description(interaction: discord.Interaction, description: str, discord_bot: Bot) -> None:
    cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot)
    if cog is None:
        return
    
    authorized_roles = ["admin"]
    authorized = await check_user_roles(interaction=interaction, authorized_roles=authorized_roles)
    if not authorized:
        return

    response = await cog.update_embed_description(new_desc=description)
    await interaction.response.send_message(response, ephemeral=True)

async def complete_bounty(interaction: discord.Interaction, discord_bot: Bot, hunt_bot: HuntBot, team_color: str) -> None:
    cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot)
    if cog is None:
        return

    authorized_roles = ["staff", f"{hunt_bot.team_one_name}_team_leader", f"{hunt_bot.team_two_name}_team_leader", "admin", "helper"]
    authorized = await check_user_roles(interaction=interaction, authorized_roles=authorized_roles)
    if not authorized:
        return
    
    # Check if first place has been claimed yet
    if cog.first_place == "":
        # if it is empty, then it hasn't so associate team color with it
        cog.first_place = team_color
        placement= "First"
    elif cog.first_place != "" and cog.second_place == "":
        # Otherwise it has been claimed so take second place instead
        cog.second_place = team_color
        placement="Second"
    elif cog.first_place != "" and cog.second_place != "":
        await interaction.response.send_message("First and Second place already claimed for the bounty", ephemeral=True)
        return
    
    await cog.post_bounty_complete_message(team_name=team_color, placement=placement)
    await interaction.response.send_message(f"{placement} place completion message posted succesfully for {team_color}", ephemeral=True)
    
    
def register_bounties_commands(tree: app_commands.CommandTree, discord_bot: Bot, hunt_bot: HuntBot) -> None:
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

    @tree.command(name="complete_bounty", description="Submits the bounty complete and place message for the team")
    @app_commands.describe(team_color="Team color that completed the bounty")
    async def complete_bounty_cmd(interaction: discord.Interaction):
        await complete_bounty(interaction, discord_bot=discord_bot, hunt_bot=hunt_bot)
