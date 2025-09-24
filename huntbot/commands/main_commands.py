import discord
from discord import app_commands
import logging
import io
import yaml
from huntbot.HuntBot import HuntBot
from huntbot.GDoc import GDoc
from discord.ext.commands import Bot
from State import State
from huntbot.commands.command_utils import check_user_roles

logger = logging.getLogger(__name__)
    
async def beep(interaction: discord.Interaction):
    logger.info("/beep command ran")
    await interaction.response.send_message("Boop")


async def start_hunt(interaction: discord.Interaction, gdoc: GDoc, hunt_bot: HuntBot, discord_bot: Bot):
    try:
        await interaction.response.defer()
    except discord.NotFound:
        logger.error("Failed to defer interaction: already expired")
        return

    authorized_roles = ["admin"]
    authorized = await check_user_roles(interaction=interaction, authorized_roles=authorized_roles)
    if not authorized:
        return

    logger.info(f"/start-hunt command ran")

    if gdoc.sheet_id == "":
        await interaction.followup.send("No GDoc sheet ID set. Use the command '/sheet' to set one.")
        return

    if hunt_bot.sheet_name == "":
        await interaction.followup.send("No GDoc sheet name set. Use the command '/sheet' to set one.")
        return

    # Start the main Hunt logic loop
    if not discord_bot.check_start_time.is_running():
        discord_bot.check_start_time.start()


async def sheet(interaction: discord.Interaction, sheet_id: str, sheet_name: str, config_table: str, gdoc: GDoc, hunt_bot: HuntBot, state: State):
    try:
        await interaction.response.defer()
    except discord.NotFound:
        logger.error("[SHEET COMMAND] Failed to defer interaction: already expired")
        return

    authorized_roles = ["admin"]
    authorized = await check_user_roles(interaction=interaction, authorized_roles=authorized_roles)
    if not authorized:
        return

    logger.info(f"/sheet command ran") 

    gdoc.set_sheet_id(sheet_id=sheet_id)
    hunt_bot.set_sheet_name(sheet_name=sheet_name)
    hunt_bot.set_config_table_name(table_name=config_table)

    await interaction.followup.send("Sheet ID and Name set successfully")

    # Retrieve the configuration from the GDoc
    try:
        hunt_bot.set_sheet_data(data=gdoc.get_data_from_sheet(sheet_name=hunt_bot.sheet_name))
    except Exception as e:
        logger.error(f"[SHEET COMMAND] Error retrieving sheet data", exc_info=e)
        await interaction.followup.send("Error retrieving sheet data.")
        return

    if hunt_bot.sheet_data.empty:
        await interaction.followup.send("Sheet is empty or not configured properly.")
        return

    hunt_bot.build_table_map()
    if not hunt_bot.table_map:
        await interaction.followup.send("Error building sheet table map.")
        return

    config_df = hunt_bot.pull_table_data(table_name=hunt_bot.config_table_name)
    if config_df.empty:
        await interaction.followup.send("Error retrieving config data.")
        return

    hunt_bot.load_config(df=config_df)
    if not hunt_bot.configured:
        await interaction.followup.send("Failed to configure hunt bot.")
        return

    try:
        await state.update_state(bot=True, **hunt_bot.config_map)
    except Exception as e:
        logger.error("Error updating state", exc_info=e)
    
    await interaction.followup.send(
        f"Hunt Bot successfully configured! The hunt will start on {hunt_bot.start_datetime}. Next, if you want to start the hunt, run the /start-hunt command"
    )


async def passwords(interaction: discord.Interaction, hunt_bot: HuntBot):
    response = (
        "**===== CURRENT PASSWORDS =====**\n\n"
        f"**MASTER:** {hunt_bot.master_password}\n"
        f"**DAILY:** {hunt_bot.daily_password}\n"
        f"**BOUNTY:** {hunt_bot.bounty_password}"
    )
    await interaction.response.send_message(response)


async def show_state(interaction: discord.Interaction, hunt_bot: HuntBot, state: State):
    if interaction.channel.id != hunt_bot.admin_channel_id:
        return

    if not state.state_data:
        await interaction.response.send_message("State is currently empty.")
        return

    yaml_text = yaml.safe_dump(state.state_data, sort_keys=False)
    fp = io.BytesIO(yaml_text.encode("utf-8"))

    await interaction.response.send_message(
        content="📄 Full state file attached (too long to display):",
        file=discord.File(fp, filename="state.yaml")
    )


def register_main_commands(tree: app_commands.CommandTree, gdoc: GDoc, hunt_bot:HuntBot, state:State, discord_bot:Bot):
    logger.info("Registering main commands")

    @tree.command(name="beep")
    async def beep_cmd(interaction: discord.Interaction):
        await beep(interaction=interaction)

    @tree.command(name="start-hunt", description="Starts the Hunt Bot on the pre-configured date and time")
    async def start_cmd(interaction: discord.Interaction):
        await start_hunt(interaction=interaction, gdoc=gdoc, hunt_bot=hunt_bot, discord_bot=discord_bot)

    @tree.command(name="sheet", description="Updates the GDoc sheet ID that the Hunt Bot references")
    @app_commands.describe(sheet_id="The GDoc sheet ID", sheet_name="The name of the sheet in the GDoc",
                           config_table="Name of the discord configuration table in the sheet")
    async def sheet_cmd(interaction: discord.Interaction, state: State, sheet_id: str, sheet_name: str = "BotConfig",
                        config_table: str = "Discord Conf"):
        await sheet(interaction=interaction, sheet_id=sheet_id, sheet_name=sheet_name, config_table=config_table, gdoc=gdoc, hunt_bot=hunt_bot, state=state)

    @tree.command(name="passwords", description="Display the current hunt passwords.")
    async def passwords_cmd(interaction: discord.Interaction):
        await passwords(interaction=interaction, hunt_bot=hunt_bot)

    @tree.command(name="state", description="Show the current state file contents")
    async def state_cmd(interaction: discord.Interaction):
        await show_state(interaction=interaction, hunt_bot=hunt_bot, state=state)
