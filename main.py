import asyncio
import datetime
import discord
import yaml
from discord.ext import commands, tasks
from discord import app_commands
import os
import logging
from gdoc import GDoc
import pandas
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


@bot.event
async def on_ready():
    await bot.tree.sync()
    bounty_channel = bot.get_channel(state.bounty_channel_id)
    daily_channel = bot.get_channel(state.daily_channel_id)
    staff_channel = bot.get_channel(state.staff_channel_id)

    if not bounty_channel:
        logging.error("Could not find Bounty Channel")

    if not daily_channel:
        logging.error("Could not find Daily Channel")

    if not staff_channel:
        logging.error("Could not find Staff Channel")


# Run bot
bot.run(state.discord_token)
