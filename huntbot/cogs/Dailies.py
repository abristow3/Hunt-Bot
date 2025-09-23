from discord.ext import commands, tasks
import pandas as pd
from string import Template
from huntbot.HuntBot import HuntBot
from huntbot.exceptions import TableDataImportException, ConfigurationException
import logging
import re
import discord

logger = logging.getLogger(__name__)

daily_complete_template = Template("""
$team_name Team $placement Place Daily!

$description                                                                      
""")

single_daily_template = Template("""
@everyone $task

Password: $password
""")

double_daily_template = Template("""
@everyone $b1_task

Password: $b1_password

@@@ DOUBLE DAILY @@@

$b2_task

""")

IMAGE_URL_PATTERN = re.compile(
    r"""(?ix)                              # Ignore case, verbose mode
    \b
    (https?://                             # Must start with http or https
        (?:                                # Supported/common image hosts
            (?:i\.)?imgur\.com |
            cdn\.discordapp\.com |
            media\.discordapp\.net |
            images\.unsplash\.com |
            gyazo\.com |
            \S+                            # Fallback: allow other domains
        )
        /[\w\-/\.%]+                       # Path
        \.(?:png|jpe?g|gif|webp|bmp|tiff)  # Image extension
        (?:\?\S*)?                         # Optional query params
    )
    \b
    """
)

class DailiesCog(commands.Cog):
    def __init__(self, bot: commands.Bot, hunt_bot: HuntBot):
        self.bot = bot
        self.hunt_bot = hunt_bot

        self.daily_channel_id = 0
        self.daily_interval = 24
        self.single_dailies_df = pd.DataFrame()
        self.double_dailies_df = pd.DataFrame()
        self.single_dailies_table_name = "Single Dailies"
        self.double_dailies_table_name = "Double Dailies"
        self.daily_description = ""
        self.message_id = 0
        self.configured = False
        self.embed_message = None

        self.single_daily_generator = None
        self.double_daily_generator = None
        self.first_place = ""
        self.second_place = ""

    async def cog_load(self) -> None:
        """Called when the cog is loaded and ready."""
        logger.info("[Dailies Cog] Loading cog and initializing.")
        try:
            self.get_daily_channel()
            self.get_single_dailies()
            self.get_double_dailies()

            self.single_daily_generator = self.yield_next_row(self.single_dailies_df)
            self.double_daily_generator = self.yield_next_row(self.double_dailies_df)
            self.configured = True
            self.start_dailies.start()
        except Exception as e:
            logger.error(f"[Dailies Cog] Initialization failed: {e}")
            self.configured = False

    async def cog_unload(self) -> None:
        """Called when the cog is unloaded to stop tasks."""
        logger.info("[Dailies Cog] Unloading cog.")
        if self.start_dailies.is_running():
            self.start_dailies.stop()

    def get_daily_channel(self) -> None:
        self.daily_channel_id = int(self.hunt_bot.config_map.get('DAILY_CHANNEL_ID', "0"))
        if self.daily_channel_id == 0:
            logger.error("[Dailies Cog] DAILY_CHANNEL_ID not found")
            raise ConfigurationException(config_key='DAILY_CHANNEL_ID')

    def get_single_dailies(self) -> None:
        self.single_dailies_df = self.hunt_bot.pull_table_data(table_name=self.single_dailies_table_name)
        if self.single_dailies_df.empty:
            logger.error("[Dailies Cog] Error parsing single dailies data")
            raise TableDataImportException(table_name=self.single_dailies_table_name)

    def get_double_dailies(self) -> None:
        self.double_dailies_df = self.hunt_bot.pull_table_data(table_name=self.double_dailies_table_name)
        if self.double_dailies_df.empty:
            logger.error("[Dailies Cog] Error parsing double dailies data")
            raise TableDataImportException(table_name=self.double_dailies_table_name)

    @staticmethod
    def yield_next_row(df):
        for _, row in df.iterrows():
            yield row

    async def post_team_notif(self) -> None:
        """
        Sends a notification message to both team chat channels with a link to a newly posted daily.

        The message includes a direct URL to the daily message posted in the daily channel.
        It retrieves the appropriate team chat channels from the hunt_bot configuration and sends 
        the notification to both Team One and Team Two channels.
        """
        # Construct the link and message
        message_url = f"https://discord.com/channels/{self.hunt_bot.guild_id}/{self.daily_channel_id}/{self.message_id}"
        message = f"A new daily has just been posted! See it here: {message_url}"

        # Get team chat channels
        team_one_channel = self.bot.get_channel(self.hunt_bot.team_one_chat_channel)
        team_two_channel = self.bot.get_channel(self.hunt_bot.team_two_chat_channel)

        # Send message to each team channel with the link
        if team_one_channel:
            await team_one_channel.send(message)
        if team_two_channel:
            await team_two_channel.send(message)

    @tasks.loop(hours=1) 
    async def start_dailies(self):
        if not self.configured:
            logger.warning("[Dailies Cog] Cog not configured, skipping dailies.")
            return
        
        channel = self.bot.get_channel(self.daily_channel_id)
        if not channel:
            logger.error("[Dailies Cog] Dailies Channel not found.")
            return

        # Reset first and second place 
        self.first_place = ""
        self.second_place = ""

        try:
            logger.info("[Dailies Cog] Attempting to serve daily")
            single_daily = next(self.single_daily_generator)
            single_task = single_daily["Task"]
            single_password = single_daily["Password"]
            self.hunt_bot.daily_password = single_password
            is_double = not pd.isna(single_daily.get("Double", None))

            if not is_double:
                logger.info("[Dailies Cog] Serving single daily")
                self.daily_description = single_daily_template.substitute(task=single_task, password=single_password)
            else:
                logger.info("[Dailies Cog] Serving double daily")
                double_daily = next(self.double_daily_generator)
                self.daily_description = double_daily_template.substitute(
                    b1_task=single_task,
                    b1_password=single_password,
                    b2_task=double_daily["Task"]
                )

            if self.embed_message:
                try:
                    await self.embed_message.unpin()
                except Exception as e:
                    logger.warning(f"[Dailies Cog] Failed to unpin old message: {e}")

            # Create the embed
            embed = self.create_embed_message()
            self.embed_message = await channel.send(embed=embed)
            self.message_id = self.embed_message.id
            await self.post_team_notif()
            await self.embed_message.pin()
        except StopIteration:
            logger.info("[Dailies Cog] No more dailies left. Stopping task")
            self.start_dailies.stop()

    @start_dailies.before_loop
    async def before_dailies(self):
        await self.bot.wait_until_ready()
        if self.daily_interval > 0:
            logger.info(f"[Dailies Cog] Dailies interval changed to: {self.daily_interval} hours" )
            self.start_dailies.change_interval(hours=self.daily_interval)

    def is_valid_image_url(self, url: str) -> bool:
        """Validates if a string is a valid image URL based on regex."""
        return bool(IMAGE_URL_PATTERN.fullmatch(url.strip()))

    def extract_image_urls(self, text: str) -> list:
        return IMAGE_URL_PATTERN.findall(text)

    def create_embed_message(self) -> discord.Embed:
        embed = discord.Embed(title="New Daily!", description=self.daily_description)
        image_urls = self.extract_image_urls(self.daily_description)
        
        if image_urls:
            embed.set_image(url=image_urls[0])
        
        return embed
    
    async def update_embed_description(self, new_desc: str) -> str:
        # Copy the original embed and update the description with the new one
        if self.embed_message and self.embed_message.embeds:
            updated_embed = self.embed_message.embeds[0]
            updated_embed.description = new_desc

            # Edit message
            await self.embed_message.edit(embed=updated_embed)
            logger.info("[Dailies Cog] Daily description update succesfully")
            response_message = "Daily description updated successfully."
            return response_message
        else:
            logger.warning("[Dailies Cog] No Daily Message in memory. Skipping.")
            response_message = "No Daily message found to update."
            return response_message

    async def update_embed_url(self, new_url: str) -> str:
        # Check we have a embed message in memory to update
        if not self.embed_message or not self.embed_message.embeds:
            logger.warning("[Dailies Cog] No Daily Message in memory. Skipping.")
            response_message = "No Daily message found to update."
            return response_message
        
        # Check new URL is accepted format
        if not self.is_valid_image_url(url=new_url):
            logger.info("[Dailies Cog] Invalid image URL provided")
            response_message = "Invalid image URL provided. Daily image not updated."
            return response_message
        
        updated_embed = self.embed_message.embeds[0] # First (and usually only) embed
        description = updated_embed.description or self.daily_description

        # Get old URL
        old_urls = self.extract_image_urls(description)
        
        if old_urls:
            old_url = old_urls[0]
            description = description.replace(old_url, new_url)
        else:
            # If no image URL is found, just append the new one
            description = f"{description.strip()}\n{new_url}".strip()

        # Replace old url in description with new URL and set new image url
        updated_embed.description = description
        updated_embed.set_image(url=new_url)

        # Edit message
        await self.embed_message.edit(embed=updated_embed)
        logger.info("[Dailies Cog] Image link updated successfully")
        response_message = "Image link updated succesfully."
        
        return response_message

    async def post_daily_complete_message(self, team_name: str, placement: str) -> None:
        channel = self.bot.get_channel(self.daily_channel_id)
        if not channel:
            logger.error("[Dailies Cog] Dailies Channel not found.")
            return
        
        try:
            clean_desc = self.daily_description.replace("@everyone ", "") 
            message = daily_complete_template.substitute(team_name=team_name, placement=placement, description=clean_desc)
            await channel.send(message)
        except Exception as e:
            logger.error("[Dailies Cog] Error when posting daily complete message", exc_info=e)
            return