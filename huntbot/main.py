#!/usr/bin/env python3
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
from huntbot.cogs.StarBoard import StarBoardCog
from huntbot.cogs.Score import ScoreCog
from huntbot.cogs.Countdown import CountdownCog
import os

# Set up the logger
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    logger.debug("No Discord API token found.")
    exit()

logger.info("Discord API token found succesfully.")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

gdoc = GDoc()
hunt_bot = HuntBot()


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

    # Get updated gdoc data rate is 300 reads /per minute
    logger.info("Retrieving GDoc data....")
    try:
        hunt_bot.set_sheet_data(data=gdoc.get_data_from_sheet(sheet_name=hunt_bot.sheet_name))
    except Exception as e:
        logger.error(e)
        logger.error("Failed to retrieve GDoc data")

    logger.info("Checking if Huntbot has been configured...")
    # Initialize Countdown only once when configured
    if hunt_bot.configured:
        logger.info("Hunt Bot is configured, starting Countdown Cog")
        await bot.add_cog(CountdownCog(bot, hunt_bot))

        logger.info("Hunt Bot is configured, starting Star Board Cog")
        await bot.add_cog(StarBoardCog(discord_bot=bot, hunt_bot=hunt_bot))

    channel = bot.get_channel(hunt_bot.announcements_channel_id)

    if not hunt_bot.started:
        logger.info("The Hunt has not started yet... checking start time...")
        # Check if we need to start the hunt or not
        hunt_bot.check_start()
        if hunt_bot.started:
            logger.info("The Hunt has begun!")
            if channel:
                await channel.send(f"@everyone the 14th Flux Hunt has officially begun!\n"
                                   f"The password is: {hunt_bot.master_password}")

            # Check if we need to end the hunt
            logger.info("Checking Hunt End Date and Time...")
            hunt_bot.check_end()
            if hunt_bot.ended:
                logger.info("The Hunt has ended!")
                await channel.send(f"@everyone The 14th Hunt has officially concluded...results coming soon!")
                return

            # If we made it this far then we are ready to start loading the cogs
            # Start bounties plugin
            try:
                logger.info("Loading Bounties Cog...")
                await bot.add_cog(BountiesCog(bot=bot, hunt_bot=hunt_bot))
                logger.info("Bounties Cog loaded succesfully")

                logger.info("Loading Dailies Cog...")
                await bot.add_cog(DailiesCog(discod_bot=bot, hunt_bot=hunt_bot))
                logger.info("Dailies Cog loaded succesfully")

                logger.info("Loading Score Cog...")
                await bot.add_cog(ScoreCog(discord_bot=bot, hunt_bot=hunt_bot))
                logger.info("Score Cog loaded succesfully")
            except Exception as e:
                logger.error(e)
                logger.error("Error Loading Cogs")
                await channel.send(f"Error loading Cogs.")
                return
        else:
            logger.info("Waiting for start time...")


@bot.tree.command(name="beep")
async def beep(interaction: discord.Interaction):
    if interaction.channel.id != hunt_bot.command_channel_id:
        return
    logger.info("/beep command ran")
    await interaction.response.send_message("Boop")


@bot.tree.command(name="start-hunt", description="Starts the Hunt Bot on the pre-configured date and time")
async def start(interaction: discord.Interaction):
    if interaction.channel.id != hunt_bot.command_channel_id:
        return

    await interaction.response.defer()

    logger.info(f"/start-hunt command ran")

    # Check sheet ID has been populated
    if gdoc.sheet_id == "":
        logger.info("Sheet ID not set")
        await interaction.followup.send("No GDoc sheet ID set. Use the command '/sheet' to set one.")
        return

    # Check sheet name has been populated
    if hunt_bot.sheet_name == "":
        logger.info("Sheet Name not set")
        await interaction.followup.send("No GDoc sheet name set. Use the command '/sheet' to set one.")
        return

    # Import the sheet data
    try:
        hunt_bot.set_sheet_data(data=gdoc.get_data_from_sheet(sheet_name=hunt_bot.sheet_name))
    except Exception as e:
        logger.error(e)
        logger.error("Error loading Sheet Data from GDoc")

    # If no data imported
    if hunt_bot.sheet_data.empty:
        logger.error("Error retrieving Hunt Bot configuration.")
        await interaction.followup.send("Error retrieving Hunt Bot configuration from GDoc. Check if the "
                                                "sheet ID and sheet name are correct.")
        return

    # There is data, so build the table map from the data so we can query it
    hunt_bot.build_table_map()

    # Check table map was created
    if not hunt_bot.table_map:
        logger.error("Error building table map for GDoc")
        await interaction.followup.send("Error building sheet table map.")
        return

    # Get the HuntBot Configuration variables
    config_df = hunt_bot.pull_table_data(table_name=hunt_bot.config_table_name)

    # Check config data was found
    if config_df.empty:
        logger.error("Error retrieving configuration data from table")
        await interaction.followup.send("Error retrieving config data.")
        return

    hunt_bot.load_config(df=config_df)

    # Check config data loaded
    if not hunt_bot.configured:
        logger.error("Hunt Bot Configuration failed to load")
        await interaction.followup.send("Error setting config data.")
        return

    logger.info("Hunt Bot configured succesfully")

    await interaction.followup.send(
        f"Hunt Bot successfully configured! The hunt will start on {hunt_bot.start_datetime}")

    if not check_start_time.is_running():
        logger.info("Starting check_start_time task")
        # Start the periodic check if not already running
        check_start_time.start()


@bot.tree.command(name="sheet", description="Updates the GDoc sheet ID that the Hunt Bot refernces")
@app_commands.describe(sheet_id="The GDoc sheet ID", sheet_name="The name of the sheet in the GDoc",
                       config_table="Name of the discord configuration table in the sheet")
async def sheet(interaction: discord.Interaction, sheet_id: str, sheet_name: str = "BotConfig",
                config_table: str = "Discord Conf"):
    if interaction.channel.id != hunt_bot.command_channel_id:
        return

    logger.info(f"/sheet command ran with args: sheet_name={sheet_name} sheet_id={sheet_id}")

    gdoc.set_sheet_id(sheet_id=sheet_id)
    hunt_bot.set_sheet_name(sheet_name=sheet_name)
    hunt_bot.set_config_table_name(table_name=config_table)
    await interaction.response.send_message("Sheet ID and Name set succesfully")
    logger.info(f"The GDoc ID has been updated to reference id: {sheet_id}, and sheet name: {sheet_name}")


async def sync_commands():
    try:
        await bot.tree.sync()
        logger.info("Slash commands have been successfully refreshed!")
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
    with open("assets/franken-thrugo.png", "rb") as avatar_file:
        # Update the bot's avatar
        image = avatar_file.read()
        await bot.user.edit(avatar=image)

    logger.info("Assets Loaded")

    try:
        channel = bot.get_channel(hunt_bot.general_channel_id)
        memory = load_random_memory("conf/memories.yaml")
        # await channel.send(memory)
        await channel.send(f"I'M ALIVEEEEE!!!!!!! FEELS FRANKEN-THURGO MAN\n\n{memory}")
    except Exception as e:
        logger.error(e)
        logger.error("Error posting memory during on_ready event")

    await sync_commands()

    # List all commands
    await list_commands()

    logger.info(f"Logged in as {bot.user}")

    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.name == hunt_bot.command_channel_name:
                hunt_bot.command_channel_id = channel.id
                return

    if hunt_bot.command_channel_id == "":
        logger.error("NO COMMAND CHANNEL FOUND")


def run():
    # Run bot
    bot.run(TOKEN)
    # bot.run(hunt_bot.discord_token)
