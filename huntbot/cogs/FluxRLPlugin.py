import discord
from discord.ext import commands, tasks
from huntbot.HuntBot import HuntBot
from huntbot.exceptions import TableDataImportException, ConfigurationException
import logging
import json
import requests
import pandas as pd
from huntbot.GDoc import GDoc

logger = logging.getLogger(__name__)


class FluxRLPluginCog(commands.Cog):
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot, gdoc: GDoc) -> None:
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.gdoc = gdoc
        self.plugin_drops_channel_id = 0
        self.configured = False
        self.participant_whitelist: set[str] = set()
        self.monster_whitelist: set[str] = set()
        self.item_whitelist: set[str] = set()
        self.monster_whitelist_fp = "../conf/monster_whitelist.json"
        self.item_whitelist_fp = "../conf/item_whitelist.json"
        self.flux_rl_plugin_sheet_id = ""
        self.sheet_data = pd.DataFrame()
        self.sheet_name = "Hunt"

    async def cog_load(self) -> None:
        """Runs when the cog is loaded and bot is ready."""
        logger.info("[FluxRLPlugin Cog] Loading Score Cog.")

        try:
            self.get_flux_plugin_drops_channel()
            self.get_flux_rl_plugin_gdoc_sheet_id()
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

    def get_flux_rl_plugin_gdoc_sheet_id(self) -> None:
        self.flux_rl_plugin_sheet_id = int(self.hunt_bot.config_map.get('FLUX_RL_PLUGIN_GDOC_SHEET_ID', "0"))

        if self.flux_rl_plugin_sheet_id == 0:
            logger.error("[FluxRLPlugin Cog] No FLUX_RL_PLUGIN_GDOC_SHEET_ID found in configuration.")
            raise ConfigurationException(config_key='FLUX_RL_PLUGIN_GDOC_SHEET_ID')

    def generate_participant_whitelist(self) -> None:
        """
        Iterates over the participations array in the JSON payload received from the WOM Hunt Competition query
        and saves the whitelist in memory.
        """
        # TODO add exception handling here
        url = self.hunt_bot.wom_event_api_url
        r = requests.get(url)
        data = r.json()

        for player in data.get("participations", []):
            player_name = player.get("player", {}).get("displayName", "")
            if player_name:
                self.participant_whitelist.add(player_name)

    def read_monster_whitelist_file(self) -> None:
        with open(self.monster_whitelist_fp, "r", encoding="utf-8") as f:
            monsters = json.load(f)

        # Convert the list to a set
        self.monster_whitelist = set(monsters)

    def read_item_whitelist_file(self) -> None:
        with open(self.item_whitelist_fp, "r", encoding="utf-8") as f:
            items = json.load(f)

        # Convert the list to a set
        self.item_whitelist = set(items)

    def write_monster_whitelist_to_plugin_config_gdoc(self) -> None:
        ...

    def write_item_whitelist_to_plugin_config_gdoc(self) -> None:
        ...

    def write_player_whitelist_to_plugin_config_gdoc(self) -> None:
        ...

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
        """
        await self.discord_bot.wait_until_ready()
