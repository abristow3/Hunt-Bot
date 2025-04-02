from string import Template
from discord.ext import commands, tasks
from HuntBot import HuntBot

begins_template = Template("""
@everyone The Hunt beings in $num_hours hours!
""")

ends_template = Template("""
@everyone The Hunt ends in $num_hours hours!
""")

class Countdown:
    def __init__(self,discord_bot: commands.Bot, hunt_bot: HuntBot):
        # Todo as we publish the message, divide these by 2
        self.countdown_interval = 24 # This interval i will be havled everytime a message is posted, then reset after it hits '1' back to 24
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.announcements_channel_id = 0

    def start_countdown(self):
        channel = self.discord_bot.get_channel(self.announcements_channel_id)

        # @tasks.loop(hours=self.interval)
        @tasks.loop(hours=self.bounty_interval)
        async def serve_bounty():
            await self.discord_bot.wait_until_ready()


            await channel.send(self.message)
