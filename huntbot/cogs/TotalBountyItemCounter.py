from huntbot.HuntBot import HuntBot
import logging
from discord.ext import commands, tasks
from string import Template
import discord

logger = logging.getLogger(__name__)

counting_complete_template = Template("""
Hands off your keyboards!!! 
The challenge has ended and no further submissions will be accepted!

Final Tally:
$firstplace_team_name has won with $firstplace_total items!
$secondplace_team_name has come in second with $secondplace_total items!
A total of $total_items items were acquired for this challenge!                                                                    
""")

sticky_msg_template = Template("""
$team_one_name team: $team_one_total items
$team_two_name team: $team_two_total items
$leading_team_name leads with $leading_team_total items!     
The last valid drop counted for the challenge is here: $message_url                                                           
""")


class TotalBountyItemCounterCog(commands.Cog):
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot):
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.start_msg_id = 0
        self.sticky_msg_id = 0
        self.sticky_message_string = ""
        self.drop_channel_id = 0
        self.active = False
        self.total_items = 0
        self.winning_team_name = ""
        self.losing_team_name = ""
        self.counting_complete_msg_str = ""
        self.message_list: list[discord.Message] = []
        self.last_valid_drop_msg_id = 0
        # Emoji identifiers
        self.valid_submission_emoji = "✅"
        self.invalid_submission_emoji = "❌"
        self.total_item_emoji = "⬆️"
        self.team_totals = {}

    async def cog_load(self) -> None:
        logger.info("[TotalBountyItemCounter Cog] Loading cog and initializing.")
        try:
            self.count_items.start()
        except Exception as e:
            logger.error(f"[TotalBountyItemCounter Cog] Initialization failed: {e}")

    async def cog_unload(self) -> None:
        logger.info("[TotalBountyItemCounter Cog] Unloading cog.")
        if self.count_items.is_running():
            self.count_items.stop()

    def update_drop_channel_id(self, channel_id: int) -> None:
        self.drop_channel_id = channel_id

    def update_start_msg_id(self, msg_id: int) -> None:
        self.start_msg_id = msg_id

    async def get_messages_from_channel(self) -> None:
        drop_channel = self.discord_bot.get_channel(self.drop_channel_id)
        if drop_channel is None:
            logger.warning("[Counter] Drop channel not found!")
            return

        self.message_list = []
        async for m in drop_channel.history(after=discord.Object(id=self.start_msg_id), limit=100):
            self.message_list.append(m)

        logger.debug(f"[Counter] Retrieved {len(self.message_list)} messages from channel.")

    async def recalc_totals(self) -> None:
        """
        Recalculate totals from scratch based on current messages.
        Only messages with both ✅ (valid) and ⬆️ (total) are counted.
        ❌ invalidates a message.
        """
        self.team_totals = {self.hunt_bot.team_one_name: 0, self.hunt_bot.team_two_name: 0}
        self.total_items = 0
        self.last_valid_drop_msg_id = 0

        guild = self.discord_bot.get_guild(self.hunt_bot.guild_id)
        if not guild:
            logger.warning("[Counter] Guild not found, cannot recalc totals.")
            return

        for msg in self.message_list:
            if msg.author.id == self.discord_bot.user.id:
                continue  # skip bot messages

            emojis = [str(r.emoji) for r in msg.reactions]

            # Skip if invalid
            if self.invalid_submission_emoji in emojis:
                continue

            # Only count if both valid and total emojis are present
            if self.valid_submission_emoji in emojis and self.total_item_emoji in emojis:
                author = msg.author
                member = author
                if isinstance(author, discord.User):
                    try:
                        member = await guild.fetch_member(author.id)
                    except discord.NotFound:
                        continue

                # Allocate point based on team roles
                for role in member.roles:
                    role_name = role.name.lower()
                    if self.hunt_bot.team_one_name.lower() in role_name:
                        self.team_totals[self.hunt_bot.team_one_name] += 1
                        self.last_valid_drop_msg_id = max(self.last_valid_drop_msg_id, msg.id)
                        break
                    elif self.hunt_bot.team_two_name.lower() in role_name:
                        self.team_totals[self.hunt_bot.team_two_name] += 1
                        self.last_valid_drop_msg_id = max(self.last_valid_drop_msg_id, msg.id)
                        break

        self.total_items = sum(self.team_totals.values())
        self.determine_team_placements()
        self.update_sticky_msg_string()

    def determine_team_placements(self) -> None:
        t1 = self.team_totals.get(self.hunt_bot.team_one_name, 0)
        t2 = self.team_totals.get(self.hunt_bot.team_two_name, 0)
        if t1 > t2:
            self.winning_team_name = self.hunt_bot.team_one_name
            self.losing_team_name = self.hunt_bot.team_two_name
        elif t2 > t1:
            self.winning_team_name = self.hunt_bot.team_two_name
            self.losing_team_name = self.hunt_bot.team_one_name
        else:
            self.winning_team_name = "Tie"
            self.losing_team_name = "Tie"

    def update_sticky_msg_string(self) -> None:
        team1_total = self.team_totals.get(self.hunt_bot.team_one_name, 0)
        team2_total = self.team_totals.get(self.hunt_bot.team_two_name, 0)
        leading_team_total = max(team1_total, team2_total)
        if self.winning_team_name == "Tie":
            leading_team_name = "Tie"
        else:
            leading_team_name = self.winning_team_name

        self.sticky_message_string = sticky_msg_template.substitute(
            team_one_name=self.hunt_bot.team_one_name,
            team_one_total=team1_total,
            team_two_name=self.hunt_bot.team_two_name,
            team_two_total=team2_total,
            leading_team_name=leading_team_name,
            leading_team_total=leading_team_total,
            message_url=f"https://discord.com/channels/{self.hunt_bot.guild_id}/{self.drop_channel_id}/{self.last_valid_drop_msg_id}" if self.last_valid_drop_msg_id else "N/A"
        )

    async def post_counting_complete_msg(self) -> None:
        try:
            drop_channel = self.discord_bot.get_channel(self.drop_channel_id)
            await drop_channel.send(self.counting_complete_msg_str)
        except Exception as e:
            logger.error("[TotalBountyItemCounter Cog] Error posting counting complete message.", exc_info=e)

    def update_counting_complete_msg(self) -> None:
        winning_total = self.team_totals.get(self.winning_team_name, 0)
        losing_total = self.team_totals.get(self.losing_team_name, 0)
        self.counting_complete_msg_str = counting_complete_template.substitute(
            firstplace_team_name=self.winning_team_name,
            firstplace_total=winning_total,
            secondplace_team_name=self.losing_team_name,
            secondplace_total=losing_total,
            total_items=self.total_items
        )

    async def start_counter(self, start_msg_id: int, drop_channel_id: int) -> None:
        self.update_start_msg_id(start_msg_id)
        self.update_drop_channel_id(drop_channel_id)
        self.active = True
        logger.info(f"[Counter] Counter started for channel {self.drop_channel_id}")

    async def stop_counter(self) -> None:
        self.active = False
        self.update_counting_complete_msg()
        await self.post_counting_complete_msg()
        self.reset_counter()

    def reset_counter(self) -> None:
        self.start_msg_id = 0
        self.sticky_msg_id = 0
        self.sticky_message_string = ""
        self.drop_channel_id = 0
        self.total_items = 0
        self.winning_team_name = ""
        self.losing_team_name = ""
        self.counting_complete_msg_str = ""
        self.message_list = []
        self.last_valid_drop_msg_id = 0

    @tasks.loop(seconds=3)
    async def count_items(self) -> None:
        if not self.active:
            return

        await self.get_messages_from_channel()
        if not self.message_list:
            return

        old_sticky = self.sticky_message_string  # store old content
        await self.recalc_totals()

        # Only proceed if the sticky content actually changed
        if self.sticky_message_string == old_sticky:
            return

        drop_channel = self.discord_bot.get_channel(self.drop_channel_id)
        if not drop_channel:
            return

        try:
            if self.sticky_msg_id:
                sticky_msg = await drop_channel.fetch_message(self.sticky_msg_id)
                # Get the last message in channel
                async for msg in drop_channel.history(limit=1):
                    last_msg = msg
                    break

                if sticky_msg.id == last_msg.id:
                    # Sticky is last, edit in place
                    await sticky_msg.edit(content=self.sticky_message_string)
                else:
                    # Sticky not last, delete & repost
                    await sticky_msg.delete()
                    sent_msg = await drop_channel.send(self.sticky_message_string)
                    self.sticky_msg_id = sent_msg.id
            else:
                # No sticky exists yet
                sent_msg = await drop_channel.send(self.sticky_message_string)
                self.sticky_msg_id = sent_msg.id

        except discord.NotFound:
            # Sticky was deleted, post again
            sent_msg = await drop_channel.send(self.sticky_message_string)
            self.sticky_msg_id = sent_msg.id

    @count_items.before_loop
    async def before_count_items(self) -> None:
        await self.discord_bot.wait_until_ready()
