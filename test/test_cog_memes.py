import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from discord.ext import commands
import discord
from huntbot.exceptions import ConfigurationException
from huntbot.HuntBot import HuntBot
from huntbot.cogs.Memes import MemesCog

...