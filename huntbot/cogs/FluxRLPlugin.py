import discord
from discord.ext import commands, tasks
from huntbot.HuntBot import HuntBot
from huntbot.exceptions import TableDataImportException, ConfigurationException
import logging

logger = logging.getLogger(__name__)


class FluxRLPluginCog(commands.Cog):
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot) -> None:
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.plugin_drops_channel_id = 0
        self.configured = False

    async def cog_load(self) -> None:
        """Runs when the cog is loaded and bot is ready."""
        logger.info("[FluxRLPlugin Cog] Loading Score Cog.")

        try:
            self.get_flux_plugin_drops_channel()
            self.configured = True
        except ConfigurationException as e:
            logger.error(f"[FluxRLPlugin Cog] Failed configuration: {e}")
            return

        # Start loops
        self.start_flux_rl_plugin.start()

    async def cog_unload(self) -> None:
        """Cleans up background tasks on cog unload."""
        logger.info("[FluxRLPlugin Cog] Unloading Score Cog.")
        if self.start_flux_rl_plugin.is_running():
            self.start_flux_rl_plugin.stop()

    def get_flux_plugin_drops_channel(self) -> None:
        self.plugin_drops_channel_id = int(self.hunt_bot.config_map.get('FLUX_PLUGIN_DROPS_CHANNEL_ID', "0"))

        if self.plugin_drops_channel_id == 0:
            logger.error("[FluxRLPlugin Cog] No FLUX_PLUGIN_DROPS_CHANNEL_ID found in configuration.")
            raise ConfigurationException(config_key='FLUX_PLUGIN_DROPS_CHANNEL_ID')

    # TODO Determine how long interval should be
    @tasks.loop(seconds=10)
    async def start_flux_rl_plugin(self) -> None:
        if not self.configured:
            logger.warning("[FluxRLPlugin Cog] Cog not properly configured. Skipping score update.")
            return

        try:
            channel = self.discord_bot.get_channel(self.plugin_drops_channel_id)
            if not channel:
                logger.warning("[FluxRLPlugin Cog] Plugin Drops channel not found.")
                return

            try:
                print("PUT YOUR PLUGIN LOGIC LOOP HERE")
            except TableDataImportException as e:
                logger.error("[FluxRLPlugin Cog] <PUT SOMETHING HERE>", exc_info=e)
        except Exception as e:
            logger.error("[FluxRLPlugin Cog] Error hit in FluxRLPlugin loop.", exc_info=e)

    @start_flux_rl_plugin.before_loop
    async def before_start_flux_rl_plugin(self) -> None:
        """
        Runs before the start_scores loop starts. Ensures the bot is ready before starting.

        Returns:
            None
        """
        await self.discord_bot.wait_until_ready()
