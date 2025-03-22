import asyncio
import datetime
import discord
import yaml
from discord.ext import commands, tasks
from discord import app_commands
import os
import logging
from gdoc import GDoc


# Setup shit
logging.basicConfig(format="{asctime} - {levelname} - {message}", style="{", datefmt="%Y-%m-%d %H:%M", )
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Load config
with open('conf.yaml', 'r') as f:
    data = yaml.safe_load(f)

# Set Constants
# TODO Configure token ENV on launch
TOKEN = "MTM1MTUzMDI5MjA2MTUzNjI5Nw.G8gCi1.2rgy-ruhqlyBoI7bjYToNa79e2eT59Iw-mvMJM"
# TOKEN = os.getenv("TOKEN")
BOUNTY_CHANNEL_ID = data.get("BOUNTY_CHANNEL_ID")
DAILY_CHANNEL_ID = data.get("DAILY_CHANNEL_ID")
STAFF_CHANNEL_ID = data.get("STAFF_CHANNEL_ID")
START_TIME = "16:00"

gdoc = GDoc()


@bot.tree.command(name="start", description="Starts the hunt bot on the specified date")
@app_commands.describe(date="The DD/MM/YY format of the hunt start date")
async def start(interaction: discord.Interaction, date: str):
    # TODO Fix the output format of this shit pile

    if interaction.channel.id != STAFF_CHANNEL_ID:
        await interaction.response.send_message("Silly goon. You can't run that command in this channel.",
                                                ephemeral=False)
        return

    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(f"=== The Hunt Bot is scheduled to start running on {date} at {START_TIME} GMT ===")

    serve_bounty.start()
    serve_daily.start()

@tasks.loop(hours=6)
async def serve_bounty():
    channel = bot.get_channel(BOUNTY_CHANNEL_ID)
    await bot.wait_until_ready()
    while not bot.is_closed():
        for bounty in gdoc.bounties_list:
            await channel.send("=== BOUNTY SERVED ===")
            await channel.send(bounty)
            await asyncio.sleep(5)


@tasks.loop(hours=24)
async def serve_daily():
    channel = bot.get_channel(DAILY_CHANNEL_ID)
    await bot.wait_until_ready()
    while not bot.is_closed():
        for daily in gdoc.dailies_list:
            await channel.send("=== DAILY SERVED ===")
            await channel.send(daily)
            await asyncio.sleep(7)


@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync commands with Discord
    bounty_channel = bot.get_channel(BOUNTY_CHANNEL_ID)
    daily_channel = bot.get_channel(DAILY_CHANNEL_ID)
    staff_channel = bot.get_channel(STAFF_CHANNEL_ID)

    if not bounty_channel:
        logging.error("Could not find Bounty Channel")

    if not daily_channel:
        logging.error("Could not find Daily Channel")

    if not staff_channel:
        logging.error("Could not find Staff Channel")


# Run bot
bot.run(TOKEN)
