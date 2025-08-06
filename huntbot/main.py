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
from huntbot.cogs.StarBoard import StarBoardCog
from huntbot.cogs.Score import ScoreCog
from huntbot.cogs.Countdown import CountdownCog
from huntbot.State import State
import os

# Set up the logger
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    logger.debug("No Discord API token found.")
    exit()

logger.info("Discord API token found successfully.")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

gdoc = GDoc()
hunt_bot = HuntBot()
state = State()


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


@bot.tree.command(name="beep")
async def beep(interaction: discord.Interaction):
    logger.info("/beep command ran")
    await interaction.response.send_message("Boop")


# Bounty command with automatic 48hr end

# Bounty command with configurable time limit (in minutes), default 48 hours
@bot.tree.command(name="bounty", description="Create a new bounty")
@app_commands.describe(
    name_of_item="Name of the item for the bounty",
    reward_amount="Reward amount for completing the bounty",
    time_limit="Time limit for the bounty in minutes (optional, default 2880 = 48 hours)"
)
async def bounty(
    interaction: discord.Interaction,
    name_of_item: str,
    reward_amount: str,
    time_limit: str = None
):
    if interaction.channel.id != hunt_bot.command_channel_id:
        return

    # Default to 48 hours (2880 minutes) if not set
    if time_limit is None or time_limit == "":
        minutes = 2880
    else:
        if not time_limit.isdigit():
            await interaction.response.send_message(
                "Please use only numbers for the time limit.", ephemeral=True
            )
            return
        minutes = int(time_limit)
        if minutes <= 0:
            minutes = 2880


    # Allow K (thousand) and M (million) suffixes in reward_amount
    reward_str = reward_amount.strip().lower()
    multiplier = 1
    if reward_str.endswith('k'):
        multiplier = 1_000
        reward_str = reward_str[:-1]
    elif reward_str.endswith('m'):
        multiplier = 1_000_000
        reward_str = reward_str[:-1]
    try:
        reward_val = float(reward_str) * multiplier
        if reward_val < 0:
            await interaction.response.send_message(
                "Reward amount cannot be negative.", ephemeral=True
            )
            return
    except ValueError:
        await interaction.response.send_message(
            "Reward amount must be a number (optionally with 'K' for thousand or 'M' for million).", ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"Bounty created!\nItem: {name_of_item}\nReward: {reward_amount}\nTime Limit: {minutes} minutes ({minutes/60:.1f} hours)"
    )


    # Store a reference to the end_bounty function for early closure
    if not hasattr(bot, 'active_bounties'):
        bot.active_bounties = {}

    bounty_key = name_of_item.strip().lower()

    # Store bounty details for later use
    bot.active_bounties[bounty_key] = {
        'handle': None,  # will be set after task creation
        'reward_amount': reward_amount
    }

    async def end_bounty():
        await interaction.followup.send(f"The bounty for '{name_of_item}' has ended after {minutes} minutes.")
        bot.active_bounties.pop(bounty_key, None)

    # Store the cancel handle so we can close early
    handle = bot.loop.create_task(_bounty_timer(end_bounty, minutes))
    bot.active_bounties[bounty_key]['handle'] = handle


# Command to list all active bounties (placed next to bounty command)
@bot.tree.command(name="listbounties", description="List all active bounties.")
async def listbounties(interaction: discord.Interaction):
    if interaction.channel.id != hunt_bot.command_channel_id:
        return
    if not hasattr(bot, 'active_bounties') or not bot.active_bounties:
        await interaction.response.send_message("There are no active bounties.", ephemeral=True)
        return
    bounty_msgs = []
    for bounty_key, info in bot.active_bounties.items():
        bounty_msgs.append(f"Bounty Item: {bounty_key} | Value: {info['reward_amount']}")
    msg = "**Active Bounties:**\n" + "\n".join(bounty_msgs)
    await interaction.response.send_message(msg, ephemeral=True)



# Command to close a bounty early and select a user as the claimer
@bot.tree.command(name="closebounty", description="Close an active bounty early by item name and select a user as the claimer.")
@app_commands.describe(
    bounty_item="The item name of the bounty to close early.",
    user="The user who claimed the bounty."
)
async def closebounty(interaction: discord.Interaction, bounty_item: str, user: discord.Member):
    if interaction.channel.id != hunt_bot.command_channel_id:
        return
    if not hasattr(bot, 'active_bounties') or not bot.active_bounties:
        await interaction.response.send_message("There are no active bounties to close.", ephemeral=True)
        return
    bounty_key = bounty_item.strip().lower()
    info = bot.active_bounties.get(bounty_key)
    if not info:
        await interaction.response.send_message("No active bounty found with that item name.", ephemeral=True)
        return
    handle = info['handle']
    handle.cancel()
    value = info['reward_amount']
    bot.active_bounties.pop(bounty_key, None)
    await interaction.response.send_message(f"Bounty for '{bounty_item}' has been claimed by {user.mention} for {value}!")


# Helper for bounty timer
import asyncio
async def _bounty_timer(callback, minutes):
    await asyncio.sleep(minutes * 60)
    await callback()


@bot.tree.command(name="start-hunt", description="Starts the Hunt Bot on the pre-configured date and time")
async def start(interaction: discord.Interaction):
    if not any(role.name.lower() == "admin" for role in interaction.user.roles):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
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

    # There is data, so build the table map from the data, so we can query it
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
    else:
        try:
            logger.info("Hunt Bot is configured, starting Star Board Cog")
            await bot.add_cog(StarBoardCog(discord_bot=bot, hunt_bot=hunt_bot))

            # logger.info("Hunt Bot is configured, starting Countdown Cog")
            # await bot.add_cog(CountdownCog(bot, hunt_bot))
        except Exception as e:
            logger.error(e)
    logger.info("Hunt Bot configured successfully")
    try:
        await state.update_state(bot=True, **hunt_bot.config_map)
    except Exception as e:
        logger.error("Exception encountered when updating state during startup when updating initial state", exc_info=e)

    await interaction.followup.send(
        f"Hunt Bot successfully configured! The hunt will start on {hunt_bot.start_datetime}")

    if not check_start_time.is_running():
        logger.info("Starting check_start_time task")
        # Start the periodic check if not already running
        check_start_time.start()


@bot.tree.command(name="sheet", description="Updates the GDoc sheet ID that the Hunt Bot references")
@app_commands.describe(sheet_id="The GDoc sheet ID", sheet_name="The name of the sheet in the GDoc",
                       config_table="Name of the discord configuration table in the sheet")
async def sheet(interaction: discord.Interaction, sheet_id: str, sheet_name: str = "BotConfig",
                config_table: str = "Discord Conf"):
    if not any(role.name.lower() == "admin" for role in interaction.user.roles):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    logger.info(f"/sheet command ran with args: sheet_name={sheet_name} sheet_id={sheet_id}")

    gdoc.set_sheet_id(sheet_id=sheet_id)
    hunt_bot.set_sheet_name(sheet_name=sheet_name)
    hunt_bot.set_config_table_name(table_name=config_table)
    await interaction.response.send_message("Sheet ID and Name set successfully")
    logger.info(f"The GDoc ID has been updated to reference id: {sheet_id}, and sheet name: {sheet_name}")


@bot.tree.command(name="passwords", description="Display the current hunt passwords.")
async def passwords(interaction: discord.Interaction):
    # Accessing HuntBot attributes
    bounty = hunt_bot.bounty_password
    daily = hunt_bot.daily_password
    master = hunt_bot.master_password

    # Format response
    response = (
        "**===== CURRENT PASSWORDS =====**\n\n"
        f"**MASTER:** {master}\n"
        f"**DAILY:** {daily}\n"
        f"**BOUNTY:** {bounty}"
    )

    await interaction.response.send_message(response, ephemeral=True)


@bot.tree.command(name="state", description="Show the current state file contents")
async def show_state(interaction: discord.Interaction):
    if interaction.channel.id != hunt_bot.admin_channel_id:
        return
    logger.info("/state command ran")

    if not state.state_data:
        await interaction.response.send_message("State is currently empty.", ephemeral=True)
        return

    import io
    import yaml

    yaml_text = yaml.safe_dump(state.state_data, sort_keys=False)
    fp = io.BytesIO(yaml_text.encode("utf-8"))

    await interaction.response.send_message(
        content="📄 Full state file attached (too long to display):",
        file=discord.File(fp, filename="state.yaml")
    )


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
        memory = load_random_memory("conf/memories.yaml")
        # await channel.send(memory)
        await channel.send(memory)
    except Exception as e:
        logger.error(e)
        logger.error("Error posting memory during on_ready event")

    await sync_commands(test=True)

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


async def main():
    try:
        await state.load_state()
        logger.info("State loaded successfully.")
    except Exception as e:
        logger.error("Exception encountered when updating state during startup when loading existing state", exc_info=e)

    await bot.start(TOKEN)


def run():
    asyncio.run(main())
