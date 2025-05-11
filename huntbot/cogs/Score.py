from discord.ext import commands, tasks
from huntbot.HuntBot import HuntBot
import pandas as pd
from string import Template
from huntbot import ConfigurationException, TableDataImportException

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # or DEBUG for more detail

# Optional: attach a console handler if not already configured globally
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


score_message = Template("""
The current score is $team1_name: $team1_points $team2_name: $team2_points
""")


class ScoreCog(commands.cog):
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot):
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.score_channel_id = 0
        self.team1_points = 0
        self.team2_points = 0
        self.score_table_name = "Current Score"
        self.message = None
        self.configured = False
        self.alert_channel_id = 0
        self.alert_sent = False  # Prevent spam
        self.score_crash_count = 0

        self.setup()
        self.start_scores.start()
        self.watch_scores.start()

    def setup(self):
        self.get_score_channel()
        self.get_alert_channel()
        self.configured = True

    def get_alert_channel(self):
        self.alert_channel_id = int(self.hunt_bot.config_map.get('ALERT_CHANNEL_ID', "0"))

        if self.alert_channel_id == 0:
            raise ConfigurationException(config_key='ALERT_CHANNEL_ID')

    def get_score_channel(self):
        self.score_channel_id = int(self.hunt_bot.config_map.get('POINTS_CHANNEL_ID', "0"))

        if self.score_channel_id == 0:
            raise ConfigurationException(config_key='POINTS_CHANNEL_ID')

    def get_score(self):
        # use table map to find score table
        # pull data
        score_df = self.hunt_bot.pull_table_data(table_name=self.score_table_name)

        if score_df.empty:
            raise TableDataImportException(table_name=self.score_table_name)

        score_dict = pd.Series(score_df['Total Points'].values, index=score_df['Team Name']).to_dict()
        self.team1_points = score_dict.get("Team Orange", "")
        self.team2_points = score_dict.get("Team Green", "")

    @tasks.loop(seconds=10)
    async def start_scores(self):
        try:
            channel = self.bot.get_channel(self.score_channel_id)
            if not channel:
                logger.warning("Score channel not found.")
                return

            self.get_score()  # your custom data logic
            message = (
                f"The current score is\n"
                f"Team Orange: {self.team1_points}\n"
                f"Team Green: {self.team2_points}"
            )
            if self.message:
                await self.message.edit(content=message)
            else:
                self.message = await channel.send(message)

            self.alert_sent = False  # Reset alert flag on success
            self.score_crash_count = 0  # Reset crash count on recovery

        except Exception as e:
            logger.exception("Exception in score loop")
            self.score_crash_count += 1
            if not self.alert_sent:
                await self.send_crash_alert(str(e))
                self.alert_sent = True

    @start_scores.before_loop
    async def before_start_scores(self):
        """Runs before the loop starts, useful for async setup."""
        await self.bot.wait_until_ready()  # Ensures bot is logged in before starting

    @tasks.loop(seconds=30)
    async def watch_scores(self):
        """Watchdog task that checks if the score loop is still running."""
        if not self.start_scores_loop.is_running():
            print("[ScoreCog] Score loop is not running. Restarting...")
            try:
                self.start_scores_loop.start()
            except RuntimeError:
                # Already running or not yet stopped properly
                pass

    @watch_scores.before_loop
    async def before_watch_scores(self):
        await self.bot.wait_until_ready()

    async def send_crash_alert(self, error_message: str):
        channel = self.bot.get_channel(self.alert_channel_id)
        if channel:
            await channel.send(
                f":warning: **ScoreCog loop crashed**\n"
                f"```{error_message}```"
            )
