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

                user = await self.discord_bot.fetch_user(payload.user_id)  # Fetch the user
                guild = self.discord_bot.get_guild(payload.guild_id)

                if guild is None:
                    print(f"Guild not found for user {user.name}.")
                    return

                # Get the member object from the guild (which contains role information)
                member = await guild.fetch_member(user.id)

                if member is None:
                    print(f"Member {user.id} not found in guild {guild.name}.")
                    return

                has_required_role = any(role.name.endswith('Team Leader') for role in member.roles) or \
                                    any(role.name == 'Staff' for role in member.roles)

                if not has_required_role:
                    reaction = payload.emoji
                    message = await guild.get_channel(payload.channel_id).fetch_message(payload.message_id)
                    await message.remove_reaction(reaction, user)
                    return

                # Check if the message already has a star reaction
                existing_star_reactions = [reaction for reaction in message.reactions if str(reaction.emoji) == "⭐"]

                if existing_star_reactions and existing_star_reactions[0].count > 1:
                    # If the message already has a star reaction, remove this new reaction
                    user = await self.discord_bot.fetch_user(payload.user_id)  # Fetch the user
                    await message.remove_reaction(payload.emoji, user)
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
            if str(payload.emoji) == "⭐":  # Only care about the star emoji
                channel = self.discord_bot.get_channel(payload.channel_id)
                original_message = await channel.fetch_message(payload.message_id)

                # Check the total count of `⭐` reactions on the original message
                star_reactions = [reaction for reaction in original_message.reactions if str(reaction.emoji) == "⭐"]

                if not star_reactions:  # If there are no `⭐` reactions left
                    # If no star reactions are left, delete the message from the starboard
                    if original_message.id in self.starred_messages:
                        starboard_message_id = self.starred_messages[original_message.id]
                        starboard_channel = self.discord_bot.get_channel(self.starboard_channel_id)
                        starboard_message = await starboard_channel.fetch_message(starboard_message_id)

                        # Delete the starboard message
                        await starboard_message.delete()

                        # Remove the mapping from the dictionary
                        del self.starred_messages[original_message.id]

                        print(
                            f"Deleted starred message with ID {starboard_message_id} for original message ID {original_message.id}")
