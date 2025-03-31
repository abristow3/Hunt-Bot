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


@bot.tree.command(name="start-hunt", description="Starts the Hunt Bot on the pre-configured date and time")
async def start(interaction: discord.Interaction):
    if interaction.channel.id != hunt_bot.command_channel_id:
        await interaction.response.send_message("Silly goon. You can't run that command in this channel.")
        return

    # Check sheet ID has been populated
    if gdoc.sheet_id == "":
        await interaction.response.send_message("No GDoc sheet ID set. Use the command '/sheet' to set one.")
        return

    # Check sheet name has been populated
    if hunt_bot.sheet_name == "":
        await interaction.response.send_message("No GDoc sheet name set. Use the command '/sheet' to set one.")
        return

    # Import the sheet data
    hunt_bot.set_sheet_data(data=gdoc.get_data_from_sheet(sheet_name=hunt_bot.sheet_name))

    # If no data imported
    if hunt_bot.sheet_data.empty:
        await interaction.response.send_message("Error retrieving Hunt Bot configuration from GDoc. Check if the "
                                                "sheet ID and sheet name are correct.")
        return

    # There is data, so build the table map from the data so we can query it
    hunt_bot.build_table_map()

    # Check table map was created
    if not hunt_bot.table_map:
        await interaction.response.send_message("Error building sheet table map.")
        return

    # Get the HuntBot Configuration variables
    config_data = hunt_bot.pull_table_data(table_name=hunt_bot.config_table_name)

    # Check config data was retrieved
    if not config_data:
        await interaction.response.send_message("Error retrieving config data.")
        return


@bot.tree.command(name="sheet", description="Updates the GDoc sheet ID that the Hunt Bot refernces")
@app_commands.describe(sheet_id="The GDoc sheet ID", sheet_name="The name of the sheet in the GDoc",
                       config_table="Name of the discord configuration table in the sheet")
async def sheet(interaction: discord.Interaction, sheet_id: str, sheet_name: str = "BotConfig",
                config_table: str = "Discord Conf"):
    if interaction.channel.id != hunt_bot.command_channel_id:
        await interaction.response.send_message("Silly goon. You can't run that command in this channel.")
        return

    gdoc.set_sheet_id(sheet_id=sheet_id)
    hunt_bot.set_sheet_name(sheet_name=sheet_name)
    hunt_bot.set_config_table_name(table_name=config_table)
    await interaction.response.send_message(
        f"The GDoc ID has been updated to reference id: {sheet_id}, and sheet name: {sheet_name}")


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

    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.name == hunt_bot.command_channel_name:
                hunt_bot.command_channel_id = channel.id
                return

    if hunt_bot.command_channel_id == "":
        print("NO COMMAND CHANNEL FOUND")


TOKEN = "MTM1MTUzMDI5MjA2MTUzNjI5Nw.G8gCi1.2rgy-ruhqlyBoI7bjYToNa79e2eT59Iw-mvMJM"
# Run bot
bot.run(TOKEN)
# bot.run(hunt_bot.discord_token)
