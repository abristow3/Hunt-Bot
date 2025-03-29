from discord.ext import commands, tasks
from BotState import BotState
from gdoc import GDoc
import asyncio


class Bounties:
    def __init__(self, bot: commands.Bot, state: BotState, gdoc: GDoc):
        self.bot = bot
        self.state = state
        self.interval = state.bounty_tick
        self.gdoc = gdoc

        self.start_bounties()

    def start_bounties(self):
        # @tasks.loop(hours=self.interval)
        @tasks.loop(seconds=self.interval)
        async def serve_bounty():
            channel = self.bot.get_channel(self.state.bounty_channel_id)
            await self.bot.wait_until_ready()
            while not self.bot.is_closed():
                for bounty in self.gdoc.bounties_list:
                    await channel.send("=== BOUNTY SERVED ===")
                    await channel.send(bounty)
                    await asyncio.sleep(5)

        # Start the task
        serve_bounty.start()
