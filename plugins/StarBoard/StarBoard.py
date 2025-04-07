from discord.ext import commands, tasks
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


class StarBoard:
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot):
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.starboard_channel_id = 0
        self.team1_drop_channel_id = 0
        self.team2_drop_channel_id = 0
        self.configured = False

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

    async def on_raw_reaction_add(self, payload):
        # Check if the reaction is from one of the two channels we're monitoring
        if payload.channel_id in [self.team1_drop_channel_id, self.team2_drop_channel_id]:
            # Check if the emoji is the star emoji
            if str(payload.emoji) == "⭐":
                channel = self.bot.get_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)

                # Get the star channel
                star_channel = self.discord_bot.get_channel(self.starboard_channel_id)

                # Copy the message to the star channel
                await star_channel.send(f"Starred message from {channel.mention}: {message.content} (original message: {message.jump_url})")

    async def on_raw_reaction_remove(self, payload):
        # Check if the reaction was removed from one of the two channels we're monitoring
        if payload.channel_id in [self.team1_drop_channel_id, self.team2_drop_channel_id]:
            # Check if the emoji is the star emoji
            if str(payload.emoji) == "⭐":
                star_channel = self.discord_bot.get_channel(self.starboard_channel_id)

                # Try to find the message in the star channel that corresponds to the original one
                async for msg in star_channel.history(limit=1000):
                    if msg.content.endswith(str(payload.message_id)):  # match the original message ID
                        await msg.delete()  # Delete the starred message from the star channel
                        break