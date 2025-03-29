from discord.ext import commands, tasks
from BotState import BotState
from gdoc import GDoc
import asyncio


class Dailies:
    def __init__(self, bot: commands.Bot, state: BotState, gdoc: GDoc):
        self.bot = bot
        self.state = state
        self.interval = 24
        self.gdoc = gdoc

        self.start_dailies()

    def start_dailies(self):
        # Define the loop with the interval specified in the instance variable
        # @tasks.loop(hours=self.interval)
        @tasks.loop(seconds=self.interval)
        async def serve_daily():
            channel = self.bot.get_channel(self.state.daily_channel_id)
            await self.bot.wait_until_ready()
            while not self.bot.is_closed():
                for daily in self.gdoc.dailies_list:
                    await channel.send("=== DAILY SERVED ===")
                    await channel.send(daily)
                    await asyncio.sleep(7)

        print("BEFORE DAILY START")
        # Start the task
        serve_daily.start()
