import discord
from discord.ext import commands, tasks
from huntbot.HuntBot import HuntBot
import logging

logger = logging.getLogger(__name__)


class WebhookCleanupCog(commands.Cog):
    """
    A cog that cleans up any webhooks leftover from the Hunt event that just ended.
    """

    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot) -> None:
        """
        Initialize the WebhookCleanupCog with necessary discord bot and huntbot instances.

        Args:
            discord_bot (commands.Bot): The instance of the Discord bot.
            hunt_bot (HuntBot): The instance of the HuntBot containing game data.

        Returns:
            None
        """
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot

    async def cog_load(self) -> None:
        """Runs when the cog is loaded and bot is ready."""
        logger.info("[WebhookCleanup Cog] Loading WebhookCleanup Cog.")

        # Start loops
        self.start_webhook_cleanup.start()

    async def cog_unload(self) -> None:
        """Cleans up background tasks on cog unload."""
        logger.info("[WebhookCleanup Cog] Unloading WebhookCleanup Cog.")
        if self.start_webhook_cleanup.is_running():
            self.start_webhook_cleanup.stop()

    @staticmethod
    async def delete_webhooks(webhooks: list) -> None:
        """
        Asynchronously deletes the webhooks in the webhook list

        Returns:
            None
        """
        for webhook in webhooks:
            await webhook.delete(reason=f"Cleared by Hunt Bot")

    @tasks.loop(seconds=10)
    async def start_webhook_cleanup(self) -> None:
        """
        Asynchronously deletes any channel webhooks once the Hunt event has ended

        Returns:
            None
        """
        if self.hunt_bot.ended:
            # get list of channels
            try:
                # get list of channels, check if TextChannel, check if has webhooks, delete if so
                for channel in self.discord_bot.get_all_channels():
                    if isinstance(channel, discord.TextChannel):
                        webhooks = await channel.webhooks()

                        if webhooks:
                            await self.delete_webhooks(webhooks=webhooks)

            except Exception as e:
                logger.error(msg="[WebhookCleanup Cog] Error when deleting webhooks", exc_info=e)

    @start_webhook_cleanup.before_loop
    async def before_start_webhook_cleanup(self) -> None:
        """
        Runs before the start_webhook_cleanup loop starts. Ensures the bot is ready before starting.

        Returns:
            None
        """
        await self.discord_bot.wait_until_ready()
