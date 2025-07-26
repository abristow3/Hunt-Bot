from discord.ext import commands
from discord import RawReactionActionEvent, Message
from huntbot.HuntBot import HuntBot
from huntbot.exceptions import TableDataImportException, ConfigurationException
import logging

logger = logging.getLogger(__name__)


class StarBoardCog(commands.Cog):
    """Cog for managing a starboard that mirrors starred messages from specific channels."""

    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot):
        """
        Initializes the StarBoardCog.

        Args:
            discord_bot (commands.Bot): The main Discord bot instance.
            hunt_bot (HuntBot): The HuntBot instance providing config and data access.
        """
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.starboard_channel_id: int = 0
        self.team1_drop_channel_id: int = 0
        self.team2_drop_channel_id: int = 0
        self.configured: bool = False
        self.starred_messages: dict[int, int] = {}

        self.startup()

    def startup(self) -> None:
        """
        Loads and validates channel configuration from the HuntBot config map.

        Returns:
            None
        """
        self.get_starboard_channel_id()
        self.get_team1_drop_channel_id()
        self.get_team2_drop_channel_id()
        self.configured = True

    def get_starboard_channel_id(self) -> None:
        """
        Retrieves the starboard channel ID from the config.

        Raises:
            ConfigurationException: If STARBOARD_CHANNEL_ID is not set or invalid.

        Returns:
            None
        """
        self.starboard_channel_id = int(self.hunt_bot.config_map.get('STARBOARD_CHANNEL_ID', "0"))
        if self.starboard_channel_id == 0:
            raise ConfigurationException(config_key='STARBOARD_CHANNEL_ID')

    def get_team1_drop_channel_id(self) -> None:
        """
        Retrieves Team 1's drop channel ID from the config.

        Raises:
            ConfigurationException: If TEAM_1_DROP_CHANNEL_ID is not set or invalid.

        Returns:
            None
        """
        self.team1_drop_channel_id = int(self.hunt_bot.config_map.get('TEAM_1_DROP_CHANNEL_ID', "0"))
        if self.team1_drop_channel_id == 0:
            raise ConfigurationException(config_key='TEAM_1_DROP_CHANNEL_ID')

    def get_team2_drop_channel_id(self) -> None:
        """
        Retrieves Team 2's drop channel ID from the config.

        Raises:
            ConfigurationException: If TEAM_2_DROP_CHANNEL_ID is not set or invalid.

        Returns:
            None
        """
        self.team2_drop_channel_id = int(self.hunt_bot.config_map.get('TEAM_2_DROP_CHANNEL_ID', "0"))
        if self.team2_drop_channel_id == 0:
            raise ConfigurationException(config_key='TEAM_2_DROP_CHANNEL_ID')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        """
        Handles new ⭐ reactions. If the reacting user is authorized and it's the first reaction,
        the message is copied to the starboard.

        Args:
            payload (RawReactionActionEvent): Discord event payload for reaction added.

        Returns:
            None
        """
        if payload.channel_id not in [self.team1_drop_channel_id, self.team2_drop_channel_id]:
            return

        if str(payload.emoji) != "⭐":
            return

        try:
            channel = self.discord_bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            user = await self.discord_bot.fetch_user(payload.user_id)
            guild = self.discord_bot.get_guild(payload.guild_id)

            if guild is None:
                logger.warning("Guild not found for user %s", user.name)
                return

            member = await guild.fetch_member(user.id)
            if member is None:
                logger.warning("Member %s not found in guild %s", user.id, guild.name)
                return

            has_required_role = any(
                role.name.endswith('Team Leader') or role.name == 'Staff' for role in member.roles
            )
            if not has_required_role:
                await message.remove_reaction(payload.emoji, member)
                logger.info("User %s removed star due to missing roles", user.name)
                return

            if any(r for r in message.reactions if str(r.emoji) == "⭐" and r.count > 1):
                await message.remove_reaction(payload.emoji, member)
                logger.info("Duplicate star reaction removed from user %s on message %s", user.name, message.id)
                return

            star_channel = self.discord_bot.get_channel(self.starboard_channel_id)
            if not star_channel:
                logger.warning("Starboard channel not found.")
                return

            message_content = message.content
            if message.attachments:
                attachments = "\n".join([attachment.url for attachment in message.attachments])
                message_content += f"\n{attachments}"

            sent = await star_channel.send(
                f"⭐ Starred message from {channel.mention}:\n"
                f"{message_content}\n"
                f"[Jump to Message]({message.jump_url})"
            )
            self.starred_messages[message.id] = sent.id
            logger.info("Starred message %s sent to starboard", message.id)

        except Exception as e:
            logger.exception("Error handling star reaction: %s", e)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent) -> None:
        """
        Handles removal of ⭐ reactions. If none remain, the message is removed from the starboard.

        Args:
            payload (RawReactionActionEvent): Discord event payload for reaction removed.

        Returns:
            None
        """
        if payload.channel_id not in [self.team1_drop_channel_id, self.team2_drop_channel_id]:
            return

        if str(payload.emoji) != "⭐":
            return

        try:
            channel = self.discord_bot.get_channel(payload.channel_id)
            original_message = await channel.fetch_message(payload.message_id)

            star_reactions = [
                r for r in original_message.reactions if str(r.emoji) == "⭐"
            ]
            if not star_reactions:
                starboard_msg_id = self.starred_messages.pop(original_message.id, None)
                if starboard_msg_id:
                    star_channel = self.discord_bot.get_channel(self.starboard_channel_id)
                    star_msg = await star_channel.fetch_message(starboard_msg_id)
                    await star_msg.delete()
                    logger.info(
                        "Deleted starboard message %s for original message %s",
                        star_msg.id,
                        original_message.id
                    )

        except Exception as e:
            logger.exception("Error handling reaction removal: %s", e)
