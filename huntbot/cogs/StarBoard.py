from discord.ext import commands
from discord import RawReactionActionEvent
from huntbot.HuntBot import HuntBot
from huntbot.exceptions import ConfigurationException
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

    async def cog_load(self) -> None:
        """Called when the cog is loaded."""
        logger.info("[Starboard Cog] Loading cog...")
        try:
            self.get_starboard_channel_id()
            self.get_team1_drop_channel_id()
            self.get_team2_drop_channel_id()
            self.configured = True
            logger.info("[Starboard Cog] Successfully configured.")
        except ConfigurationException as e:
            logger.error("[Starboard Cog] Configuration failed: %s", e)
            raise

    async def cog_unload(self) -> None:
        """Called when the cog is unloaded."""
        logger.info("[Starboard Cog] Unloading cog...")
        self.starred_messages.clear()
        self.configured = False

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
            logger.error("[Starboard Cog] No STARBOARD_CHANNEL_ID found.")
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
            logger.error("[Starboard Cog] No TEAM_1_DROP_CHANNEL_ID found.")
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
            logger.error("[Starboard Cog] No TEAM_2_DROP_CHANNEL_ID found.")
            raise ConfigurationException(config_key='TEAM_2_DROP_CHANNEL_ID')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        """
        Handles new ⭐ or 🤔 reactions. If the reacting user is authorized and it's the first reaction,
        the message is copied to the starboard.
        """
        if payload.channel_id not in [self.team1_drop_channel_id, self.team2_drop_channel_id]:
            return

        if str(payload.emoji) not in ["⭐", "🤔"]:
            return

        try:
            channel = self.discord_bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            user = await self.discord_bot.fetch_user(payload.user_id)
            guild = self.discord_bot.get_guild(payload.guild_id)

            if guild is None:
                logger.info("[Starboard Cog] Guild not found for user %s", user.name)
                return

            member = await guild.fetch_member(user.id)
            if member is None:
                logger.info("[Starboard Cog] Member %s not found in guild %s", user.id, guild.name)
                return

            # Check user role
            has_required_role = any(
                role.name.endswith('Team Leader') or role.name == 'Staff' or role.name == "Sheet helper"
                for role in member.roles
            )
            if not has_required_role:
                await message.remove_reaction(payload.emoji, member)
                logger.info("[Starboard Cog] User %s reaction removed due to missing roles", user.name)
                return

            # Check if already posted to starboard
            if message.id in self.starred_messages:
                await message.remove_reaction(payload.emoji, member)
                logger.info("[Starboard Cog] Duplicate reaction removed from user %s on message %s", user.name, message.id)
                return

            # Prepare message content
            message_content = message.content
            if message.attachments:
                attachments = "\n".join([attachment.url for attachment in message.attachments])
                message_content += f"\n{attachments}"

            # Send to starboard
            star_channel = self.discord_bot.get_channel(self.starboard_channel_id)
            if not star_channel:
                logger.error("[Starboard Cog] Starboard channel not found.")
                return

            if str(payload.emoji) == "⭐":
                sent = await star_channel.send(
                    f"⭐ Starred message from {channel.mention}:\n"
                    f"{message_content}\n"
                    f"[Jump to Message]({message.jump_url})"
                )
                logger.info("[Starboard Cog] Starred message %s sent to starboard", message.id)

            elif str(payload.emoji) == "🤔":
                sent = await star_channel.send(
                    f"🤔 Thinking message from {channel.mention}:\n"
                    f"{message_content}\n"
                    f"[Jump to Message]({message.jump_url})"
                )
                logger.info("[Starboard Cog] Thinking message %s sent to starboard", message.id)

            # Store reference
            self.starred_messages[message.id] = sent.id

        except Exception as e:
            logger.exception("[Starboard Cog] Error handling reaction add: %s", e)


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

        if str(payload.emoji) not in ["⭐", "🤔"]:
            return

        try:
            channel = self.discord_bot.get_channel(payload.channel_id)
            original_message = await channel.fetch_message(payload.message_id)

            star_reactions = [
                r for r in original_message.reactions
                if str(r.emoji) in ["⭐", "🤔"]
            ]
            
            if not star_reactions:
                starboard_msg_id = self.starred_messages.pop(original_message.id, None)
                if starboard_msg_id:
                    star_channel = self.discord_bot.get_channel(self.starboard_channel_id)
                    star_msg = await star_channel.fetch_message(starboard_msg_id)
                    await star_msg.delete()
                    logger.info(
                        "[Starboard Cog] Deleted starboard message %s for original message %s",
                        star_msg.id,
                        original_message.id
                    )

        except Exception as e:
            logger.exception("[Starboard Cog] Error handling reaction removal: %s", e)
