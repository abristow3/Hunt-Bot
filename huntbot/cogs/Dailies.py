from discord.ext import commands, tasks
import pandas as pd
from string import Template
from huntbot.HuntBot import HuntBot
from huntbot.exceptions import TableDataImportException, ConfigurationException
import logging

logger = logging.getLogger(__name__)

dan_message = "Dan's late. Don't worry boss I'll take care of it..."

single_daily_template = Template("""
@everyone $task

Password: $password
""")

double_daily_template = Template("""
@everyone $b1_task

Password: $b1_password

@@@ DOUBLE DAILY @@@

$b2_task

""")


class DailiesCog(commands.Cog):
    def __init__(self, bot: commands.Bot, hunt_bot: HuntBot):
        self.bot = bot
        self.hunt_bot = hunt_bot

        self.daily_channel_id = 0
        self.daily_interval = 24
        self.single_dailies_df = pd.DataFrame()
        self.double_dailies_df = pd.DataFrame()
        self.single_dailies_table_name = "Single Dailies"
        self.double_dailies_table_name = "Double Dailies"
        self.message = ""
        self.message_id = 0
        self.configured = False

        self.single_daily_generator = None
        self.double_daily_generator = None

    async def cog_load(self) -> None:
        """Called when the cog is loaded and ready."""
        logger.info("[Dailies Cog] Loading cog and initializing.")
        try:
            self.get_daily_channel()
            self.get_single_dailies()
            self.get_double_dailies()

            self.single_daily_generator = self.yield_next_row(self.single_dailies_df)
            self.double_daily_generator = self.yield_next_row(self.double_dailies_df)
            self.configured = True
            self.start_dailies.start()
        except Exception as e:
            logger.error(f"[Dailies Cog] Initialization failed: {e}")
            self.configured = False

    async def cog_unload(self) -> None:
        """Called when the cog is unloaded to stop tasks."""
        logger.info("[Dailies Cog] Unloading cog.")
        if self.start_dailies.is_running():
            self.start_dailies.stop()

    def get_daily_channel(self) -> None:
        self.daily_channel_id = int(self.hunt_bot.config_map.get('DAILY_CHANNEL_ID', "0"))
        if self.daily_channel_id == 0:
            logger.error("[Dailies Cog] DAILY_CHANNEL_ID not found")
            raise ConfigurationException(config_key='DAILY_CHANNEL_ID')

    def get_single_dailies(self) -> None:
        self.single_dailies_df = self.hunt_bot.pull_table_data(table_name=self.single_dailies_table_name)
        if self.single_dailies_df.empty:
            logger.error("[Dailies Cog] Error parsing single dailies data")
            raise TableDataImportException(table_name=self.single_dailies_table_name)

    def get_double_dailies(self) -> None:
        self.double_dailies_df = self.hunt_bot.pull_table_data(table_name=self.double_dailies_table_name)
        if self.double_dailies_df.empty:
            logger.error("[Dailies Cog] Error parsing double dailies data")
            raise TableDataImportException(table_name=self.double_dailies_table_name)

    @staticmethod
    def yield_next_row(df):
        for _, row in df.iterrows():
            yield row

    async def post_team_notif(self) -> None:
        """
        Sends a notification message to both team chat channels with a link to a newly posted daily.

        The message includes a direct URL to the daily message posted in the daily channel.
        It retrieves the appropriate team chat channels from the hunt_bot configuration and sends 
        the notification to both Team One and Team Two channels.
        """
        # Construct the link and message
        message_url = f"https://discord.com/channels/{self.hunt_bot.guild_id}/{self.daily_channel_id}/{self.message_id}"
        message = f"A new daily has just been posted! See it here: {message_url}"

        # Get team chat channels
        team_one_channel = self.bot.get_channel(self.hunt_bot.team_one_chat_channel)
        team_two_channel = self.bot.get_channel(self.hunt_bot.team_two_chat_channel)

        # Send message to each team channel with the link
        await team_one_channel.send(message)
        await team_two_channel.send(message)

    @tasks.loop(hours=1) 
    async def start_dailies(self):
        if not self.configured:
            logger.warning("[Dailies Cog] Cog not configured, skipping dailies.")
            return
        
        channel = self.bot.get_channel(self.daily_channel_id)
        if not channel:
            logger.error("[Dailies Cog] Dailies Channel not found.")
            return

        try:
            single_daily = next(self.single_daily_generator)
            single_task = single_daily["Task"]
            single_password = single_daily["Password"]
            self.hunt_bot.daily_password = single_password
            is_double = not pd.isna(single_daily.get("Double", None))

            await channel.send(dan_message)

            if not is_double:
                logger.info("[Dailies Cog] Serving single daily")
                self.message = single_daily_template.substitute(task=single_task, password=single_password)
            else:
                logger.info("[Dailies Cog] Serving double daily")
                double_daily = next(self.double_daily_generator)
                self.message = double_daily_template.substitute(
                    b1_task=single_task,
                    b1_password=single_password,
                    b2_task=double_daily["Task"]
                )

            if self.message_id:
                try:
                    old_message = await channel.fetch_message(self.message_id)
                    await old_message.unpin()
                except Exception as e:
                    logger.warning(f"[Dailies Cog] Failed to unpin old message: {e}")

            sent_message = await channel.send(self.message)
            self.message_id = sent_message.id
            await self.post_team_notif()
            await sent_message.pin()
        except StopIteration:
            logger.info("[Dailies Cog] No more dailies left. Stopping task")
            self.start_dailies.stop()

    @start_dailies.before_loop
    async def before_dailies(self):
        await self.bot.wait_until_ready()
        if self.daily_interval > 0:
            logger.info(f"[Dailies Cog] Dailies interval changed to: {self.daily_interval} hours" )
            self.start_dailies.change_interval(hours=self.daily_interval)
