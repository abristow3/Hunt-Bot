#!/usr/bin/env python3
import asyncio
import re
import yaml
import discord
import random
from discord.ext import commands, tasks
from discord import app_commands
import logging
from huntbot.GDoc import GDoc
from huntbot.HuntBot import HuntBot
from huntbot.cogs.Bounties import BountiesCog
from huntbot.cogs.Dailies import DailiesCog
from huntbot.cogs.Score import ScoreCog
from huntbot.cogs.Countdown import CountdownCog
from huntbot.State import State
import os
from huntbot.commands.bounty_commands import register_bounty_commands, ItemBounties
from huntbot.commands.main_commands import register_main_commands
from huntbot.commands.dailies_command import register_daily_commands
from huntbot.commands.bounties_command import register_bounties_commands

# Set up the logger
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    logger.error("No Discord API token found.")
    exit()

logger.info("Discord API token found successfully.")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

gdoc = GDoc()
hunt_bot = HuntBot()
state = State()
item_bounties = ItemBounties(hunt_bot)


def load_random_memory(yaml_file_path):
    with open(yaml_file_path, 'r') as file:
        data = yaml.safe_load(file)

    memories = data.get('memories', [])

    if not memories:
        return "No memories found in the file."

    memory = random.choice(memories)

    # Try to extract the player name from the end of the memory string
    match = re.search(r'\s-\s(.+)$', memory)
    if match:
        player = match.group(1).strip()
        memory_text = memory[:match.start()].strip()
    else:
        player = "Unknown"
        memory_text = memory.strip()

    return f'"{memory_text}"\n\n— {player}'


@tasks.loop(seconds=5)
async def check_start_time():
    # global countdown
    logger.info("Checking start time task loop....")

    try:
        # Get updated gdoc data rate is 300 reads /per minute
        logger.info("Retrieving GDoc data....")
        hunt_bot.set_sheet_data(data=gdoc.get_data_from_sheet(sheet_name=hunt_bot.sheet_name))
    except Exception as e:
        logger.error(e)
        logger.error("Failed to retrieve GDoc data")

    logger.info("Checking if Hunt Bot has been configured...")

    channel = bot.get_channel(hunt_bot.announcements_channel_id)

    if not hunt_bot.started:
        logger.info("The Hunt has not started yet... checking start time...")
        # Check if we need to start the hunt or not
        hunt_bot.check_start()
        if hunt_bot.started:
            logger.info("The Hunt has begun!")
            if channel:
                await channel.send(f"https://imgur.com/Of4zPcO \n@everyone the 14th Flux Hunt has officially begun!\n"
                                   f"The password is: {hunt_bot.master_password}")

            # Check if we need to end the hunt
            logger.info("Checking Hunt End Date and Time...")
            hunt_bot.check_end()
            if hunt_bot.ended:
                logger.info("The Hunt has ended!")
                await channel.send(
                    f"https://imgur.com/qdtYicb \n@everyone The 14th Hunt has officially concluded...results coming soon!")
                return

            # If we made it this far then we are ready to start loading the cogs
            # Start bounties plugin
            try:
                logger.info("Loading Bounties Cog...")
                await bot.add_cog(BountiesCog(bot=bot, hunt_bot=hunt_bot))
                logger.info("Bounties Cog loaded successfully")

                logger.info("Loading Dailies Cog...")
                await bot.add_cog(DailiesCog(bot=bot, hunt_bot=hunt_bot))
                logger.info("Dailies Cog loaded successfully")

                logger.info("Loading Score Cog...")
                await bot.add_cog(ScoreCog(discord_bot=bot, hunt_bot=hunt_bot))
                logger.info("Score Cog loaded successfully")
            except Exception as e:
                logger.error(e)
                logger.error("Error Loading Cogs")
                await channel.send(f"Error loading Cogs.")
                return
        else:
            logger.info("Waiting for start time...")


async def sync_commands(test: bool = False):
    try:
        # Optional: force sync for a specific guild
        if test:
            guild = discord.Object(id=1351532522663837757)
            await bot.tree.sync(guild=guild)
            logger.info("Slash commands have been synced to guild.")

        # Also sync globally (optional but safe to include)
        await bot.tree.sync()
        logger.info("Global slash commands have been successfully refreshed!")
    except Exception as e:
        logger.error(f"Error refreshing commands: {e}")


async def list_commands():
    # List all global commands
    logger.info("Listing all registered commands:")
    for command in bot.tree.get_commands():
        logger.info(f"Command Name: {command.name}, Description: {command.description}")


@bot.event
async def on_ready():
    logger.info("Loading Assets...")
    with open("assets/franken-thurgo.png", "rb") as avatar_file:
        # Update the bot's avatar
        image = avatar_file.read()
        await bot.user.edit(avatar=image)

    logger.info("Assets Loaded")

    try:
        channel = bot.get_channel(hunt_bot.general_channel_id)

        if hunt_bot.first_join:
            await channel.send("Ah shit, it's about that time 👀")
        else:
            memory = load_random_memory("conf/memories.yaml")
            # await channel.send(memory)
            await channel.send(memory)
    except Exception as e:
        logger.error(e)
        logger.error("Error posting memory during on_ready event")

    register_bounty_commands(bot.tree, item_bounties)
    register_main_commands(bot.tree, gdoc, hunt_bot, state, bot)
    register_bounties_commands(bot.tree, bot)
    register_daily_commands(bot.tree, bot)

    # Sync and List all commands
    await sync_commands(test=True)
    await list_commands()

    logger.info(f"Logged in as {bot.user}")


async def main():
    try:
        await state.load_state()
        logger.info("State loaded successfully.")
    except Exception as e:
        logger.error("Exception encountered when updating state during startup when loading existing state", exc_info=e)

    await bot.start(TOKEN)


def run():
    asyncio.run(main())
