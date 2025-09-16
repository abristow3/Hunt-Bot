from discord.ext import commands, tasks
from discord import RawReactionActionEvent
import discord
from huntbot.HuntBot import HuntBot
from huntbot.exceptions import ConfigurationException
import logging
from string import Template

logger = logging.getLogger(__name__)

meme_scoreboard_message_template = Template("""
**Number $placement with $num_reactions reactions - <@$user_id>:**

$meme
""")

class MemesCog(commands.Cog):
    """
    A Discord Cog responsible for tracking and ranking meme submissions
    during an active hunt. Memes are ranked based on the number of reactions received.
    """
    
    def __init__(self, bot: commands.Bot, hunt_bot: HuntBot):
        """
        Initializes the MemesCog.

        Args:
            bot (commands.Bot): The Discord bot instance.
            hunt_bot (HuntBot): The HuntBot instance with hunt state and configuration.
        """
        
        self.bot = bot
        self.hunt_bot = hunt_bot
        self.meme_channel_id = 0
        self.message_reactions = {}

    async def cog_load(self) -> None:
        # Called when the cog is fully loaded and the bot is ready
        self.get_meme_channel()
        await self.initialize_meme_messages()

    async def cog_unload(self) -> None:
        """Called when the cog is unloaded."""
        logger.info("[Memes Cog] Unloading cog...")
        self.message_reactions.clear()
        self.meme_channel_id = 0

    def get_meme_channel(self) -> None:
        """
        Loads the meme channel ID from the configuration.
        Raises a ConfigurationException if not set properly.
        """
        self.meme_channel_id = int(self.hunt_bot.config_map.get('MEME_CHANNEL_ID', "0"))
        if self.meme_channel_id == 0:
            logger.error("[Memes Cog] MEME_CHANNEL_ID not found")
            raise ConfigurationException(config_key='MEME_CHANNEL_ID')
        
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Event listener triggered when a new message is posted.

        Args:
            message (discord.Message): The message object from Discord.
        """
        # Only look in the meme channel after the hunt has started
        # Not the meme channel so return
        if message.channel.id != self.meme_channel_id:
            return
        
        # Hunt hasn't started yet so ignore
        if not self.hunt_bot.started:
            return
        
        # The hunt has ended, so ignore
        # TODO possibly here where we put the logic to post the top ranking memes?
        if self.hunt_bot.ended:
            return
        
        # Made it to here the hunt has started, has not ended, and this is the correct text channel
        # First thing first, check if the message has an image, video, or gif attachment
        valid_attachments = self.validate_attachments(message=message)
        if not valid_attachments:
            logger.error("[Memes Cog] Invalid attachments types and extensions")
            return

            
        # We made it to here, so we have a message, with an image or video, posted after the hunt started, but before it ends, in the meme channel
        # now we need to capture the message ID and store it in memory to reference later when adding or removing reaction counts
        logger.info("[Memes Cog] New meme posted and added to memory")
        # Capture message ID and start count at 0
        self.message_reactions[message.id] = 0

        # And now this function is done so return
        return

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        """
        Event listener triggered when a message is deleted.

        Args:
            payload (discord.RawMessageDeleteEvent): Raw delete event data.
        """
        # Check if message deleted was in the memes channel
        if payload.channel_id != self.meme_channel_id:
            return

        logger.info("[Memes Cog] Message deleted, checking tracker in memory")

        # Check if message deleted was one we are currently tracking in memory, if so remove from tracking
        if payload.message_id in self.message_reactions:
            del self.message_reactions[payload.message_id]
            logger.info(f"[Memes Cog] Deleted message {payload.message_id} removed from tracking.")
        
        return

    # Task loop, or on reaction add and reaction remove? On an add increment by 1, on a remove decrement by 1, all need is message id, dont matter reaction type
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        """
        Event listener triggered when a reaction is added.

        Args:
            payload (RawReactionActionEvent): Raw reaction add event data.
        """
        # Check event occured in the meme channel
        if payload.channel_id != self.meme_channel_id:
            return
        
        # Check the message that got the reaction is one of the memes we are tracking, if not then return
        if payload.message_id not in self.message_reactions:
            return
        
        # Since it was, and this is a reaction add, we incriment the value for the message_id key by 1
        logger.info(f"[Memes Cog] Reaction added to meme {payload.message.id}, updating total")
        self.message_reactions[payload.message_id] += 1
        return

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent) -> None:
        """
        Event listener triggered when a reaction is removed.

        Args:
            payload (RawReactionActionEvent): Raw reaction remove event data.
        """
        # Check event occured in the meme channel
        if payload.channel_id != self.meme_channel_id:
            return
        
        # Check the message that got the reaction is one of the memes we are tracking, if not then return
        if payload.message_id not in self.message_reactions:
            return
        
        # Since it was, and this is a reaction add, we decriment the value for the message_id key by 1
        logger.info(f"[Memes Cog] Reaction removed from meme {payload.message.id}, updating total")
        if self.message_reactions[payload.message_id] > 0:
            self.message_reactions[payload.message_id] -= 1
        
        return
    
    def validate_attachments(self, message: discord.Message) -> bool:
        """
        Validates that a message has at least one valid image or video attachment.

        Args:
            message (discord.Message): The message to validate.

        Returns:
            bool: True if a valid attachment is found, False otherwise.
        """
        # If the message has no attachments, then there must be no meme, so ignore and return
        if not message.attachments:
            return False
        
        # Otherwise it does have attachments, so check if a video or iamge
        # Check each attachment and check if it is a video or image, if not then just return
        if not any(
            (att.content_type and (att.content_type.startswith("image/") or att.content_type.startswith("video/"))) or
            att.filename.lower().endswith((
                ".png", ".jpg", ".jpeg", ".gif", ".webp",
                ".mp4", ".mov", ".avi", ".webm", ".mkv"
            ))
            for att in message.attachments
        ):
            return False
        
        else:
            logger.info("[Memes Cog] Attachment is a valid")
            return True
    
    async def initialize_meme_messages(self) -> None:
        """
        On bot startup, initialize in-memory meme tracking by scanning messages
        in the meme channel posted after the hunt started.
        """
        # Method called on startup in case bot goes down mid hunt and we need to restart
        # Sorts through initial messages after start date and sums reactions, then adds in memory
        logger.info("[Starting Memes Cog]")
        await self.bot.wait_until_ready()

        # Get the actual TextChannel object from ID
        channel = self.bot.get_channel(self.meme_channel_id)
        if not isinstance(channel, discord.TextChannel):
            logger.error("[Memes Cog] Meme channel not found or invalid.")
            return

        # Only check messages that were posted after the hunt start date and time
        after_time = self.hunt_bot.start_datetime
        logger.info(f"[Memes Cog] Retrieving message history after {after_time}")

        # Loop through messages in the meme channel after the hunt start time
        async for message in channel.history(after=after_time, oldest_first=True, limit=None):
            if not self.validate_attachments(message):
                continue
            
            # Sum reactions on meme
            total_reactions = sum(reaction.count for reaction in message.reactions)

            # Update in memory
            self.message_reactions[message.id] = total_reactions
        
        logger.info(f"[Memes Cog] Initialized {len(self.message_reactions)} meme messages with reactions.")


    async def post_top_memes_scoreboard(self) -> None:
        """
        Posts the top 5 memes (based on reaction count) in the meme channel as a scoreboard.
        """
        # Get the meme channel object
        channel = self.bot.get_channel(self.meme_channel_id)
        if not isinstance(channel, discord.TextChannel):
            logger.error("[Memes Cog] Meme channel not found or invalid.")
            return
        
        logger.info("[Memes Cog] Generating top 5 memes messages...")

        # Sort messages by reactions count descending (highest shown first)
        top_memes = sorted(self.message_reactions.items(), key=lambda x: x[1], reverse=True)[:5]
        top_memes.reverse()
        if not top_memes:
            logger.info("[Memes Cog] No memes to post.")
            return
        
        place = 5
        # Since they are sorted like most to least, and we want to post them in order to the first place gets posted last so its newest to the user, we need to reverse the list and post
        for message_id, reaction_count in top_memes:
            # Try to get the message object
            try:
                # Get the message object and author
                message = await channel.fetch_message(message_id)
                user_id = message.author.id

                # Get the attachment from the message
                media_url = None
                for att in message.attachments:
                    if att.content_type and (att.content_type.startswith("image/") or att.content_type.startswith("video/")):
                        media_url = att.url
                        break
                    elif att.filename.lower().endswith((
                        ".png", ".jpg", ".jpeg", ".gif", ".webp",
                        ".mp4", ".mov", ".avi", ".webm", ".mkv"
                    )):
                        media_url = att.url
                        break
                if not media_url:
                    media_url = "(No media found)"
                
                # Template injection and send message
                formatted_message = meme_scoreboard_message_template.substitute(
                    placement=place,
                    num_reactions = reaction_count,
                    user_id=user_id,
                    meme=media_url
                )
                
                await channel.send(f"{formatted_message}\n---")

            except discord.NotFound:
                logger.warning(f"[Memes Cog] Could not fetch message {message_id} for top memes.")
                continue
            
            place -= 1
            