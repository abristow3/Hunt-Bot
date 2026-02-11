import discord
from discord.ext import commands, tasks
from huntbot.HuntBot import HuntBot
from huntbot.exceptions import TableDataImportException, ConfigurationException
import logging
import json
import requests

logger = logging.getLogger(__name__)


class FluxRLPluginCog(commands.Cog):
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot) -> None:
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.plugin_drops_channel_id = 0
        self.configured = False
        self.participant_whitelist: set[str] = set()
        self.monster_whitelist: set[str] = set()
        self.item_whitelist: set[str] = set()
        self.monster_whitelist_fp = "../conf/monster_whitelist.json"
        self.item_whitelist_fp = "../conf/item_whitelist.json"

        # Comp ID gets appended onto URLs later after config is retrieved
        self.wom_competition_id = 0
        self.wom_event_api_url = "https://api.wiseoldman.net/v2/competitions/"
        self.wom_event_website_url = "https://wiseoldman.net/competitions/"

    async def cog_load(self) -> None:
        """Runs when the cog is loaded and bot is ready."""
        logger.info("[FluxRLPlugin Cog] Loading Score Cog.")

        try:
            self.get_flux_plugin_drops_channel()
            self.get_wom_competition_id()
            # Generate the WOM Competition URLs using the Comp ID from the configuration
            self.generate_wom_competition_urls()
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

    def get_wom_competition_id(self) -> None:
        self.wom_competition_id = int(self.hunt_bot.config_map.get('WOM_COMPETITION_ID', "0"))

        if self.wom_competition_id == 0:
            logger.error("[FluxRLPlugin Cog] No WOM_COMPETITION_ID found in configuration.")
            raise ConfigurationException(config_key='WOM_COMPETITION_ID')

    def generate_participant_whitelist(self) -> None:
        """
        Iterates over the participations array in the JSON payload received from the WOM Hunt Competition query
        and saves the whitelist in memory.
        """
        url = "https://api.wiseoldman.net/v2/competitions/100262"
        r = requests.get(url)
        data = r.json()

        for player in data.get("participations", []):
            player_name = player.get("player", {}).get("displayName", "")
            if player_name:
                self.participant_whitelist.add(player_name)

    def print_whitelist(self) -> None:
        print(sorted(self.participant_whitelist))

    def generate_wom_competition_urls(self) -> None:
        """
        Appends the WOM Competition ID from the configuration to the end of the WOM event URls
        """
        self.wom_event_api_url = self.wom_event_api_url + str(self.wom_competition_id)
        self.wom_event_website_url = self.wom_event_website_url + str(self.wom_competition_id)

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

    def generate_plugin_config_monster_list(self) -> None:
        ...

    def generate_plugin_config_item_list(self) -> None:
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
