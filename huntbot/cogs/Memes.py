from discord.ext import commands, tasks
from huntbot.HuntBot import HuntBot
from huntbot.exceptions import TableDataImportException, ConfigurationException
from huntbot import ConfigurationException, TableDataImportException
import logging

logger = logging.getLogger(__name__)

class MemesCog(commands.Cog):
    def __init__(self, bot: commands.Bot, hunt_bot: HuntBot):
        self.bot = bot
        self.hunt_bot = hunt_bot
        self.meme_channel_id = 0
        self.message_reactions = {}

        self.update_reaction_counts.start()

    def get_daily_channel(self):
        self.meme_channel_id = int(self.hunt_bot.config_map.get('MEME_CHANNEL_ID', "0"))
        if self.meme_channel_id == 0:
            logger.error("[Memes Cog] MEME_CHANNEL_ID not found")
            raise ConfigurationException(config_key='MEME_CHANNEL_ID')
        
    @commands.Cog.listener()
    async def on_message(self, message):
        # Only look in the meme channel after the hunt has started
        if message.channel.id != self.meme_channel_id:
            return
        if not self.hunt_bot.is_hunt_active():  # assume this method exists
            return
'''
Needs to look in the meme channel AFTER the hunt starts (load cog on start)
Look at the messages that come in
If they have a image or a video store that message ID in a dict as a new key and set the values to 0 as default
once per task loop, check all the message IDs in the list and count up the number of reactions on them and set the value as the updated count
testetset
'''