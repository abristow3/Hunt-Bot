from discord.ext import commands, tasks
from huntbot.HuntBot import HuntBot
from huntbot.exceptions import TableDataImportException, ConfigurationException
import logging
import discord
from discord import app_commands
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Bounty:
    def __init__(self, item_name: str, reward_amount: float, time_limit_hours: int = 48):
        self.item_name = item_name
        self.reward_amount = reward_amount
        self.time_limit_hours = time_limit_hours
        self.active = True
        self.completed_by = ""
        self.start_time = datetime.utcnow()
        self.time_remaining = self.time_limit_hours

class TeamItemBountyCog(commands.Cog):
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot):
        self.bot = discord_bot
        self.hunt_bot = hunt_bot