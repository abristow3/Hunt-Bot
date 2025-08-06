#!/usr/bin/env python3
import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Button
import logging
from huntbot.GDoc import GDoc
from huntbot.HuntBot import HuntBot
from huntbot.cogs.Bounties import BountiesCog
from huntbot.cogs.Dailies import DailiesCog
from huntbot.cogs.StarBoard import StarBoardCog
from huntbot.cogs.Score import ScoreCog
from huntbot.cogs.Countdown import CountdownCog
import os
import datetime
from typing import List

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

# Global leaderboard dictionary: {team_tag: {user_id: {'name': str, 'count': int, 'value': float}}}
bounty_leaderboard = {'Red Team': {}, 'Gold Team': {}}


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
    # Only allow users with the specified roles to create bounties
    allowed_roles = {"Red Team Leader", "Gold Team Leader", "Staff"}
    if not any(role.name in allowed_roles for role in getattr(interaction.user, 'roles', [])):
        await interaction.response.send_message("You must be a Red Team Leader, Gold Team Leader, or Staff to create bounties.", ephemeral=True)
        return
    if interaction.channel.id != hunt_bot.command_channel_id:
        return

    bounty_key = name_of_item.strip().lower()
    # Prevent duplicate bounties with the same name
    if not hasattr(bot, 'active_bounties'):
        bot.active_bounties = {}
    if bounty_key in bot.active_bounties:
        await interaction.response.send_message(f"A bounty with the name '{name_of_item}' already exists. Please choose a different name.", ephemeral=True)
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


    # Allow K (thousand) and M (million) suffixes in reward_amount (case-insensitive)
    reward_str = reward_amount.strip()
    multiplier = 1
    if reward_str.lower().endswith('k'):
        multiplier = 1_000
        reward_str = reward_str[:-1]
    elif reward_str.lower().endswith('m'):
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
    # Prevent duplicate bounties with the same name
    if bounty_key in bot.active_bounties:
        await interaction.response.send_message(f"A bounty with the name '{name_of_item}' already exists. Please choose a different name.", ephemeral=True)
        return

    # Tag bounty with creator's leader role
    creator_roles = {role.name for role in getattr(interaction.user, 'roles', [])}
    bounty_team_tag = None
    if 'Red Team Leader' in creator_roles:
        bounty_team_tag = 'Red Team'
    elif 'Gold Team Leader' in creator_roles:
        bounty_team_tag = 'Gold Team'
    elif 'Staff' in creator_roles:
        bounty_team_tag = 'Staff'
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
    bot.active_bounties[bounty_key] = {
        'handle': None,  # will be set after task creation
        'reward_amount': reward_amount,
        'team_tag': bounty_team_tag,
        'expires_at': expires_at,
        'original_name': name_of_item.strip()
    }

    async def end_bounty():
        await interaction.followup.send(f"The bounty for '{name_of_item}' has ended after {minutes} minutes.")
        bot.active_bounties.pop(bounty_key, None)

    # Store the cancel handle so we can close early
    handle = bot.loop.create_task(_bounty_timer(end_bounty, minutes))
    bot.active_bounties[bounty_key]['handle'] = handle


# Command to close a bounty early and select a user as the claimer
@bot.tree.command(name="closebounty", description="Close an active bounty early by item name and optionally select a user as the claimer.")
@app_commands.describe(
    bounty_item="The item name of the bounty to close early.",
    user="The user who claimed the bounty (optional)."
)
async def closebounty(interaction: discord.Interaction, bounty_item: str, user: discord.Member = None):
    # Only allow users with the specified roles to close bounties
    allowed_roles = {"Red Team Leader", "Gold Team Leader", "Staff"}
    user_roles = {role.name for role in getattr(interaction.user, 'roles', [])}
    if not any(role in allowed_roles for role in user_roles):
        await interaction.response.send_message("You must be a Red Team Leader, Gold Team Leader, or Staff to close bounties.", ephemeral=True)
        return
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
    # Restrict team leaders to only close their own team's bounties
    team_tag = info.get('team_tag')
    if 'Staff' not in user_roles:
        if team_tag == 'Red Team' and 'Red Team Leader' not in user_roles:
            await interaction.response.send_message("Only Red Team Leaders or Staff can close Red Team bounties.", ephemeral=True)
            return
        if team_tag == 'Gold Team' and 'Gold Team Leader' not in user_roles:
            await interaction.response.send_message("Only Gold Team Leaders or Staff can close Gold Team bounties.", ephemeral=True)
            return
    handle = info['handle']
    handle.cancel()
    value = info['reward_amount']
    bot.active_bounties.pop(bounty_key, None)
    # Parse value as float for leaderboard
    try:
        value_num = float(str(value).replace('k', '000').replace('m', '000000').replace(',', ''))
    except Exception:
        value_num = 0
    if user:
        await interaction.response.send_message(f"Bounty for '{bounty_item}' has been claimed by {user.mention} for {int(value_num):,}!")
        # Update the leaderboard
        team_data = bounty_leaderboard.setdefault(info['team_tag'], {})
        user_data = team_data.setdefault(user.id, {'name': user.display_name, 'count': 0, 'value': 0, 'team': info['team_tag']})
        user_data['count'] += 1
        user_data['value'] += value_num
        user_data['team'] = info['team_tag']
    else:
        # Confirmation window for no winner
        view = ConfirmNoWinnerView()
        await interaction.response.send_message(f"Are you sure you want to close the bounty for '{bounty_item}' with no winner selected?", view=view, ephemeral=True)
        timeout = await view.wait()
        if view.value:
            await interaction.followup.send(f"Bounty for '{bounty_item}' has ended, no winner selected.")
        else:
            # Do not close the bounty, re-add it to active bounties
            bot.active_bounties[bounty_key] = info
        return

        # Command to list all active bounties (placed next to bounty command)
@bot.tree.command(name="listbounties", description="List all active bounties.")
async def listbounties(interaction: discord.Interaction):
    if interaction.channel.id != hunt_bot.command_channel_id:
        return
    if not hasattr(bot, 'active_bounties') or not bot.active_bounties:
        await interaction.response.send_message("There are no active bounties.", ephemeral=True)
        return
    import datetime
    user_roles = {role.name for role in getattr(interaction.user, 'roles', [])}
    now = datetime.datetime.utcnow()
    bounty_msgs = []
    for bounty_key, info in bot.active_bounties.items():
        team_tag = info.get('team_tag')
        # Staff can see all
        if 'Staff' in user_roles:
            show = True
        elif team_tag == 'Red Team' and ('Red Team' in user_roles or 'Red Team Leader' in user_roles):
            show = True
        elif team_tag == 'Gold Team' and ('Gold Team' in user_roles or 'Gold Team Leader' in user_roles):
            show = True
        else:
            show = False
        if show:
            # Calculate time remaining
            expires_at = info.get('expires_at')
            if expires_at:
                remaining = expires_at - now
                if remaining.total_seconds() > 0:
                    hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                    minutes = remainder // 60
                    time_str = f"{hours}h {minutes}m left"
                else:
                    time_str = "Expired"
            else:
                time_str = "Unknown"
            bounty_name = info.get('original_name', bounty_key)
            bounty_msgs.append(f"Bounty Item: {bounty_name} | Value: {info['reward_amount']} | {time_str}")
    if not bounty_msgs:
        await interaction.response.send_message("There are no active bounties for your team.", ephemeral=True)
        return
    msg = "**Active Bounties:**\n" + "\n".join(bounty_msgs)
    # Send to special channels for Red/Gold teams
    red_channel_id = 1401693654782967931
    gold_channel_id = 1401693679311257703
    if 'Red Team' in user_roles or 'Red Team Leader' in user_roles:
        channel = interaction.guild.get_channel(red_channel_id)
        if channel:
            await channel.send(msg)
            await interaction.response.send_message("Bounties sent to your team channel.", ephemeral=True)
            return
    elif 'Gold Team' in user_roles or 'Gold Team Leader' in user_roles:
        channel = interaction.guild.get_channel(gold_channel_id)
        if channel:
            await channel.send(msg)
            await interaction.response.send_message("Bounties sent to your team channel.", ephemeral=True)
            return
    # Staff and others see ephemeral message
    await interaction.response.send_message(msg, ephemeral=True)


# Command to show the top 3 bounty completers per team
@bot.tree.command(name="bountyleaderboard", description="Show the top 3 bounty completers per team.")
async def bountyleaderboard(interaction: discord.Interaction):
    if interaction.channel.id != hunt_bot.command_channel_id:
        return
    # Determine which team to show
    user_roles = {role.name for role in getattr(interaction.user, 'roles', [])}
    show_teams = []
    if 'Staff' in user_roles:
        show_teams = ['Red Team', 'Gold Team']
    elif 'Red Team' in user_roles or 'Red Team Leader' in user_roles:
        show_teams = ['Red Team']
    elif 'Gold Team' in user_roles or 'Gold Team Leader' in user_roles:
        show_teams = ['Gold Team']
    else:
        await interaction.response.send_message("You must be a member or leader of a team to view the leaderboard.")
        return
    msg = "**Bounty Leaderboard**\n"
    for show_team in show_teams:
        msg += f"\n__{show_team}__\n"
        team_data = bounty_leaderboard.get(show_team, {})
        # Show all users who have completed bounties for this team, regardless of current roles
        filtered = [entry for entry in team_data.values() if entry.get('team') == show_team]
        if not filtered:
            msg += "No completions yet.\n"
        else:
            top = sorted(filtered, key=lambda x: (x['value'], x['count']), reverse=True)[:3]
            for idx, entry in enumerate(top, 1):
                value_str = f"{int(entry['value']):,}"
                msg += f"{idx}. {entry['name']} - {entry['count']} bounties, {value_str} total value\n"
    await interaction.response.send_message(msg)


# Helper for bounty timer
import asyncio
async def _bounty_timer(callback, minutes):
    await asyncio.sleep(minutes * 60)
    await callback()


@bot.tree.command(name="start-hunt", description="Starts the Hunt Bot on the pre-configured date and time")
async def start(interaction: discord.Interaction):
    if interaction.channel.id != hunt_bot.command_channel_id:
        return

    logger.info(f"/start-hunt command ran")

    # Check sheet ID has been populated
    if gdoc.sheet_id == "":
        logger.info("Sheet ID not set")
        await interaction.response.send_message("No GDoc sheet ID set. Use the command '/sheet' to set one.")
        return

    # Check sheet name has been populated
    if hunt_bot.sheet_name == "":
        logger.info("Sheet Name not set")
        await interaction.response.send_message("No GDoc sheet name set. Use the command '/sheet' to set one.")
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
        await interaction.response.send_message("Error retrieving Hunt Bot configuration from GDoc. Check if the "
                                                "sheet ID and sheet name are correct.")
        return

    # There is data, so build the table map from the data so we can query it
    hunt_bot.build_table_map()

    # Check table map was created
    if not hunt_bot.table_map:
        logger.error("Error building table map for GDoc")
        await interaction.response.send_message("Error building sheet table map.")
        return

    # Get the HuntBot Configuration variables
    config_df = hunt_bot.pull_table_data(table_name=hunt_bot.config_table_name)

    # Check config data was found
    if config_df.empty:
        logger.error("Error retrieving configuration data from table")
        await interaction.response.send_message("Error retrieving config data.")
        return

    hunt_bot.load_config(df=config_df)

    # Check config data loaded
    if not hunt_bot.configured:
        logger.error("Hunt Bot Configuration failed to load")
        await interaction.response.send_message("Error setting config data.")
        return

    logger.info("Hunt Bot configured succesfully")

    await interaction.response.send_message(
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
        channel = bot.get_channel(699971574689955853)
        await channel.send("I'M ALIVEEEEE!!!!!!!\n"
                           "FEELS FRANKEN-THURGO MAN")
    except Exception as e:
        pass

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

class ConfirmNoWinnerView(View):
    def __init__(self):
        super().__init__(timeout=30)
        self.value = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        self.value = True
        self.stop()
        await interaction.response.edit_message(content="Bounty closed with no winner selected.", view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        self.value = False
        self.stop()
        await interaction.response.edit_message(content="Bounty closure cancelled.", view=None)

@bot.tree.command(name="updatebounty", description="Update the reward value and/or time remaining for an active bounty.")
@app_commands.describe(
    bounty_item="The item name of the bounty to update.",
    reward_amount="New reward amount (optional, e.g. 100k, 2M)",
    time_remaining="New time remaining in minutes (optional)"
)
async def updatebounty(
    interaction: discord.Interaction,
    bounty_item: str,
    reward_amount: str = None,
    time_remaining: str = None
):
    # Only allow staff or team leaders to update bounties
    allowed_roles = {"Red Team Leader", "Gold Team Leader", "Staff"}
    user_roles = {role.name for role in getattr(interaction.user, 'roles', [])}
    if not any(role in allowed_roles for role in user_roles):
        await interaction.response.send_message("You do not have permission to update bounties.", ephemeral=True)
        return
    if interaction.channel.id != hunt_bot.command_channel_id:
        return
    if not hasattr(bot, 'active_bounties') or not bot.active_bounties:
        await interaction.response.send_message("There are no active bounties to update.", ephemeral=True)
        return
    bounty_key = bounty_item.strip().lower()
    info = bot.active_bounties.get(bounty_key)
    if not info:
        await interaction.response.send_message("No active bounty found with that item name.", ephemeral=True)
        return
    updates = []
    # Update reward amount if provided
    if reward_amount:
        reward_str = reward_amount.strip()
        multiplier = 1
        if reward_str.lower().endswith('k'):
            multiplier = 1_000
            reward_str = reward_str[:-1]
        elif reward_str.lower().endswith('m'):
            multiplier = 1_000_000
            reward_str = reward_str[:-1]
        try:
            reward_val = float(reward_str) * multiplier
            if reward_val < 0:
                await interaction.response.send_message("Reward amount cannot be negative.", ephemeral=True)
                return
            info['reward_amount'] = reward_amount
            updates.append(f"reward value set to {reward_amount}")
        except ValueError:
            await interaction.response.send_message("Reward amount must be a number (optionally with 'K' for thousand or 'M' for million).", ephemeral=True)
            return
    # Update time remaining if provided
    if time_remaining:
        if not time_remaining.isdigit():
            await interaction.response.send_message("Please use only numbers for the time remaining.", ephemeral=True)
            return
        minutes = int(time_remaining)
        if minutes <= 0:
            await interaction.response.send_message("Time remaining must be positive.", ephemeral=True)
            return
        # Cancel the old timer and set a new one
        handle = info['handle']
        handle.cancel()
        import datetime
        info['expires_at'] = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
        async def end_bounty():
            await interaction.followup.send(f"The bounty for '{bounty_item}' has ended after being updated.")
            bot.active_bounties.pop(bounty_key, None)
        new_handle = bot.loop.create_task(_bounty_timer(end_bounty, minutes))
        info['handle'] = new_handle
        updates.append(f"time remaining set to {minutes} minutes")
    if not updates:
        await interaction.response.send_message("No updates provided. Please specify a new reward value and/or time remaining.", ephemeral=True)
        return
    await interaction.response.send_message(f"Bounty for '{bounty_item}' updated: {', '.join(updates)}.", ephemeral=True)
