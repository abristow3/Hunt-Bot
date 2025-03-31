import asyncio
import datetime
import discord
import yaml
from discord.ext import commands, tasks
from discord import app_commands
import os
import logging
from GDoc import GDoc
from HuntBot import HuntBot
from Plugins.Bounties.Bounties import Bounties
from Plugins.Dailies.Dailies import Dailies

'''
TODO LIST:
- Automate "hunt starts in 24 hours, 12, etc. messages
- Automate Quick time event (QTE) (anything that doesnt happen on the 6-hour schedule)
    - on QTE entries, can have field with GMT time for the GMT time QTE should be published
    - Also have Channel ID for where to publish the message
- Automate Hunt score update messages to publish 
- Move config file to GDOC
- Add command to input GDOC Sheet ID for bot to use for Hunt
- Dynamically determine cell ranges for bounties and dailies, etc.
'''

# Setup shit
logging.basicConfig(format="{asctime} - {levelname} - {message}", style="{", datefmt="%Y-%m-%d %H:%M", )
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

gdoc = GDoc()
hunt_bot = HuntBot()


@bot.tree.command(name="beep")
async def beep(interaction: discord.Interaction):
    await interaction.response.send_message("Boop")


@bot.tree.command(name="start", description="Starts the hunt bot on the specified date")
@app_commands.describe(date="The DD/MM/YY format of the hunt start date")
async def start(interaction: discord.Interaction, date: str):
    if gdoc.sheet_id == "":
        await interaction.response.send_message("No GDoc sheet ID set. User the command '/sheet' to set one.",
                                                ephemeral=False)
        return

    config_data = gdoc.get_data_from_sheet(sheet_name=hunt_bot.config_sheet_name, cell_range=hunt_bot.config_cell_range)
    config_map = dict(config_data)
    hunt_bot.setup_config(config_map=config_map)

    # hunt_bot.setup_config()

    # if interaction.channel.id != hunt_bot.staff_channel_id:
    #     await interaction.response.send_message("Silly goon. You can't run that command in this channel.",
    #                                             ephemeral=False)
    #     return
    #
    # await interaction.response.defer(ephemeral=True)
    # await interaction.followup.send(
    #     f"=== The Hunt Bot is scheduled to start running on {date} at {hunt_bot.start_time} GMT ===")
    #
    # # TODO Move these to a startup command that only can be run after initial configuration
    # bounty_task = Bounties(bot=bot, gdoc=gdoc, state=hunt_bot)
    # daily_task = Dailies(bot=bot, gdoc=gdoc, state=hunt_bot)


@bot.tree.command(name="sheet", description="Updates the GDoc sheet ID that the Hunt Bot refernces")
@app_commands.describe(sheetid="The GDoc sheet ID",
                       pull="Whether to pull data from the sheet after updating the ID. Defaults to False")
async def sheet(interaction: discord.Interaction, sheetid: str, pull: bool = False):
    # if interaction.channel.id != hunt_bot.staff_channel_id:
    #     await interaction.response.send_message("Silly goon. You can't run that command in this channel.",
    #                                             ephemeral=False)
    #     return

    gdoc.set_sheet_id(sheet_id=sheetid)
    await interaction.response.send_message(f"The GDoc ID has been updated to reference id: {sheet}", ephemeral=False)


async def sync_commands():
    try:
        await bot.tree.sync()
        print("Slash commands have been successfully refreshed!")
    except Exception as e:
        print(f"Error refreshing commands: {e}")


async def list_commands():
    # List all global commands
    print("Listing all registered commands:")
    for command in bot.tree.get_commands():
        print(f"Command Name: {command.name}, Description: {command.description}")


@bot.event
async def on_ready():
    with open("assets/Etsy_Item_Listing_Photo_copy_189_3_1_2.png", "rb") as avatar_file:
        # Update the bot's avatar
        image = avatar_file.read()
        await bot.user.edit(avatar=image)
        print("FEELS FRANKEN-THURGO MAN")

    await sync_commands()

    # List all commands
    await list_commands()

    print(f"Logged in as {bot.user}")

    # bounty_channel = bot.get_channel(state.bounty_channel_id)
    # daily_channel = bot.get_channel(state.daily_channel_id)
    # staff_channel = bot.get_channel(state.staff_channel_id)
    #
    # if not bounty_channel:
    #     logging.error("Could not find Bounty Channel")
    #
    # if not daily_channel:
    #     logging.error("Could not find Daily Channel")
    #
    # if not staff_channel:
    #     logging.error("Could not find Staff Channel")


TOKEN = "MTM1MTUzMDI5MjA2MTUzNjI5Nw.G8gCi1.2rgy-ruhqlyBoI7bjYToNa79e2eT59Iw-mvMJM"
# Run bot
bot.run(TOKEN)
# bot.run(hunt_bot.discord_token)
