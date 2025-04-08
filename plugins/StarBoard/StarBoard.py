from discord.ext import commands
from HuntBot import HuntBot

class TableDataImportException(Exception):
    def __init__(self, message="Configuration error occurred", table_name=None):
        # Call the base class constructor with the message
        super().__init__(message)

        # Optionally store extra information, like the problematic config key
        self.config_key = table_name

    def __str__(self):
        # Customize the string representation of the exception
        if self.config_key:
            return f'{self.args[0]} (Config key: {self.config_key})'
        return self.args[0]


class ConfigurationException(Exception):
    """Exception raised for errors in the configuration."""

    def __init__(self, message="Configuration error occurred", config_key=None):
        # Call the base class constructor with the message
        super().__init__(message)

        # Optionally store extra information, like the problematic config key
        self.config_key = config_key

    def __str__(self):
        # Customize the string representation of the exception
        if self.config_key:
            return f'{self.args[0]} (Config key: {self.config_key})'
        return self.args[0]


class StarBoard(commands.Cog):
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot):
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.starboard_channel_id = 0
        self.team1_drop_channel_id = 0
        self.team2_drop_channel_id = 0
        self.configured = False
        self.starred_messages = {}

        self.startup()

    def startup(self):
        self.get_starboard_channel_id()
        self.get_team1_drop_channel_id()
        self.get_team2_drop_channel_id()
        self.configured = True

    def get_starboard_channel_id(self):
        self.starboard_channel_id = int(self.hunt_bot.config_map.get('STARBOARD_CHANNEL_ID', "0"))

        if self.starboard_channel_id == 0:
            raise ConfigurationException(config_key='STARBOARD_CHANNEL_ID')

    def get_team1_drop_channel_id(self):
        self.team1_drop_channel_id = int(self.hunt_bot.config_map.get('TEAM_1_DROP_CHANNEL_ID', "0"))

        if self.team1_drop_channel_id == 0:
            raise ConfigurationException(config_key='TEAM_1_DROP_CHANNEL_ID')

    def get_team2_drop_channel_id(self):
        self.team2_drop_channel_id = int(self.hunt_bot.config_map.get('TEAM_2_DROP_CHANNEL_ID', "0"))

        if self.team2_drop_channel_id == 0:
            raise ConfigurationException(config_key='TEAM_2_DROP_CHANNEL_ID')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # Check if the reaction is from one of the two channels we're monitoring
        if payload.channel_id in [self.team1_drop_channel_id, self.team2_drop_channel_id]:
            # Check if the emoji is the star emoji
            if str(payload.emoji) == "⭐":
                channel = self.discord_bot.get_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)

                # Check if the message already has a star reaction
                existing_star_reactions = [reaction for reaction in message.reactions if str(reaction.emoji) == "⭐"]

                if existing_star_reactions and existing_star_reactions[0].count > 0:
                    # If the message already has a star reaction, remove this new reaction
                    user = await self.discord_bot.get_user(payload.user_id)  # Get the user who reacted
                    await message.remove_reaction(payload.emoji, user)  # Remove their reaction
                    print(f"Removed duplicate star reaction from {user} on message {message.id}")
                    return  # Skip posting to starboard since it's already starred

                # Get the star channel
                star_channel = self.discord_bot.get_channel(self.starboard_channel_id)

                # Start constructing the message that will be sent to the star channel
                message_content = message.content

                # Check if there are any attachments (images, files, etc.)
                if message.attachments:
                    attachments = [attachment.url for attachment in message.attachments]
                    message_content += "\n" + "\n".join(attachments)

                # Send the message to the star channel
                sent_message = await star_channel.send(
                    f"Starred message from {channel.mention}: {message_content} (original message: {message.jump_url})"
                )

                # Store the relationship between the original message and the copied message in the star channel
                self.starred_messages[message.id] = sent_message.id

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.channel_id in [self.team1_drop_channel_id, self.team2_drop_channel_id]:
            if str(payload.emoji) == "⭐":
                # Check if the message is in the starred_messages dictionary
                original_message_id = payload.message_id
                if original_message_id in self.starred_messages:
                    # Get the ID of the starred message in the star channel
                    star_channel = self.discord_bot.get_channel(self.starboard_channel_id)
                    starred_message_id = self.starred_messages[original_message_id]

                    # Fetch the starred message and delete it
                    starred_message = await star_channel.fetch_message(starred_message_id)
                    await starred_message.delete()

                    # Remove the entry from the dictionary after deleting the message
                    del self.starred_messages[original_message_id]

                    print(
                        f"Deleted starred message with ID {starred_message_id} for original message ID {original_message_id}")

