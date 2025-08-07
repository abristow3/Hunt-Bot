import discord
from discord import app_commands
import logging
import io
import yaml
from huntbot.cogs.StarBoard import StarBoardCog
from huntbot.commands.bounty_commands import ItemBounties

logger = logging.getLogger(__name__)


async def beep(interaction: discord.Interaction):
    logger.info("/beep command ran")
    await interaction.response.send_message("Boop")


async def start_hunt(interaction: discord.Interaction, gdoc, hunt_bot, state, bot):
    try:
        await interaction.response.defer()
    except discord.NotFound:
        logger.error("Failed to defer interaction: already expired")
        return

    if not any(role.name.lower() == "admin" for role in interaction.user.roles):
        await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
        return

    logger.info(f"/start-hunt command ran")

    if gdoc.sheet_id == "":
        await interaction.followup.send("No GDoc sheet ID set. Use the command '/sheet' to set one.")
        return

    if hunt_bot.sheet_name == "":
        await interaction.followup.send("No GDoc sheet name set. Use the command '/sheet' to set one.")
        return

    try:
        hunt_bot.set_sheet_data(data=gdoc.get_data_from_sheet(sheet_name=hunt_bot.sheet_name))
    except Exception as e:
        logger.error(e)
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
        await bot.add_cog(StarBoardCog(discord_bot=bot, hunt_bot=hunt_bot))
    except Exception as e:
        logger.error("Error loading StarBoardCog", exc_info=e)

    try:
        await state.update_state(bot=True, **hunt_bot.config_map)
    except Exception as e:
        logger.error("Error updating state", exc_info=e)

    await interaction.followup.send(
        f"Hunt Bot successfully configured! The hunt will start on {hunt_bot.start_datetime}"
    )

    if not bot.check_start_time.is_running():
        bot.check_start_time.start()


async def sheet(interaction: discord.Interaction, sheet_id: str, sheet_name: str, config_table: str, gdoc, hunt_bot):
    if not any(role.name.lower() == "admin" for role in interaction.user.roles):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    gdoc.set_sheet_id(sheet_id=sheet_id)
    hunt_bot.set_sheet_name(sheet_name=sheet_name)
    hunt_bot.set_config_table_name(table_name=config_table)

    await interaction.response.send_message("Sheet ID and Name set successfully")


async def passwords(interaction: discord.Interaction, hunt_bot):
    response = (
        "**===== CURRENT PASSWORDS =====**\n\n"
        f"**MASTER:** {hunt_bot.master_password}\n"
        f"**DAILY:** {hunt_bot.daily_password}\n"
        f"**BOUNTY:** {hunt_bot.bounty_password}"
    )
    await interaction.response.send_message(response)


async def show_state(interaction: discord.Interaction, hunt_bot, state):
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


def register_main_commands(tree: app_commands.CommandTree, gdoc, hunt_bot, state, bot):
    logger.info("Registering main commands")

    @tree.command(name="beep")
    async def beep_cmd(interaction: discord.Interaction):
        await beep(interaction)

    @tree.command(name="start-hunt", description="Starts the Hunt Bot on the pre-configured date and time")
    async def start_cmd(interaction: discord.Interaction):
        await start_hunt(interaction, gdoc=gdoc, hunt_bot=hunt_bot, state=state, bot=bot)

    @tree.command(name="sheet", description="Updates the GDoc sheet ID that the Hunt Bot references")
    @app_commands.describe(sheet_id="The GDoc sheet ID", sheet_name="The name of the sheet in the GDoc",
                           config_table="Name of the discord configuration table in the sheet")
    async def sheet_cmd(interaction: discord.Interaction, sheet_id: str, sheet_name: str = "BotConfig",
                        config_table: str = "Discord Conf"):
        await sheet(interaction, sheet_id, sheet_name, config_table, gdoc, hunt_bot)

    @tree.command(name="passwords", description="Display the current hunt passwords.")
    async def passwords_cmd(interaction: discord.Interaction):
        await passwords(interaction, hunt_bot)

    @tree.command(name="state", description="Show the current state file contents")
    async def state_cmd(interaction: discord.Interaction):
        await show_state(interaction, hunt_bot, state)
