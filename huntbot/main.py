#!/usr/bin/env python3
import discord
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

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("NO TOKEN CONFIGURED")
    exit()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

gdoc = GDoc()
hunt_bot = HuntBot()


@tasks.loop(seconds=5)
async def check_start_time():
    # global countdown

    # Get updated gdoc data rate is 300 reads /per minute
    hunt_bot.set_sheet_data(data=gdoc.get_data_from_sheet(sheet_name=hunt_bot.sheet_name))

    # Initialize Countdown only once when configured
    if hunt_bot.configured:
        await bot.add_cog(CountdownCog(bot, hunt_bot))

    channel = bot.get_channel(hunt_bot.announcements_channel_id)

    if hunt_bot.configured:
        # Start Starboard plugin
        await bot.add_cog(StarBoardCog(discord_bot=bot, hunt_bot=hunt_bot))

    if not hunt_bot.started:
        # Check if we need to start the hunt or not
        hunt_bot.check_start()
        if hunt_bot.started:

            if channel:
                await channel.send(f"@everyone the 13th Flux Hunt has officially begun!\n"
                                   f"The password is: {hunt_bot.master_password}")

            # Check if we need to end the hunt
            hunt_bot.check_end()
            if hunt_bot.ended:
                await channel.send(f"@everyone The 13th Hunt has officially concluded...results coming soon!")
                return

            # If we made it this far then we are ready to start loading the cogs
            # Start bounties plugin
            try:
                await bot.add_cog(BountiesCog(bot=bot, hunt_bot=hunt_bot))
            except Exception as e:
                await channel.send(f"Error loading Bounties Cog: {e}")
                return

            try:
                await bot.add_cog(DailiesCog(discod_bot=bot, hunt_bot=hunt_bot))
            except Exception as e:
                await channel.send(f"Error loading Dailies Cog: {e}")
                return

            await bot.add_cog(ScoreCog(discord_bot=bot, hunt_bot=hunt_bot))

        else:
            print("Waiting for the start time...")


@bot.tree.command(name="beep")
async def beep(interaction: discord.Interaction):
    if interaction.channel.id != hunt_bot.command_channel_id:
        return
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

    await interaction.response.send_message(
        f"Bounty created!\nItem: {name_of_item}\nReward: {reward_amount}\nTime Limit: {minutes} minutes ({minutes/60:.1f} hours)"
    )

    async def end_bounty():
        await interaction.followup.send(f"The bounty for '{name_of_item}' has ended after {minutes} minutes.")

    bot.loop.create_task(_bounty_timer(end_bounty, minutes))


# Helper for bounty timer
import asyncio
async def _bounty_timer(callback, minutes):
    await asyncio.sleep(minutes * 60)
    await callback()


@bot.tree.command(name="start-hunt", description="Starts the Hunt Bot on the pre-configured date and time")
async def start(interaction: discord.Interaction):
    if interaction.channel.id != hunt_bot.command_channel_id:
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
    config_df = hunt_bot.pull_table_data(table_name=hunt_bot.config_table_name)

    # Check config data was found
    if config_df.empty:
        await interaction.response.send_message("Error retrieving config data.")
        return

    hunt_bot.load_config(df=config_df)

    # Check config data loaded
    if not hunt_bot.configured:
        await interaction.response.send_message("Error setting config data.")
        return

    await interaction.response.send_message(
        f"Hunt Bot successfully configured! The hunt will start on {hunt_bot.start_datetime}")

    if not check_start_time.is_running():
        # Start the periodic check if not already running
        check_start_time.start()


@bot.tree.command(name="sheet", description="Updates the GDoc sheet ID that the Hunt Bot refernces")
@app_commands.describe(sheet_id="The GDoc sheet ID", sheet_name="The name of the sheet in the GDoc",
                       config_table="Name of the discord configuration table in the sheet")
async def sheet(interaction: discord.Interaction, sheet_id: str, sheet_name: str = "BotConfig",
                config_table: str = "Discord Conf"):
    if interaction.channel.id != hunt_bot.command_channel_id:
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
    with open("assets/franken-thrugo.png", "rb") as avatar_file:
        # Update the bot's avatar
        image = avatar_file.read()
        await bot.user.edit(avatar=image)

    try:
        channel = bot.get_channel(699971574689955853)
        await channel.send("I'M ALIVEEEEE!!!!!!!\n"
                           "FEELS FRANKEN-THURGO MAN")
    except Exception as e:
        pass

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


def run():
    # Run bot
    bot.run(TOKEN)
    # bot.run(hunt_bot.discord_token)
