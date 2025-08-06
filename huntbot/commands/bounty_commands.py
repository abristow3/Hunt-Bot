import discord
from discord import app_commands
import asyncio
import logging

logger = logging.getLogger(__name__)

active_bounties = {}  # Shared storage for bounties


async def bounty(interaction: discord.Interaction, name_of_item: str, reward_amount: str, time_limit: str = None, hunt_bot=None):
    if interaction.channel.id != hunt_bot.command_channel_id:
        return

    minutes = 2880  # default
    if time_limit and time_limit.isdigit():
        minutes = max(int(time_limit), 1)

    reward_str = reward_amount.strip().lower()
    multiplier = 1
    if reward_str.endswith('k'):
        multiplier = 1_000
        reward_str = reward_str[:-1]
    elif reward_str.endswith('m'):
        multiplier = 1_000_000
        reward_str = reward_str[:-1]

    try:
        reward_val = float(reward_str) * multiplier
        if reward_val < 0:
            await interaction.response.send_message("Reward amount cannot be negative.", ephemeral=True)
            return
    except ValueError:
        await interaction.response.send_message("Reward must be a number (K/M allowed).", ephemeral=True)
        return

    await interaction.response.send_message(
        f"Bounty created!\nItem: {name_of_item}\nReward: {reward_amount}\nTime Limit: {minutes} minutes"
    )

    bounty_key = name_of_item.strip().lower()

    async def end_bounty():
        await interaction.followup.send(f"The bounty for '{name_of_item}' has ended after {minutes} minutes.")
        active_bounties.pop(bounty_key, None)

    task = asyncio.create_task(asyncio.sleep(minutes * 60))
    task.add_done_callback(lambda _: asyncio.create_task(end_bounty()))

    active_bounties[bounty_key] = {
        'handle': task,
        'reward_amount': reward_amount
    }


async def listbounties(interaction: discord.Interaction, hunt_bot=None):
    if interaction.channel.id != hunt_bot.command_channel_id:
        return

    if not active_bounties:
        await interaction.response.send_message("There are no active bounties.", ephemeral=True)
        return

    msg = "\n".join(
        f"Item: {key} | Reward: {info['reward_amount']}" for key, info in active_bounties.items()
    )
    await interaction.response.send_message(f"**Active Bounties:**\n{msg}", ephemeral=True)


async def closebounty(interaction: discord.Interaction, bounty_item: str, user: discord.Member, hunt_bot=None):
    if interaction.channel.id != hunt_bot.command_channel_id:
        return

    bounty_key = bounty_item.strip().lower()
    info = active_bounties.get(bounty_key)
    if not info:
        await interaction.response.send_message("No such active bounty.", ephemeral=True)
        return

    info['handle'].cancel()
    reward = info['reward_amount']
    active_bounties.pop(bounty_key, None)
    await interaction.response.send_message(
        f"Bounty for '{bounty_item}' has been claimed by {user.mention} for {reward}!"
    )


def register_bounty_commands(tree: app_commands.CommandTree, hunt_bot):
    @tree.command(name="bounty", description="Create a new bounty")
    @app_commands.describe(
        name_of_item="Name of the item",
        reward_amount="Reward amount",
        time_limit="Time limit in minutes (optional)"
    )
    async def bounty_cmd(interaction: discord.Interaction, name_of_item: str, reward_amount: str, time_limit: str = None):
        await bounty(interaction, name_of_item, reward_amount, time_limit, hunt_bot=hunt_bot)

    @tree.command(name="listbounties", description="List all active bounties.")
    async def listbounties_cmd(interaction: discord.Interaction):
        await listbounties(interaction, hunt_bot=hunt_bot)

    @tree.command(name="closebounty", description="Close a bounty early.")
    @app_commands.describe(
        bounty_item="The item name of the bounty",
        user="The user who claimed it"
    )
    async def closebounty_cmd(interaction: discord.Interaction, bounty_item: str, user: discord.Member):
        await closebounty(interaction, bounty_item, user, hunt_bot=hunt_bot)
