import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
from GDoc import GDoc
from HuntBot import HuntBot
from Plugins.Bounties.Bounties import Bounties
from Plugins.Dailies.Dailies import Dailies
from Plugins.Countdown.Countdown import Countdown
import os


'''
TODO LIST:
- Automate Quick time event (QTE) (anything that doesnt happen on the 6-hour schedule)
    - on QTE entries, can have field with GMT time for the GMT time QTE should be published
    - Also have Channel ID for where to publish the message
- Automate Hunt score update messages to publish 

If drop has specific emoji, paste in star-board, if emoji removed, remove it
    white list by drop screenshot channels for both teams (only certain users can emoji ni these channels)
'''
TOKEN = os.getenv("DISCORD_TOKEN")


# Setup shit
logging.basicConfig(format="{asctime} - {levelname} - {message}", style="{", datefmt="%Y-%m-%d %H:%M", )
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

gdoc = GDoc()
hunt_bot = HuntBot()
countdown = None


@tasks.loop(seconds=5)
async def check_start_time():
    global countdown
    # Initialize Countdown only once when configured
    if hunt_bot.configured and countdown is None:
        countdown = Countdown(hunt_bot=hunt_bot, discord_bot=bot)
    if not countdown.countdown_task_started:
        countdown.start_countdown()

    if not hunt_bot.started:
        # Check if we need to start the hunt or not
        hunt_bot.check_start()
        if hunt_bot.started:
            channel = bot.get_channel(hunt_bot.command_channel_id)

            if channel:
                await channel.send("Start time reached. Starting the hunt!")

            print("Start time reached. Starting the hunt!")
            # If we made it this far then we are ready to start loading the plugins
            # Start bounties plugin
            bounties = Bounties(discord_bot=bot, hunt_bot=hunt_bot)

            # Check plugin loaded
            if not bounties.configured:
                await channel.send("Error loading Bounties plugin.")
                return

            # Start Dailies plugin
            dailies = Dailies(discord_bot=bot, hunt_bot=hunt_bot)

            # Check plugin loaded
            if not dailies.configured:
                await channel.send("Error loading Dailies plugin.")
                return

        else:
            print("Waiting for the start time...")


@bot.tree.command(name="beep")
async def beep(interaction: discord.Interaction):
    await interaction.response.send_message("Boop")


@bot.tree.command(name="start-hunt", description="Starts the Hunt Bot on the pre-configured date and time")
async def start(interaction: discord.Interaction):
    if interaction.channel.id != hunt_bot.command_channel_id:
        await interaction.response.send_message("Silly goon. You can't run that command in this channel.")
        return

    # TODO remove this lines when done
    gdoc.set_sheet_id(sheet_id="1VcBBIxejr0dg87LH4hg_hnznaAcmt8Afq8plTBmD6-k")
    hunt_bot.sheet_name = "BotConfig"

    # TODO best way to handle table name storage?
    hunt_bot.config_table_name = "Discord Conf"

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


# Run bot
bot.run(TOKEN)
# bot.run(hunt_bot.discord_token)
