from discord.ext import commands, tasks
import pandas as pd
from string import Template
from huntbot.HuntBot import HuntBot
from huntbot import ConfigurationException, TableDataImportException

single_daily_template = Template("""
@everyone $task

Password: $password
""")

double_daily_template = Template("""
@everyone $b1_task

Password: $b1_password

@@@ DOUBLE DAILY @@@

$b2_task

Password: $b2_password
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

        self.bot.loop.create_task(self.initialize())

    async def initialize(self):
        try:
            self.start_up()
            self.configured = True
            self.start_dailies.start()
        except Exception as e:
            print(f"[Dailies] Initialization failed: {e}")
            self.configured = False

    def start_up(self):
        self.get_daily_channel()
        self.get_single_dailies()
        self.get_double_dailies()

        self.single_daily_generator = self.yield_next_row(self.single_dailies_df)
        self.double_daily_generator = self.yield_next_row(self.double_dailies_df)

    def get_daily_channel(self):
        self.daily_channel_id = int(self.hunt_bot.config_map.get('DAILY_CHANNEL_ID', "0"))
        if self.daily_channel_id == 0:
            logger.error("[Dailies Cog] DAILY_CHANNEL_ID not found")
            raise ConfigurationException(config_key='DAILY_CHANNEL_ID')

    def get_single_dailies(self):
        self.single_dailies_df = self.hunt_bot.pull_table_data(table_name=self.single_dailies_table_name)
        if self.single_dailies_df.empty:
            logger.error("[Dailies Cog] Error parsing single dailies data")
            raise TableDataImportException(table_name=self.single_dailies_table_name)

    def get_double_dailies(self):
        self.double_dailies_df = self.hunt_bot.pull_table_data(table_name=self.double_dailies_table_name)
        if self.double_dailies_df.empty:
            logger.error("[Dailies Cog] Error parsing double dailies data")
            raise TableDataImportException(table_name=self.double_dailies_table_name)

    @staticmethod
    def yield_next_row(df):
        for _, row in df.iterrows():
            yield row

    @tasks.loop(hours=1)  # overridden after init
    async def start_dailies(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(self.daily_channel_id)
        if not channel:
            logger.error("[Dailies Cog] Dailies Channel not found.")
            return

        try:
            single_daily = next(self.single_daily_generator)
            single_task = single_daily["Task"]
            single_password = single_daily["Password"]
            is_double = not pd.isna(single_daily.get("Double", None))

            if not is_double:
                logger.info("[Dailies Cog] Serving single daily")
                self.message = single_daily_template.substitute(task=single_task, password=single_password)
            else:
                logger.info("[Dailies Cog] Serving double daily")
                double_daily = next(self.double_daily_generator)
                self.message = double_daily_template.substitute(
                    b1_task=single_task,
                    b1_password=single_password,
                    b2_task=double_daily["Task"],
                    b2_password=double_daily["Password"]
                )

            if self.message_id:
                old_message = await channel.fetch_message(self.message_id)
                await old_message.unpin()

            sent_message = await channel.send(self.message)
            self.message_id = sent_message.id
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
