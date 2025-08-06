import discord
from discord import app_commands
import asyncio
import logging

logger = logging.getLogger(__name__)

active_bounties = {}  # Shared storage for bounties


class Bounty:
    def __init__(self, item_name: str, reward_amount: str, time_limit_hours: int = 48):
        self.item_name = item_name
        self.reward_amount = reward_amount
        self.time_limit_hours = time_limit_hours
        self.active = True
        self.completed_by = ""


class ItemBounties:
    def __init__(self):
        self.item_bounties = []

    async def create_new_bounty(self, item_name: str, reward_amount: str, time_limit_hours: int = 48):
        new_bounty = Bounty(item_name=item_name, reward_amount=reward_amount, time_limit_hours=time_limit_hours)
        self.item_bounties.append(new_bounty)


async def create_bounty(interaction: discord.Interaction, name_of_item: str, reward_amount: str,
                        time_limit_hours: int = 48, hunt_bot=None):
    if interaction.channel.id != hunt_bot.team_one_chat_channel and interaction.channel.id != hunt_bot.team_two_chat_channel:
        logger.info("bounty command ran in wrong channel")
        return


# async def listbounties(interaction: discord.Interaction, hunt_bot=None):
#     if interaction.channel.id != hunt_bot.command_channel_id:
#         return
#
#     if not active_bounties:
#         await interaction.response.send_message("There are no active bounties.", ephemeral=True)
#         return
#
#     msg = "\n".join(
#         f"Item: {key} | Reward: {info['reward_amount']}" for key, info in active_bounties.items()
#     )
#     await interaction.response.send_message(f"**Active Bounties:**\n{msg}", ephemeral=True)


# async def closebounty(interaction: discord.Interaction, bounty_item: str, user: discord.Member, hunt_bot=None):
#     if interaction.channel.id != hunt_bot.command_channel_id:
#         return
#
#     bounty_key = bounty_item.strip().lower()
#     info = active_bounties.get(bounty_key)
#     if not info:
#         await interaction.response.send_message("No such active bounty.", ephemeral=True)
#         return
#
#     info['handle'].cancel()
#     reward = info['reward_amount']
#     active_bounties.pop(bounty_key, None)
#     await interaction.response.send_message(
#         f"Bounty for '{bounty_item}' has been claimed by {user.mention} for {reward}!"
#     )


def register_bounty_commands(tree: app_commands.CommandTree, hunt_bot):
    @tree.command(name="bounty", description="Create a new bounty")
    @app_commands.describe(
        name_of_item="Name of the item",
        reward_amount="Reward amount",
        time_limit_hours="Time limit in hours (optional)"
    )
    async def bounty_cmd(interaction: discord.Interaction, name_of_item: str, reward_amount: str,
                         time_limit_hours: int = 48):
        await create_bounty(interaction, name_of_item=name_of_item, reward_amount=reward_amount,
                            time_limit_hours=time_limit_hours, hunt_bot=hunt_bot)

    # @tree.command(name="listbounties", description="List all active bounties.")
    # async def listbounties_cmd(interaction: discord.Interaction):
    #     await listbounties(interaction, hunt_bot=hunt_bot)
    #
    # @tree.command(name="closebounty", description="Close a bounty early.")
    # @app_commands.describe(
    #     bounty_item="The item name of the bounty",
    #     user="The user who claimed it"
    # )
    # async def closebounty_cmd(interaction: discord.Interaction, bounty_item: str, user: discord.Member):
    #     await closebounty(interaction, bounty_item, user, hunt_bot=hunt_bot)
