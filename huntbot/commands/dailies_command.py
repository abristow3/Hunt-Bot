import discord
from discord import app_commands
import logging
from discord.ext.commands import Bot
from huntbot.HuntBot import HuntBot
from huntbot.commands.command_utils import check_user_roles, fetch_cog
from huntbot.cogs.Dailies import DailiesCog

logger = logging.getLogger(__name__)
    
async def current_daily(interaction: discord.Interaction, discord_bot: Bot) -> None:
    cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot, cog_name="DailiesCog", cog_type=DailiesCog)
    if cog is None:
        return

    message = cog.daily_description or "No daily currently available"
    clean_message = message.replace("@everyone ", "")
    await interaction.response.send_message(f"**Current Daily:**\n{clean_message}", ephemeral=True)

async def update_daily_image(interaction: discord.Interaction, discord_bot: Bot, url: str) -> None:
    cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot, cog_name="DailiesCog", cog_type=DailiesCog)
    if cog is None:
        return

    authorized_roles = ["admin", "helper", "staff"]
    authorized = await check_user_roles(interaction=interaction, authorized_roles=authorized_roles)
    if not authorized:
        return

    response = await cog.update_embed_url(new_url=url)
    await interaction.response.send_message(response, ephemeral=True)

async def update_daily_description(interaction: discord.Interaction, description: str, discord_bot: Bot):
    cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot, cog_name="DailiesCog", cog_type=DailiesCog)
    if cog is None:
        return

    authorized_roles = ["admin"]
    authorized = await check_user_roles(interaction=interaction, authorized_roles=authorized_roles)
    if not authorized:
        return

    response = await cog.update_embed_description(new_desc=description)
    await interaction.response.send_message(response, ephemeral=True)

async def complete_daily(interaction: discord.Interaction, discord_bot: Bot, hunt_bot: HuntBot, team_color: str) -> None:
    cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot, cog_name="DailiesCog", cog_type=DailiesCog)
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
        await interaction.response.send_message("First and Second place already claimed for the daily", ephemeral=True)
        return
    
    await cog.post_daily_complete_message(team_name=team_color, placement=placement)
    await interaction.response.send_message(f"{placement} place completion message posted succesfully for {team_color}", ephemeral=True)
    

def register_daily_commands(tree: app_commands.CommandTree, discord_bot, hunt_bot: HuntBot) -> None:
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

    @tree.command(name="complete_daily", description="Submits the daily complete and place message for the team")
    async def complete_daily_cmd(interaction: discord.Interaction):
        await complete_daily(interaction, discord_bot=discord_bot, hunt_bot=hunt_bot)

