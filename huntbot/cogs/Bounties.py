from discord.ext import commands, tasks
import pandas as pd
from string import Template
from huntbot.HuntBot import HuntBot
from huntbot.exceptions import TableDataImportException, ConfigurationException
import logging
import re
import discord

logger = logging.getLogger(__name__)

bounty_complete_template = Template("""
$team_name Team $placement Place Bounty!

$description                                                                      
""")

single_bounty_template = Template("""                                                           
@everyone $task

Password: $password
""")

double_bounty_template = Template("""                             
@everyone $b1_task

Password: $b1_password

@@@ DOUBLE BOUNTY @@@

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

class BountiesCog(commands.Cog):
    def __init__(self, bot: commands.Bot, hunt_bot: HuntBot):
        self.bot = bot
        self.hunt_bot = hunt_bot

        self.bounties_per_day = 0
        self.bounty_channel_id = 0
        self.bounty_interval = 0
        self.single_bounties_df = pd.DataFrame()
        self.double_bounties_df = pd.DataFrame()
        self.single_bounties_table_name = "Single Bounties"
        self.double_bounties_table_name = "Double Bounties"
        self.bounty_description = ""
        self.message_id = 0
        self.configured = False
        self.embed_message = None

        self.single_bounty_generator = None
        self.double_bounty_generator = None
        self.first_place = ""
        self.second_place = ""

    async def cog_load(self):
        logger.info("[Bounties Cog] Loading cog and initializing.")
        try:
            logger.info("[Bounties Cog] Retrieving Bounties data from GDoc config map")
            self.get_bounties_per_day()
            self.set_bounty_interval()
            self.get_bounty_channel()
            self.get_single_bounties()
            self.get_double_bounties()

            self.single_bounty_generator = self.yield_next_row(self.single_bounties_df)
            self.double_bounty_generator = self.yield_next_row(self.double_bounties_df)
            self.configured = True
            self.start_bounties.start()
        except Exception as e:
            logger.error(f"[Bounties Cog] Initialization failed: {e}")
            self.configured = False

    async def cog_unload(self):
        logger.info("[Bounties Cog] Unloading cog.")
        if self.start_bounties.is_running():
            self.start_bounties.stop()

    def get_bounties_per_day(self):
        self.bounties_per_day = int(self.hunt_bot.config_map.get('BOUNTIES_PER_DAY', "0"))
        if self.bounties_per_day == 0:
            logger.error("[Bounties Cog] No BOUNTIES_PER_DAY data found in config")
            raise ConfigurationException(config_key='BOUNTIES_PER_DAY')

    def set_bounty_interval(self):
        self.bounty_interval = 24 / self.bounties_per_day
        logger.info(f"[Bounties Cog] Bounties interval set to {self.bounty_interval}")

    def get_bounty_channel(self):
        self.bounty_channel_id = int(self.hunt_bot.config_map.get('BOUNTY_CHANNEL_ID', "0"))
        if self.bounty_channel_id == 0:
            logger.error("[Bounties Cog] No BOUNTY_CHANNEL_ID data found in config")
            raise ConfigurationException(config_key='BOUNTY_CHANNEL_ID')

    def get_single_bounties(self):
        self.single_bounties_df = self.hunt_bot.pull_table_data(table_name=self.single_bounties_table_name)
        if self.single_bounties_df.empty:
            logger.error("[Bounties Cog] Error parsing single bounties from config map")
            raise TableDataImportException(table_name=self.single_bounties_table_name)

    def get_double_bounties(self):
        self.double_bounties_df = self.hunt_bot.pull_table_data(table_name=self.double_bounties_table_name)
        if self.double_bounties_df.empty:
            logger.error("[Bounties Cog] Error parsing double bounties from config map")
            raise TableDataImportException(table_name=self.double_bounties_table_name)

    @staticmethod
    def yield_next_row(df):
        for _, row in df.iterrows():
            yield row

    async def post_team_notif(self) -> None:
        """
        Sends a notification message to both team chat channels with a link to a newly posted bounty.

        The message includes a direct URL to the bounty message posted in the bounty channel.
        It retrieves the appropriate team chat channels from the hunt_bot configuration and sends 
        the notification to both Team One and Team Two channels.
        """
        # Construct the link and message
        message_url = f"https://discord.com/channels/{self.hunt_bot.guild_id}/{self.bounty_channel_id}/{self.message_id}"
        message = f"A new bounty has just been posted! See it here: {message_url}"

        # Get team chat channels
        team_one_channel = self.bot.get_channel(self.hunt_bot.team_one_chat_channel_id)
        team_two_channel = self.bot.get_channel(self.hunt_bot.team_two_chat_channel_id)

        # Send message to each team channel with the link
        if team_one_channel:
            await team_one_channel.send(message)
        if team_two_channel:
            await team_two_channel.send(message)


    @tasks.loop(hours=6)  # Will override this interval after init
    async def start_bounties(self):
        if not self.configured:
            logger.warning("[Bounties Cog] Cog not configured, skipping bounties.")
            return

        channel = self.bot.get_channel(self.bounty_channel_id)
        if not channel:
            logger.error("[Bounties Cog] Bounties Channel not found.")
            return

        # Reset first and second place 
        self.first_place = ""
        self.second_place = ""

        try:
            logger.info("[Bounties Cog] Attempting to serve bounty")
            counter_cog = self.bot.get_cog("TotalItemCounterCog")
            is_total = False

            # If process is still running, go ahead and end it before next continuing
            if counter_cog.active:
                logger.info("[Bounties Cog] Total drop challenge over. Stopping TotalItemCounter Cog.")
                await counter_cog.stop_counter()

            single_bounty = next(self.single_bounty_generator)
            single_task = single_bounty["Task"]
            single_password = single_bounty["Password"]
            self.hunt_bot.bounty_password = single_password
            is_double = not pd.isna(single_bounty.get("Double", None))
            is_total = not pd.isna(single_bounty.get("Total Drop", None))

            if not is_double:
                logger.info("[Bounties Cog] Bounty is a single bounty")
                self.bounty_description = single_bounty_template.substitute(task=single_task, password=single_password)
            else:
                logger.info("[Bounties Cog] Bounty is a double bounty")
                double_bounty = next(self.double_bounty_generator)

                # Assumes there will never be two total drop challenges for a double
                if not is_total:
                    is_total = not pd.isna(double_bounty.get("Total Drop", None))

                self.bounty_description = double_bounty_template.substitute(
                    b1_task=single_task,
                    b1_password=single_password,
                    b2_task=double_bounty["Task"]
                )

            # Unpin the old message
            if self.embed_message:
                try:
                    await self.embed_message.unpin()
                except Exception as e:
                    logger.warning(f"[Bounties Cog] Failed to unpin old message: {e}")

            # Create the embed
            embed = self.create_embed_message()
            self.embed_message = await channel.send(embed=embed)
            self.message_id = self.embed_message.id
            await self.post_team_notif()
            await self.embed_message.pin()

            if is_total:
                logger.info("[Bounties Cog] Total drop challenge detected. Starting TotalItemCounter Cog.")
                # There is a total item challenge, so we start the couner cog process
                await counter_cog.start_counter(start_msg_id=self.message_id, drop_channel_id=self.bounty_channel_id)

        except StopIteration:
            logger.info("[Bounties Cog] No more bounties left. Stopping task.")
            self.start_bounties.stop()

    @start_bounties.before_loop
    async def before_bounties(self):
        await self.bot.wait_until_ready()
        if self.bounty_interval > 0:
            logger.info(f"[Bounties Cog] Updating Bounties task interval to: {self.bounty_interval} hours")
            self.start_bounties.change_interval(hours=self.bounty_interval)

    def is_valid_image_url(self, url: str) -> bool:
        """Validates if a string is a valid image URL based on regex."""
        return bool(IMAGE_URL_PATTERN.fullmatch(url.strip()))

    def extract_image_urls(self, text: str) -> list:
        return IMAGE_URL_PATTERN.findall(text)
    
    def create_embed_message(self) -> discord.Embed:
        embed = discord.Embed(title="New Bounty!", description=self.bounty_description)
        image_urls = self.extract_image_urls(self.bounty_description)
        
        if image_urls:
            embed.set_image(url=image_urls[0])
        
        return embed
    
    async def update_embed_url(self, new_url: str) -> str:
        # Check we have a embed message in memory to update
        if not self.embed_message or not self.embed_message.embeds:
            logger.warning("[Bounties Cog] No Bounty Message in memory. Skipping.")
            response_message = "No bounty message found to update."
            return response_message
        
        # Check new URL is accepted format
        if not self.is_valid_image_url(url=new_url):
            logger.info("[Bounties Cog] Invalid image URL provided")
            response_message = "Invalid image URL provided. Bounty image not updated."
            return response_message
        
        updated_embed = self.embed_message.embeds[0] # First (and usually only) embed
        description = updated_embed.description or self.bounty_description

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
        logger.info("[Bounties Cog] Image link updated successfully")
        response_message = "Image link updated succesfully."
        
        return response_message

    async def update_embed_description(self, new_desc: str) -> str:
        # Copy the original embed and update the description with the new one
        if self.embed_message and self.embed_message.embeds:
            updated_embed = self.embed_message.embeds[0]
            updated_embed.description = new_desc

            # Edit message
            await self.embed_message.edit(embed=updated_embed)
            logger.info("[Bounties Cog] Bounty description update succesfully")
            response_message = "Bounty description updated successfully."
            return response_message
        else:
            logger.warning("[Bounties Cog] No Bounty Message in memory. Skipping.")
            response_message = "No bounty message found to update."
            return response_message

    async def post_bounty_complete_message(self, team_name: str, placement: str) -> None:
        channel = self.bot.get_channel(self.bounty_channel_id)
        if not channel:
            logger.error("[Bounties Cog] Bounties Channel not found.")
            return
        
        try:
            clean_desc = self.bounty_description.replace("@everyone ", "") 
            message = bounty_complete_template.substitute(team_name=team_name, placement=placement, description=clean_desc)
            await channel.send(message)
        except Exception as e:
            logger.error("[Bounties Cog] Error when posting bounty complete message", exc_info=e)
            return
