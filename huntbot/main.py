#!/usr/bin/env python3
import asyncio
import discord
from discord.ext import commands, tasks
import logging
from huntbot.GDoc import GDoc
from huntbot.HuntBot import HuntBot
from huntbot.cogs.Bounties import BountiesCog
from huntbot.cogs.Dailies import DailiesCog
from huntbot.cogs.Score import ScoreCog
from huntbot.cogs.Countdown import CountdownCog
from huntbot.cogs.Memories import MemoriesCog
from huntbot.State import State
import os
from huntbot.commands.bounty_commands import register_bounty_commands, ItemBounties
from huntbot.commands.main_commands import register_main_commands
from huntbot.commands.dailies_command import register_daily_commands
from huntbot.commands.bounties_command import register_bounties_commands

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Capture all logs

# Common formatter
formatter = logging.Formatter(
    '[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Debug handler (everything goes here)
debug_handler = logging.FileHandler('debug.log')
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(formatter)

# Info handler (INFO and up)
info_handler = logging.FileHandler('app.log')
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(formatter)

# Add handlers to root logger
logger.addHandler(debug_handler)
logger.addHandler(info_handler)

# Optional: Get logger for current module
logger = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    logger.error("[Main Task Loop] No Discord API token found.")
    exit()

logger.info("[Main Task Loop] Discord API token found successfully.")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

gdoc = GDoc()
hunt_bot = HuntBot()
state = State()
item_bounties = ItemBounties(hunt_bot)

@tasks.loop(seconds=5)
async def check_start_time():
    logger.debug("[Main Task Loop] Checking start time task loop....")

    try:
        # Get updated gdoc data rate is 300 reads /per minute
        logger.info("[Main Task Loop] Retrieving GDoc data....")
        hunt_bot.set_sheet_data(data=gdoc.get_data_from_sheet(sheet_name=hunt_bot.sheet_name))
    except Exception as e:
        logger.error(e)
        logger.error("[Main Task Loop] Failed to retrieve GDoc data")

    logger.debug("[Main Task Loop] Checking if Hunt Bot has been configured...")

    channel = bot.get_channel(hunt_bot.announcements_channel_id)

    if not hunt_bot.started:
        logger.debug("[Main Task Loop] The Hunt has not started yet... checking start time...")
        # Check if we need to start the hunt or not
        hunt_bot.check_start()
        if hunt_bot.started:
            logger.info("[Main Task Loop] The Hunt has begun!")
            if channel:
                await channel.send(f"https://imgur.com/Of4zPcO \n@everyone the 14th Flux Hunt has officially begun!\n"
                                   f"The password is: {hunt_bot.master_password}")

            # If we made it this far then we are ready to start loading the cogs
            # Start bounties plugin
            try:
                logger.info("[Main Task Loop] Loading Bounties Cog...")
                await bot.add_cog(BountiesCog(bot=bot, hunt_bot=hunt_bot))
                logger.info("[Main Task Loop] Bounties Cog loaded successfully")

                logger.info("[Main Task Loop] Loading Dailies Cog...")
                await bot.add_cog(DailiesCog(bot=bot, hunt_bot=hunt_bot))
                logger.info("[Main Task Loop] Dailies Cog loaded successfully")

                logger.info("[Main Task Loop] Loading Score Cog...")
                await bot.add_cog(ScoreCog(discord_bot=bot, hunt_bot=hunt_bot))
                logger.info("[Main Task Loop] Score Cog loaded successfully")

                logger.info("[Main Task Loop] Loading Memories Cog...")
                memories_cog = MemoriesCog(discord_bot=bot, hunt_bot=hunt_bot)
                await bot.add_cog(memories_cog)
                await memories_cog.cog_load()
                logger.info("[Main Task Loop] Memories Cog loaded successfully")

            except Exception as e:
                logger.error(e)
                logger.error("[Main Task Loop] Error Loading Cogs")
                await channel.send(f"Error loading Cogs.")
                return
        else:
            logger.info("[Main Task Loop] Waiting for start time...")
    else:
                # Check if we need to end the hunt
        logger.debug("[Main Task Loop] Checking Hunt End Date and Time...")
        hunt_bot.check_end()
        if hunt_bot.ended:
            logger.info("[Main Task Loop] The Hunt has ended!")
            await channel.send(
                f"https://imgur.com/qdtYicb \n@everyone The 14th Hunt has officially concluded...results coming soon!")
            check_start_time.stop()


bot.check_start_time = check_start_time


async def sync_commands(test: bool = False):
    try:
        # Optional: force sync for a specific guild
        if test:
            guild = discord.Object(id=699971574689955850)
            await bot.tree.sync(guild=guild)
            logger.info("[Main Task Loop] Slash commands have been synced to guild.")

        # Also sync globally (optional but safe to include)
        await bot.tree.sync()
        logger.info("[Main Task Loop] Global slash commands have been successfully refreshed!")
    except Exception as e:
        logger.error(f"[Main Task Loop] Error refreshing commands: {e}")


async def list_commands():
    # List all global commands
    logger.info("[Main Task Loop] Listing all registered commands:")
    for command in bot.tree.get_commands():
        logger.info(f"[Main Task Loop] Command Name: {command.name}, Description: {command.description}")


@bot.event
async def on_ready():
    logger.info("[Main Task Loop] Loading Assets...")
    with open("assets/franken-thurgo.png", "rb") as avatar_file:
        # Update the bot's avatar
        image = avatar_file.read()
        await bot.user.edit(avatar=image)

    logger.info("[Main Task Loop] Assets Loaded")

    register_main_commands(bot.tree, gdoc, hunt_bot, state, bot)
    register_bounties_commands(bot.tree, bot)
    register_daily_commands(bot.tree, bot)
    register_bounty_commands(bot.tree, item_bounties)

    # Sync and List all commands
    await sync_commands(test=True)
    await list_commands()

    logger.info(f"[Main Task Loop] Logged in as {bot.user}")


async def main():
    try:
        await state.load_state()
        logger.info("[Main Task Loop] State loaded successfully.")
    except Exception as e:
        logger.error("[Main Task Loop] Exception encountered when updating state during startup when loading existing state", exc_info=e)

    await bot.start(TOKEN)


def run():
    asyncio.run(main())
