from discord.ext import commands, tasks
import pandas as pd
from string import Template
from huntbot.HuntBot import HuntBot
from huntbot.exceptions import TableDataImportException, ConfigurationException

single_bounty_template = Template("""
@everyone $task

Password: $password
""")

double_bounty_template = Template("""
@everyone $b1_task

Password: $b1_password

@@@ DOUBLE BOUNTY @@@

$b2_task
                                  
Password: $b2_password
""")


class BountiesCog(commands.Cog):
    def __init__(self, bot: commands.Bot, hunt_bot: HuntBot):
        self.bot = bot
        self.hunt_bot = hunt_bot

        self.bounties_per_day = 0
        self.bounty_channel_id = 0
        self.bounty_interval = 0
        self.single_bounties_df = pd.DataFrame()
        self.double_bounties_df = pd.DataFrame()
        self.single_bounties_table_name = "Single Bounties"
        self.double_bounties_table_name = "Double Bounties"
        self.message = ""
        self.message_id = 0
        self.configured = False

        self.single_bounty_generator = None
        self.double_bounty_generator = None

        self.bot.loop.create_task(self.initialize())

    async def initialize(self):
        try:
            self.start_up()
            self.configured = True
            self.start_bounties.start()
        except Exception as e:
            print(f"[Bounties] Initialization failed: {e}")
            self.configured = False

    def start_up(self):
        self.get_bounties_per_day()
        self.set_bounty_interval()
        self.get_bounty_channel()
        self.get_single_bounties()
        self.get_double_bounties()

        self.single_bounty_generator = self.yield_next_row(self.single_bounties_df)
        self.double_bounty_generator = self.yield_next_row(self.double_bounties_df)

    def get_bounties_per_day(self):
        self.bounties_per_day = int(self.hunt_bot.config_map.get('BOUNTIES_PER_DAY', "0"))
        if self.bounties_per_day == 0:
            raise ConfigurationException(config_key='BOUNTIES_PER_DAY')

    def set_bounty_interval(self):
        self.bounty_interval = 24 / self.bounties_per_day

    def get_bounty_channel(self):
        self.bounty_channel_id = int(self.hunt_bot.config_map.get('BOUNTY_CHANNEL_ID', "0"))
        if self.bounty_channel_id == 0:
            raise ConfigurationException(config_key='BOUNTY_CHANNEL_ID')

    def get_single_bounties(self):
        self.single_bounties_df = self.hunt_bot.pull_table_data(table_name=self.single_bounties_table_name)
        if self.single_bounties_df.empty:
            raise TableDataImportException(table_name=self.single_bounties_table_name)

    def get_double_bounties(self):
        self.double_bounties_df = self.hunt_bot.pull_table_data(table_name=self.double_bounties_table_name)
        if self.double_bounties_df.empty:
            raise TableDataImportException(table_name=self.double_bounties_table_name)

    @staticmethod
    def yield_next_row(df):
        for _, row in df.iterrows():
            yield row

    @tasks.loop(hours=1)  # Will override this interval after init
    async def start_bounties(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(self.bounty_channel_id)
        if not channel:
            print("[Bounties] Channel not found.")
            return

        try:
            single_bounty = next(self.single_bounty_generator)
            single_task = single_bounty["Task"]
            single_password = single_bounty["Password"]
            is_double = not pd.isna(single_bounty.get("Double", None))

            if not is_double:
                self.message = single_bounty_template.substitute(task=single_task, password=single_password)
            else:
                double_bounty = next(self.double_bounty_generator)
                self.message = double_bounty_template.substitute(
                    b1_task=single_task,
                    b1_password=single_password,
                    b2_task=double_bounty["Task"],
                    b2_password=double_bounty["Password"]
                )

            if self.message_id:
                old_message = await channel.fetch_message(self.message_id)
                await old_message.unpin()

            sent_message = await channel.send(self.message)
            self.message_id = sent_message.id
            await sent_message.pin()
        except StopIteration:
            print("[Bounties] No more bounties left. Stopping task.")
            self.start_bounties.stop()

    @start_bounties.before_loop
    async def before_bounties(self):
        await self.bot.wait_until_ready()
        if self.bounty_interval > 0:
            self.start_bounties.change_interval(hours=self.bounty_interval)
