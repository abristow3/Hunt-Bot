import pytz
from datetime import timedelta, datetime
from discord.ext import commands, tasks
from string import Template
from huntbot.HuntBot import HuntBot
from huntbot.exceptions import ConfigurationException
import logging

logger = logging.getLogger(__name__)

begins_template = Template("""
The Hunt begins in $num_hours hours!
""")

ends_template = Template("""
The Hunt ends in $num_hours hours!
""")


class CountdownCog(commands.Cog):
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot):
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.announcements_channel_id = 0
        self.start_completed = False
        self.end_completed = False
        self.message = ""
        self.start_countdown_intervals = [24, 12, 6, 2, 1]
        self.end_countdown_intervals = [24, 12, 6, 2, 1]
        self.configured = False

    async def cog_load(self) -> None:
        """Called when the cog is loaded and ready."""
        logger.info("[Countdown Cog] Loading cog and initializing.")
        try:
            self.get_announcements_channel()
            self.configured = True
            self.startup_check()
            self.start_countdown.start()
        except Exception as e:
            logger.error(f"[Countdown Cog] Initialization failed: {e}")
            self.configured = False

    async def cog_unload(self) -> None:
        """Called when the cog is unloaded to stop tasks."""
        logger.info("[Countdown Cog] Unloading cog.")
        if self.start_countdown.is_running():
            self.start_countdown.stop()

    def get_announcements_channel(self) -> None:
        self.announcements_channel_id = int(self.hunt_bot.config_map.get('ANNOUNCEMENTS_CHANNEL_ID', "0"))
        if self.announcements_channel_id == 0:
            logger.error("[Countdown Cog] No ANNOUNCEMENTS_CHANNEL_ID found")
            raise ConfigurationException(config_key='ANNOUNCEMENTS_CHANNEL_ID')

    @staticmethod
    def get_current_gmt_time() -> datetime:
        gmt_timezone = pytz.timezone('Europe/London')
        return datetime.now(gmt_timezone)

    @tasks.loop(seconds=30) 
    async def start_countdown(self) -> None:
        if not self.configured:
            logger.warning("[Countdown Cog] Cog not configured, skipping countdown.")
            return
        
        channel = self.discord_bot.get_channel(self.announcements_channel_id)
        
        if not channel:
            logger.error("[Countdown Cog] Announcements Channel not found.")
            return

        current_time = self.get_current_gmt_time()

        # Post a countdown start message logic
        if not self.start_completed and not self.end_completed:
            # Make sure there is an element in the interval list still
            if self.start_countdown_intervals:
                next_interval = self.start_countdown_intervals[0]
                target_time = self.hunt_bot.start_datetime - timedelta(hours=next_interval)
                
                if current_time >= target_time:
                    # Post message
                    logger.info(f"[Countdown Cog] Posting Countdown start message for interval: {next_interval} hours.")
                    self.message = begins_template.safe_substitute(num_hours=next_interval)
                    await channel.send(self.message)
                    self.start_countdown_intervals.pop(0)

            if not self.start_countdown_intervals:
                logger.info(f"[Countdown Cog] Start messages completed.")
                self.start_completed = True

        # post a countdown end message logic
        if self.start_completed and not self.end_completed:
            # Make sure there is an element in the interval list still
            if self.end_countdown_intervals:
                next_interval = self.end_countdown_intervals[0]
                target_time = self.hunt_bot.end_datetime - timedelta(hours=next_interval)
                
                if current_time >= target_time:
                    # Post message
                    logger.info(f"[Countdown Cog] Posting Countdown end message for interval: {next_interval} hours.")
                    self.message = ends_template.safe_substitute(num_hours=next_interval)
                    await channel.send(self.message)
                    self.end_countdown_intervals.pop(0)
            
            if not self.end_countdown_intervals:
                logger.info(f"[Countdown Cog] End messages completed.")
                self.end_completed = True
        
        # Countdown completed logic
        if self.start_completed and self.end_completed:
            logger.info(f"[Countdown Cog] Start and End messages completed.")
            self.start_countdown.stop()


    @start_countdown.before_loop
    async def before_start_countdown(self) -> None:
        await self.discord_bot.wait_until_ready()

    def startup_check(self) -> None:
        '''
        On cog startup, checks the current time against hunt start time and the interval list,
        removing any intervals that have already passed to ensure correct countdown behavior.
        '''
        if not self.hunt_bot.started:
            current_time = self.get_current_gmt_time()
            current_delta = self.hunt_bot.start_datetime - current_time
            hours_until_start = current_delta.total_seconds() / 3600

            # Filter out intervals that are already passed using a for loop
            updated_intervals = []
            for interval in self.start_countdown_intervals:
                if interval <= hours_until_start:
                    updated_intervals.append(interval)

            self.start_countdown_intervals = updated_intervals

            logger.info(f"[Countdown Cog] Filtered start intervals: {self.start_countdown_intervals}")

        # If the hunt has started but not ended
        if self.hunt_bot.started and not self.hunt_bot.ended:
            # Set countdown start_complete to True so it bypasses it in task loop
            self.start_completed = True

            current_time = self.get_current_gmt_time()
            current_delta = self.hunt_bot.end_datetime - current_time
            hours_until_end = current_delta.total_seconds() / 3600

            # Filter out intervals that are already passed using a for loop
            updated_intervals = []
            for interval in self.end_countdown_intervals:
                if interval <= hours_until_end:
                    updated_intervals.append(interval)

            self.end_countdown_intervals = updated_intervals

            logger.info(f"[Countdown Cog] Filtered end intervals: {self.end_countdown_intervals}")

