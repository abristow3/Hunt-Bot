import discord
from discord.ext import commands, tasks
from huntbot.HuntBot import HuntBot
import pandas as pd
from string import Template
from huntbot.exceptions import TableDataImportException, ConfigurationException
import logging

logger = logging.getLogger(__name__)

class ScoreCog(commands.Cog):
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot) -> None:
        ...