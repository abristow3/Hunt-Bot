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

    serve_bounty.start()
    serve_daily.start()


@tasks.loop(hours=state.bounty_tick)
async def serve_bounty():
    channel = bot.get_channel(state.bounty_channel_id)
    await bot.wait_until_ready()
    while not bot.is_closed():
        for bounty in gdoc.bounties_list:
            await channel.send("=== BOUNTY SERVED ===")
            await channel.send(bounty)
            await asyncio.sleep(5)


@tasks.loop(hours=24)
async def serve_daily():
    channel = bot.get_channel(state.daily_channel_id)
    await bot.wait_until_ready()
    while not bot.is_closed():
        for daily in gdoc.dailies_list:
            await channel.send("=== DAILY SERVED ===")
            await channel.send(daily)
            await asyncio.sleep(7)


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
