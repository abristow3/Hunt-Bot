from discord.ext import commands
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

class TotalItemCounterCog(commands.Cog):
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot):
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.start_msg_id = 0
        self.team_totals = {self.hunt_bot.team_one_name: 0, self.hunt_bot.team_two_name: 0}
        self.sticky_msg_id = 0
        self.sticky_message_string = ""
        self.drop_channel_id = 0
        self.active = False
        self.emoji_identifier = ""
        self.total_items = 0
        self.winning_team_name = ""
        self.losing_team_name = ""
        self.counting_complete_msg_str = ""
        self.message_list = [discord.Message]
        self.last_valid_drop_msg_id = 0
        self.valid_submission_emoji = "✅"
        self.invalid_submission_emoji = "❌"
        self.total_item_emoji = "⬆️"
    
    async def cog_load(self) -> None:
        logger.info("[TotalItemCounter Cog] Loading cog and initializing.")
        try:
            self.count_items.start()
        except Exception as e:
            logger.error(f"[TotalItemCounter Cog] Initialization failed: {e}")
    
    async def cog_unload(self) -> None:
        logger.info("[TotalItemCounter Cog] Unloading cog.")
        if self.count_items.is_running():
            self.count_items.stop()

    def update_drop_channel_id(self, channel_id: int) -> None:
        logger.debug("[TotalItemCounter Cog] Updating discord channel ID for drops.")
        self.drop_channel_id = channel_id
    
    def update_start_msg_id(self, msg_id: int) -> None:
        logger.debug("[TotalItemCounter Cog] Updating start message ID.")
        self.start_msg_id = msg_id

    async def post_sticky_msg(self) -> None:
        logger.debug("[TotalItemCounter Cog] Posting sticky message.")
        try:
            drop_channel = self.discord_bot.get_channel(self.drop_channel_id)
            sent_msg = await drop_channel.send(self.sticky_message_string)
            self.update_sticky_msg_id(sent_msg.id)
        except Exception as e:
            logger.error("[TotalItemCounter Cog] Error posting sticky message.", exc_info=e)

    async def get_newest_msg_id(self) -> int:
        # returns msot recent message ID
        return self.message_list[0].id

    async def delete_sticky_msg(self) -> None:
        logger.debug("[TotalItemCounter Cog] Deleting sticky messge.")
        try:
            drop_channel = self.discord_bot.get_channel(self.drop_channel_id)
            msg = await drop_channel.fetch_message(self.sticky_msg_id)
            await msg.delete()
        except Exception as e:
            logger.error("[TotalItemCounter Cog] Error deleting sticky message.", exc_info=e)

    async def edit_sticky_msg_content(self) -> None:
        logger.debug("[TotalItemCounter Cog] Editing published sticky message content.")
        try:
            drop_channel = self.discord_bot.get_channel(self.drop_channel_id)
            msg = await drop_channel.fetch_message(self.sticky_msg_id)
            await msg.edit(content=self.sticky_message_string)
        except Exception as e:
            logger.error("[TotalItemCounter Cog] Error when editing published sticky message content.", exc_info=e)

    def update_sticky_msg_string(self) -> None:
        logger.debug("[TotalItemCounter Cog] Updating sticky message string.")
        try:
            team1_name = self.hunt_bot.team_one_name
            team2_name = self.hunt_bot.team_two_name
            team1_total = self.team_totals[team1_name]
            team2_total = self.team_totals[team2_name]
            leading_team_total = self.team_totals[self.winning_team_name]
            message_url = f"https://discord.com/channels/{self.hunt_bot.guild_id}/{self.drop_channel_id}/{self.last_valid_drop_msg_id}"    

            self.sticky_message_string = sticky_msg_template.substitute(team_one_name=team1_name, team_one_total=team1_total, 
                                                                        team_two_name=team2_name, team_two_total=team2_total, 
                                                                        leading_team_name=self.winning_team_name, 
                                                                        leading_team_total=leading_team_total, message_url=message_url)
        except Exception as e:
            logger.error("[TotalItemCounter Cog] Error when updating sticky message string", exc_info=e)
    
    def update_sticky_msg_id(self, msg_id: int) -> None:
        logger.debug("[TotalItemCounter Cog] Updating sticky message ID.")
        self.sticky_msg_id = msg_id

    def update_counting_complete_msg(self) -> None:
        logger.debug("[TotalItemCounter Cog] Updating counting complete message")
        winning_team_total = self.team_totals[self.winning_team_name]
        losing_team_total = self.team_totals[self.losing_team_name]
        self.counting_complete_msg_str = counting_complete_template.substitute(firstplace_team_name=self.winning_team_name, firstplace_total=winning_team_total,
                                                    secondplace_team_name=self.losing_team_name, secondplace_total=losing_team_total,
                                                    total_tems=self.total_items)

    async def post_counting_complete_msg(self) -> None:
        logger.debug("[TotalItemCounter Cog] Posting counting complete message")
        try:
            drop_channel = self.discord_bot.get_channel(self.drop_channel_id)
            await drop_channel.send(self.counting_complete_msg_str)
        except Exception as e:
            logger.error("[TotalItemCounter Cog] Error posting counting complete message.", exc_info=e)

    async def start_counter(self, start_msg_id: int, drop_channel_id: int) -> None:
        logger.info("[TotalItemCounter Cog] Starting item counter for challenge.")
        self.update_start_msg_id(start_msg_id=start_msg_id)
        self.update_drop_channel_id(channel_id=drop_channel_id)
        self.active = True
    
    async def stop_counter(self) -> None:
        logger.info("[TotalItemCounter Cog] Ending item counter for challenge.")
        self.active = False
        self.update_counting_complete_msg()
        self.post_counting_complete_msg()
        self.reset_counter()
    
    def reset_counter(self) -> None:
        # Reset to initial values for next process call
        logger.info("[TotalItemCounter Cog] Resetting cog values.")
        self.start_msg_id = 0
        self.sticky_msg_id = 0
        self.sticky_message_string = ""
        self.drop_channel_id = 0
        self.total_items = 0
        self.team_totals = {self.hunt_bot.team_one_name: 0, self.hunt_bot.team_two_name: 0}
        self.winning_team_name = ""
        self.losing_team_name = ""
        self.counting_complete_msg_str = ""
        self.message_list = []
        self.last_valid_drop_msg_id = 0

    def update_total_items(self) -> None:
        logger.debug("[TotalItemCounter Cog] Updating total items.")
        team1_total = self.team_totals.get(self.hunt_bot.team_one_name, 0)
        team2_total = self.team_totals.get(self.hunt_bot.team_two_name, 0)
        self.total_items = team1_total + team2_total

    def determine_team_placements(self) -> None:
        logger.debug("[TotalItemCounter Cog] Determing which team is in the lead.")
        team1_total = self.team_totals[self.hunt_bot.team_one_name]
        team2_total = self.team_totals[self.hunt_bot.team_two_name]

        if team1_total > team2_total:
            # Team 1 is in the lead so use their name
            self.winning_team_name = self.hunt_bot.team_one_name
            self.losing_team_name = self.hunt_bot.team_two_name
        elif team1_total < team2_total:
            # Team 2 is in the lead so use their name
            self.winning_team_name = self.hunt_bot.team_two_name
            self.losing_team_name = self.hunt_bot.team_one_name
        elif team1_total == team2_total:
            # It is a tie and since you  must win by 1, the team that was winning before the tie is technically still winning, so do nothing.
            return
        
    async def get_messages_from_channel(self) -> None:
        logger.debug("[TotalItemCounter Cog] Retrieving message history from drop channel.")
        # Get list of messages in channel since self.starting_msg_id
        try:
            drop_channel = self.discord_bot.get_channel(self.drop_channel_id)
            self.message_list = []
        
            # Iterate over messages and only include messages after our start_msg_id
            async for m in drop_channel.history(after=discord.Object(id=self.start_msg_id)):
                self.message_list.append(m)
        except Exception as e:
            logger.error("[TotalItemCounter Cog] Error when retrieving message history from drop channel.", exc_info=e)

    def count_valid_drops(self) -> None:
        logger.debug("[TotalItemCounter Cog] Tallying up scores based on drop submissions.")
        self.filter_messages()
        self.update_total_items()

    def filter_messages(self) -> None:
        # Iterates over messages and checks if they have the valid screenie reaction
        valid = False
        is_total = False

        for message in self.message_list:
            # Check all reactions to see if it is a drop we need to process
            for reaction in message.reactions:
                if reaction == self.invalid_submission_emoji:
                    valid = False
                    break

                if reaction == self.valid_submission_emoji:
                    valid = True
                
                if reaction == self.total_item_emoji:
                    is_total = True

            if valid and is_total:
                self.allocate_point(message=message)
                self.determine_team_placements()

    def allocate_point(self, message: discord.Message) -> None:
        msg_id = message.id
        author = message.author

        # Check if they are a member of team 1, if not, then they are team 2
        for role in author.roles:
            if self.hunt_bot.team_one_name in role:
                self.update_team_total(team_name=self.hunt_bot.team_one_name)
            else:
                self.update_team_total(team_name=self.hunt_bot.team_two_name)

        # Update last valid drop msg ID pointer
        self.last_valid_drop_msg_id = msg_id
    
    def update_team_total(self, team_name: str) -> None:
        # Increments the total for a team name
        self.team_totals[team_name] += 1

    @tasks.loop(seconds=3)
    async def count_items(self) -> None:
        if not self.active:
            # Do nothing
            return 
        
        # Flag is active, so run main logic
        self.get_messages_from_channel()
        self.count_valid_drops()

        # Once a drop has been submitted and tallied, then post the first sticky message and the other processes
        if self.total_items > 0:
            # Check if any new messages since last sticky was posted
            latest_msg_id = self.get_newest_msg_id()

            # update message strig no matter what in case there were changes 
            self.update_sticky_msg_string()

            # Check if latest msg is not sticky msg
            if latest_msg_id != self.sticky_msg_id:
                # if not delete old sticky message and post new one
                self.delete_sticky_msg()
                self.post_sticky_msg()
            else:
                # otherwise it is - update sticky msg string
                self.edit_sticky_msg_content()

    @count_items.before_loop
    async def before_count_items(self) -> None:
        await self.discord_bot.wait_until_ready()
