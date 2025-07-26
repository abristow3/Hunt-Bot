import pytz
from datetime import timedelta, datetime
from discord.ext import commands, tasks
from string import Template
from huntbot.HuntBot import HuntBot
from huntbot.exceptions import TableDataImportException, ConfigurationException

begins_template = Template("""
The Hunt begins in $num_hours hours!
""")

ends_template = Template("""
The Hunt ends in $num_hours hours!
""")


class CountdownCog(commands.Cog):
    def __init__(self, bot: commands.Bot, hunt_bot: HuntBot):
        self.bot = bot
        self.hunt_bot = hunt_bot

        self.announcements_channel_id = 0
        self.countdown_start_date = self.hunt_bot.start_datetime - timedelta(days=1)
        self.countdown_end_date = self.countdown_start_date + timedelta(days=9)

        self.start_completed = False
        self.end_completed = False
        self.message = ""
        self.countdown_task_started = False
        self.countdown_intervals = [24, 12, 6, 2, 1]

        self.bot.loop.create_task(self.initialize())

    async def initialize(self):
        try:
            self.setup()
            self.start_countdown()
        except Exception as e:
            logger.error(f"[Countdown Cog] Initialization failed: {e}")

    def setup(self):
        self.announcements_channel_id = int(self.hunt_bot.config_map.get('ANNOUNCEMENTS_CHANNEL_ID', "0"))
        if self.announcements_channel_id == 0:
            logger.error("[Countdown Cog] No ANNOUNCEMENTS_CHANNEL_ID found")
            raise ConfigurationException(config_key='ANNOUNCEMENTS_CHANNEL_ID')

    @staticmethod
    def get_current_gmt_time():
        gmt_timezone = pytz.timezone('Europe/London')
        return datetime.now(gmt_timezone)

    def check_time(self):
        return self.get_current_gmt_time()

    def start_countdown(self):
        if self.countdown_task_started:
            return

        self.countdown_task_started = True

        @tasks.loop(seconds=5)
        async def begin_countdown():
            logger.info("[Countdown Cog] checking countdown")
            await self.bot.wait_until_ready()
            ctime = self.check_time()
            channel = self.bot.get_channel(self.announcements_channel_id)
            if not channel:
                logger.info("[Countdown Cog] Announcements Channel not found.")
                return

            remaining_hours_start = round((self.hunt_bot.start_datetime - ctime).total_seconds() / 3600)
            remaining_hours_end = round((self.hunt_bot.end_datetime - ctime).total_seconds() / 3600)

            logger.info(f"[Countdown Cog] TIME TILL START: {remaining_hours_start}")
            logger.info(f"[Countdown Cog]: {remaining_hours_end}")

            if not self.start_completed and remaining_hours_start in self.countdown_intervals:
                self.message = begins_template.substitute(num_hours=remaining_hours_start)
                await channel.send(self.message)
                self.countdown_intervals.remove(remaining_hours_start)

            if not self.start_completed and not self.countdown_intervals:
                self.start_completed = True
                self.countdown_intervals = [24, 12, 6, 2, 1]

            if self.start_completed and not self.end_completed:
                if remaining_hours_end in self.countdown_intervals:
                    self.message = ends_template.substitute(num_hours=remaining_hours_end)
                    await channel.send(self.message)
                    self.countdown_intervals.remove(remaining_hours_end)
                if not self.countdown_intervals:
                    self.end_completed = True

            if not self.start_completed and ctime >= self.countdown_start_date:
                self.start_completed = True

            if not self.end_completed and ctime >= self.countdown_end_date:
                self.end_completed = True

        begin_countdown.start()
