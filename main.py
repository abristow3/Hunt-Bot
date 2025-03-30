import asyncio
import datetime
import discord
import yaml
from discord.ext import commands, tasks
from discord import app_commands
import os
import logging
from gdoc import GDoc
from BotState import BotState
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
state = BotState()


@bot.tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")


@bot.tree.command(name="hello")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("Hello there!")


@bot.tree.command(name="goodbye")
async def goodbye(interaction: discord.Interaction):
    await interaction.response.send_message("Goodbye!")


@bot.tree.command(name="start", description="Starts the hunt bot on the specified date")
@app_commands.describe(date="The DD/MM/YY format of the hunt start date")
async def start(interaction: discord.Interaction, date: str):
    if interaction.channel.id != state.staff_channel_id:
        await interaction.response.send_message("Silly goon. You can't run that command in this channel.",
                                                ephemeral=False)
        return

    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(
        f"=== The Hunt Bot is scheduled to start running on {date} at {state.start_time} GMT ===")

    # TODO Move these to a startup command that only can be run after initial configuration
    bounty_task = Bounties(bot=bot, gdoc=gdoc, state=state)
    daily_task = Dailies(bot=bot, gdoc=gdoc, state=state)


@bot.tree.command(name="sheet", description="Updates the GDoc sheet ID that the Hunt Bot refernces")
@app_commands.describe(sheetid="The GDoc sheet ID",
                       pull="Whether to pull data from the sheet after updating the ID. Defaults to False")
async def sheet(interaction: discord.Interaction, sheetid: str, pull: bool = False):
    if interaction.channel.id != state.staff_channel_id:
        await interaction.response.send_message("Silly goon. You can't run that command in this channel.",
                                                ephemeral=False)
        return

    # TODO should probably try to send a request to pull the sheet data and on a 200 respond with that, otherwise return the error

    gdoc.set_sheet_id(sheet_id=sheetid)

    if pull:
        gdoc.pull_sheets()
        sheet_data = gdoc.get_sheet(sheet_name="Bot Config")
        if 'values' in sheet_data and sheet_data['values']:
            for row in sheet_data['values']:
                print(row)  # Print each row of data from the sheet
        else:
            print(f"No data found in sheet")

        # if not success:
        #     await interaction.response.send_message(f"There was an error retrieving the GDoc sheet with the ID provided: {sheet_id}",
        #                                             ephemeral=False)

    await interaction.response.send_message(f"The Google Sheet ID has been updated to reference id: {sheet}",
                                            ephemeral=False)

    # TODO Move these to a startup command that only can be run after initial configuration
    bounty_task = Bounties(bot=bot, gdoc=gdoc, state=state)
    daily_task = Dailies(bot=bot, gdoc=gdoc, state=state)

"https://discord.com/oauth2/authorize?client_id=1351530292061536297&scope=bot+applications.commands&permissions=2147691584"
# Sync the commands (for a specific guild)
async def sync_commands():
    try:
        # This line will sync the commands for a specific guild by passing guild_id
        await bot.tree.sync()  # Syncing the commands for this guild
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


# Run bot
bot.run(state.discord_token)
