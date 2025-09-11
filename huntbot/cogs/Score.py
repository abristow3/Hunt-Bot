from discord.ext import commands, tasks
from huntbot.HuntBot import HuntBot
import pandas as pd
from string import Template
from huntbot.exceptions import TableDataImportException, ConfigurationException
import logging

logger = logging.getLogger(__name__)

score_message = Template("""
The current score is $team1_name: $team1_points $team2_name: $team2_points
""")


class ScoreCog(commands.Cog):
    """
    A cog that manages and updates the score on Discord.

    This cog includes tasks that retrieve score data from the HuntBot API,
    update the score message on Discord, and handle failure recovery mechanisms.
    """

    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot) -> None:
        """
        Initialize the ScoreCog with necessary bot and huntbot instances.

        Args:
            discord_bot (commands.Bot): The instance of the Discord bot.
            hunt_bot (HuntBot): The instance of the HuntBot containing game data.

        Returns:
            None
        """
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
        self.lead_message = ""
        self.score_message = ""

        self.setup()
        self.start_scores.start()
        self.watch_scores.start()

    def setup(self) -> None:
        """
        Set up the initial configuration by fetching channels and validating configurations.

        Returns:
            None
        """
        self.get_score_channel()
        self.get_alert_channel()
        self.configured = True

    def get_alert_channel(self) -> None:
        """
        Retrieve the alert channel from the HuntBot configuration.

        Raises:
            ConfigurationException: If the ALERT_CHANNEL_ID is not set in the configuration.

        Returns:
            None
        """
        self.alert_channel_id = int(self.hunt_bot.config_map.get('ALERT_CHANNEL_ID', "0"))

        if self.alert_channel_id == 0:
            logger.error("[Score Cog] No ALERT_CHANNEL_ID found in configuration.")
            raise ConfigurationException(config_key='ALERT_CHANNEL_ID')

    def get_score_channel(self) -> None:
        """
        Retrieve the score channel from the HuntBot configuration.

        Raises:
            ConfigurationException: If the POINTS_CHANNEL_ID is not set in the configuration.

        Returns:
            None
        """
        self.score_channel_id = int(self.hunt_bot.config_map.get('POINTS_CHANNEL_ID', "0"))

        if self.score_channel_id == 0:
            logger.error("[Score Cog] No POINTS_CHANNEL_ID found in configuration.")
            raise ConfigurationException(config_key='POINTS_CHANNEL_ID')

    def get_score(self) -> None:
        """
        Retrieve and parse the score data from the HuntBot score table.

        Raises:
            TableDataImportException: If the score table data is empty or unavailable.

        Returns:
            None
        """
        logger.info("[Score Cog] Attempting to fetch score.")
        # Use table map to find score table and pull data
        score_df = self.hunt_bot.pull_table_data(table_name=self.score_table_name)

        if score_df.empty:
            logger.error("[Score Cog] Error retrieving score data from GDoc table.")
            raise TableDataImportException(table_name=self.score_table_name)

        score_dict = pd.Series(score_df['Total Points'].values, index=score_df['Team Name']).to_dict()
        self.team1_points = score_dict.get(f"Team {self.hunt_bot.team_one_name}", 0)
        self.team2_points = score_dict.get(f"Team {self.hunt_bot.team_two_name}", 0)

    def determine_lead(self) -> None:
        # Calculate lead
        if self.team1_points > self.team2_points:
            lead_team = self.hunt_bot.team_one_name
            lead_points = self.team1_points - self.team2_points
            self.lead_message = f"Team {lead_team} is ahead by {lead_points} point{'s' if lead_points != 1 else ''}!"
        elif self.team2_points > self.team1_points:
            lead_team = self.hunt_bot.team_two_name
            lead_points = self.team2_points - self.team1_points
            self.lead_message = f"Team {lead_team} is ahead by {lead_points} point{'s' if lead_points != 1 else ''}!"
        else:
           self.lead_message = "It's a tie!"

    @tasks.loop(seconds=10)
    async def start_scores(self) -> None:
        """
        Asynchronously update the score on Discord every 10 seconds.

        If an exception occurs, it will attempt to alert the specified channel and prevent spam.

        Returns:
            None
        """
        try:
            channel = self.discord_bot.get_channel(self.score_channel_id)
            if not channel:
                logger.warning("Score channel not found.")
                return

            try:
                self.get_score()
            except TableDataImportException as e:
                logger.error("[Score Cog] Failed to update score, skipping update cycle.")
                return 

            self.determine_lead()
            
            self.score_message = (
                f"The current score is\n"
                f"Team {self.hunt_bot.team_one_name}: {self.team1_points}\n"
                f"Team {self.hunt_bot.team_two_name}: {self.team2_points}\n\n"
                f"{self.lead_message}"
            )
            if self.message:
                await self.message.edit(content=self.score_message)
            else:
                self.message = await channel.send(self.score_message)

            self.alert_sent = False  # Reset alert flag on success
            self.score_crash_count = 0  # Reset crash count on recovery

        except Exception as e:
            logger.error("[Score Cog] Error hit in score loop.")
            self.score_crash_count += 1
            if not self.alert_sent:
                await self.send_crash_alert(str(e))
                self.alert_sent = True

    @start_scores.before_loop
    async def before_start_scores(self) -> None:
        """
        Runs before the start_scores loop starts. Ensures the bot is ready before starting.

        Returns:
            None
        """
        await self.discord_bot.wait_until_ready()  # Ensures bot is logged in before starting

    @tasks.loop(seconds=30)
    async def watch_scores(self) -> None:
        """
        Watchdog task that checks if the score loop is still running and restarts it if not.

        Returns:
            None
        """
        if not self.start_scores.is_running():
            logger.error("[Score Cog] Score loop is not running. Restarting...")
            try:
                self.start_scores.start()
            except RuntimeError:
                # Already running or not yet stopped properly
                pass

    @watch_scores.before_loop
    async def before_watch_scores(self) -> None:
        """
        Runs before the watch_scores loop starts. Ensures the bot is ready before starting.

        Returns:
            None
        """
        await self.discord_bot.wait_until_ready()

    async def send_crash_alert(self, error_message: str) -> None:
        """
        Send an alert to the specified channel when the score loop crashes.

        Args:
            error_message (str): The error message to send in the alert.

        Returns:
            None
        """
        channel = self.discord_bot.get_channel(self.alert_channel_id)
        if channel:
            try:
                await channel.send(
                    f":warning: **ScoreCog loop crashed**\n"
                    f"```{error_message}```"
                )
            except Exception as e:
                logger.error("[Score Cog] Failed to send crash alert to Discord", exc_info=True)

    async def cog_unload(self) -> None:
        """
        Stops the tasks when the cog is unloaded.

        Returns:
            None
        """
        logger.info("[Score Cog] Unloading Score Cog.")
        if self.start_scores.is_running():
            self.start_scores.stop()
        if self.watch_scores.is_running():
            self.watch_scores.stop()
