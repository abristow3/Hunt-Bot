import discord
from discord import app_commands
import logging
from huntbot.HuntBot import HuntBot
from datetime import datetime

logger = logging.getLogger(__name__)


class Bounty:
    def __init__(self, item_name: str, reward_amount: float, time_limit_hours: int = 48):
        self.item_name = item_name
        self.reward_amount = reward_amount
        self.time_limit_hours = time_limit_hours
        self.active = True
        self.completed_by = ""
        self.start_time = datetime.utcnow()
        self.time_remaining = self.time_limit_hours


class ItemBounties:
    def __init__(self, hunt_bot: HuntBot):
        self.hunt_bot = hunt_bot
        self.target_roles = {"red team leader", "gold team leader", "staff"}

        # Setup dict format: {"team1":[], "team2":[]}
        self.active_bounties = {self.hunt_bot.team_one_name: [], self.hunt_bot.team_two_name: []}

        # Set empty bounty leaderboard (same structure as active bounties)
        self.bounty_leaderboard = self.active_bounties

    async def create_bounty(self, interaction: discord.Interaction, item_name: str, reward_amount: str,
                            time_limit_hours: int = 48):
        # Check correct channel
        if not await self._check_channel_id(interaction):
            return

        # Check user roles for privileges
        if not await self._check_user_roles(interaction):
            return

        reward_val = None
        if reward_amount != "":
            reward_val = await self._parse_reward_amount(interaction, reward_amount)
            if reward_val is None:
                return

        if time_limit_hours <= 0:
            await interaction.response.send_message("Time limit must be greater than 0.", ephemeral=True)
            return

        logger.info(f"[ITEM BOUNTIES] create bounty arguments validated: {item_name} {reward_val} {time_limit_hours}")

        # Determine team and embed color
        if interaction.channel_id == self.hunt_bot.team_one_chat_channel:
            team_name = self.hunt_bot.team_one_name
        elif interaction.channel_id == self.hunt_bot.team_two_chat_channel:
            team_name = self.hunt_bot.team_two_name
        else:
            await interaction.response.send_message("Error: Could not determine the correct team.", ephemeral=True)
            return

        # Check for duplicate bounty
        if self._is_duplicate_bounty(team_name=team_name, item_name=item_name):
            await interaction.response.send_message("Error: Your team already has a bounty out for this item.",
                                                    ephemeral=True)
            return

        await interaction.response.defer()

        # Create and add bounty
        new_bounty = Bounty(item_name=item_name.lower(), reward_amount=reward_val, time_limit_hours=time_limit_hours)

        if team_name not in self.active_bounties:
            self.active_bounties[team_name] = []

        self.active_bounties[team_name].append(new_bounty)
        logger.info(f"All bounties: {self.active_bounties}")
        logger.info(f"[CREATE_BOUNTY] New bounty created for {team_name} team")

        # Table formatting for new bounty message
        col_widths = {
            "Item Name": 20,
            "Status": 8,
            "Reward": 16,
            "Time Left": 12,
            "Completed By": 14
        }

        headers = list(col_widths.keys())
        header_row = "| " + " | ".join(f"{header:^{col_widths[header]}}" for header in headers) + " |"
        divider = "+-" + "-+-".join("-" * col_widths[header] for header in headers) + "-+"

        # Bounty details
        status = "Active"
        time_left = f"{new_bounty.time_remaining:.1f}h"
        reward = f"{int(new_bounty.reward_amount):,}" if new_bounty.reward_amount else "N/A"
        completed_by = "N/A"

        row = "| " + " | ".join([
            f"{new_bounty.item_name[:col_widths['Item Name']]:^{col_widths['Item Name']}}",
            f"{status:^{col_widths['Status']}}",
            f"{reward:^{col_widths['Reward']}}",
            f"{time_left:^{col_widths['Time Left']}}",
            f"{completed_by:^{col_widths['Completed By']}}"
        ]) + " |"

        # Combine full message
        lines = [
            f"🎯 **New Bounty Posted for {team_name}!** 🎯",
            "",
            divider,
            header_row,
            divider,
            row,
            divider
        ]

        message = "\n".join(lines)
        # Wrap in code block for proper monospace alignment
        formatted_message = f"```{message}```"
        await interaction.followup.send(formatted_message)

    async def list_bounties(self, interaction: discord.Interaction):
        # Check correct channel
        if not await self._check_channel_id(interaction=interaction):
            return

        # Determine team and embed color
        team_name = await self._get_team_name(interaction=interaction)
        if not team_name:
            await interaction.response.send_message("Error: Could not determine the correct team.", ephemeral=True)
            return

        # Only update when command is used (uses less resources and clock)
        await self.update_bounty_time_remaining()

        # Generate table
        message = await self._create_bounty_table(team_name)
        await interaction.response.send_message(f"```\n{message}\n```")

    async def close_bounty(self, interaction: discord.Interaction, item_name: str, completed_by: str):
        # Check correct channel
        if not await self._check_channel_id(interaction=interaction):
            return

        # Check user roles for privileges
        if not await self._check_user_roles(interaction):
            return

        # Determine team
        team_name = await self._get_team_name(interaction=interaction)
        if not team_name:
            await interaction.response.send_message("Error: Could not determine the correct team.", ephemeral=True)
            return

        # Find the bounty
        item_name = item_name.lower()
        closed = False

        for bounty in self.active_bounties[team_name]:
            if bounty.item_name == item_name:
                # Found the bounty - close it and put in who completed it
                bounty.active = False
                bounty.completed_by = completed_by
                bounty.time_remaining = 0
                closed = True
                break

        if not closed:
            logger.error(f"Error closing {team_name} team bounty for {item_name}")
            await interaction.response.send_message("Error closing bounty.", ephemeral=True)
            return

        logger.info(f"{team_name} team bounty for {item_name} closed successfully")
        await interaction.response.send_message(f"Bounty for {item_name} closed successfully", ephemeral=True)

    async def update_bounty(self, interaction: discord.Interaction, item_name: str, reward_amount: str = "",
                            time_limit_hours: int = -100):
        # Check correct channel
        if not await self._check_channel_id(interaction):
            return

        # Check user roles for privileges
        if not await self._check_user_roles(interaction):
            return

        # Determine team
        team_name = await self._get_team_name(interaction=interaction)

        if not team_name:
            await interaction.response.send_message("Error: Could not determine the correct team.", ephemeral=True)
            return

        if reward_amount == "" and time_limit_hours == -100:
            await interaction.response.send_message("Error: You must update either the reward amount, or the time "
                                                    "remaining.", ephemeral=True)
            return

        reward_val = None
        if reward_amount != "":
            reward_val = await self._parse_reward_amount(interaction, reward_amount)
            if reward_val is None:
                return

        if time_limit_hours != -100 and time_limit_hours <= 0:
            await interaction.response.send_message("Time limit must be greater than 0.", ephemeral=True)
            return

        item_name = item_name.lower()
        updated = False

        # Find bounty and update time and or reward amount
        for bounty in self.active_bounties[team_name]:
            if bounty.item_name.lower() == item_name:
                if reward_val is not None:
                    bounty.reward_amount = reward_amount
                if time_limit_hours > 0:
                    bounty.time_limit_hours = time_limit_hours
                    bounty.start_time = datetime.utcnow()  # Reset the timer

                updated = True
                logger.info("Item bounty found and updated")
                # Update bounty times in memory
                await self.update_bounty_time_remaining()
                break

        if not updated:
            await interaction.response.send_message(f"Error: Could not find bounty item '{item_name}' and update it.",
                                                    ephemeral=True)
            return

        await interaction.response.send_message(f"Bounty for {item_name} updated successfully!", ephemeral=True)
        return

    async def _get_team_name(self, interaction: discord.Interaction) -> str | None:
        if interaction.channel_id == self.hunt_bot.team_one_chat_channel:
            return self.hunt_bot.team_one_name
        elif interaction.channel_id == self.hunt_bot.team_two_chat_channel:
            return self.hunt_bot.team_two_name
        else:
            await interaction.response.send_message("Error: Could not determine the correct team.", ephemeral=True)
            return None

    def _is_duplicate_bounty(self, team_name, item_name: str) -> bool:
        item_name = item_name.lower()
        return any(
            (bounty.item_name.lower() == item_name and bounty.active)
            for bounty in self.active_bounties.get(team_name, [])
        )

    async def _check_user_roles(self, interaction: discord.Interaction) -> bool:
        member = interaction.user
        role_names = [role.name.lower() for role in member.roles]
        normalized_targets = {r.lower() for r in self.target_roles}

        logger.info(f"[ITEM BOUNTIES] Checking user roles: {role_names}, valid roles: {normalized_targets}")

        if not any(role in role_names for role in normalized_targets):
            await interaction.response.send_message("You don't have permission to run that command.", ephemeral=True)
            return False

        return True

    async def update_bounty_time_remaining(self):
        for team_bounties in self.active_bounties.values():
            for bounty in team_bounties:
                if bounty.active:
                    await self._update_single_bounty_time(bounty)

    @staticmethod
    async def _update_single_bounty_time(bounty):
        if not bounty.active:
            return

        elapsed_time = datetime.utcnow() - bounty.start_time
        elapsed_hours = elapsed_time.total_seconds() / 3600
        bounty.time_remaining = round(bounty.time_limit_hours - elapsed_hours, 2)

        if bounty.time_remaining <= 0:
            bounty.time_remaining = 0
            bounty.active = False

    async def _check_channel_id(self, interaction) -> bool:
        logger.info(f"[ITEM BOUNTIES] interaction channel id {interaction.channel_id}")
        logger.info(f"[ITEM BOUNTIES] team one general channel id {self.hunt_bot.team_one_chat_channel}")
        logger.info(f"[ITEM BOUNTIES] team two general channel id {self.hunt_bot.team_two_chat_channel}")
        if interaction.channel.id != self.hunt_bot.team_one_chat_channel and interaction.channel.id != self.hunt_bot.team_two_chat_channel:
            await interaction.response.send_message("This command can only be ran in the team chat channels",
                                                    ephemeral=True)
            return False
        else:
            logger.info("[ITEM BOUNTIES] Chat channel check passed")
            return True

    @staticmethod
    async def _parse_reward_amount(interaction: discord.Interaction, reward_amount: str) -> float | None:
        """
        Parses a reward amount string, allowing 'K' (thousand) and 'M' (million) suffixes.
        Returns the numeric value as float, or None if invalid input (after sending an error response).
        """
        reward_str = reward_amount.strip()
        multiplier = 1

        if reward_str.lower().endswith('k'):
            multiplier = 1_000
            reward_str = reward_str[:-1]
        elif reward_str.lower().endswith('m'):
            multiplier = 1_000_000
            reward_str = reward_str[:-1]

        try:
            reward_val = float(reward_str) * multiplier
            if reward_val < 0:
                await interaction.response.send_message(
                    "Reward amount cannot be negative.", ephemeral=True
                )
                return None
            return reward_val
        except ValueError:
            await interaction.response.send_message(
                "Reward amount must be a number (optionally with 'K' for thousand or 'M' for million).",
                ephemeral=True
            )
            return None

    async def _create_bounty_table(self, team_name: str) -> str:
        bounties = self.active_bounties.get(team_name, [])

        if not bounties:
            return f"No bounties currently listed for {team_name}."

        # Sort bounties
        sorted_bounties = sorted(bounties, key=lambda b: (not b.active, b.time_remaining))

        # Column widths
        col_widths = {
            "Item Name": 20,
            "Status": 8,
            "Reward": 16,
            "Time Left": 12,
            "Completed By": 14
        }

        # Header row with borders
        headers = list(col_widths.keys())
        header_row = "| " + " | ".join(f"{header:^{col_widths[header]}}" for header in headers) + " |"
        divider = "+-" + "-+-".join("-" * col_widths[header] for header in headers) + "-+"

        lines = [divider, header_row, divider]

        # Table rows with border after each row
        for b in sorted_bounties:
            status = "Active" if b.active else "Inactive"
            time_left = f"{b.time_remaining:.1f}h" if b.active else "Expired"
            reward = f"{int(b.reward_amount):,}" if b.reward_amount else "N/A"
            completed_by = b.completed_by or "N/A"

            row = "| " + " | ".join([
                f"{b.item_name[:col_widths['Item Name']]:^{col_widths['Item Name']}}",
                f"{status:^{col_widths['Status']}}",
                f"{reward:^{col_widths['Reward']}}",
                f"{time_left:^{col_widths['Time Left']}}",
                f"{completed_by[:col_widths['Completed By']]:^{col_widths['Completed By']}}"
            ]) + " |"

            lines.append(row)
            lines.append(divider)  # <-- Add divider here after every row

        return "\n".join(lines)


def register_bounty_commands(tree: app_commands.CommandTree, item_bounties: ItemBounties):
    @tree.command(name="create_team_bounty", description="Create a new team bounty")
    @app_commands.describe(
        item_name="Name of the item",
        reward_amount="Reward amount",
        time_limit_hours="Time limit in hours (optional)"
    )
    async def create_bounty_cmd(interaction: discord.Interaction, item_name: str, reward_amount: str,
                                time_limit_hours: int = 48):
        try:
            logger.info(f"[ITEM BOUNTIES] create command ran with: {item_name} {reward_amount} {time_limit_hours}")
            await item_bounties.create_bounty(interaction, item_name=item_name, reward_amount=reward_amount,
                                              time_limit_hours=time_limit_hours)
        except Exception as e:
            logger.error("Error running create bounty command", exc_info=e)
            return

    @tree.command(name="list_team_bounties", description="Lists all team bounties.")
    async def list_bounties_cmd(interaction: discord.Interaction):
        logger.info(f"[ITEM BOUNTIES] list command ran")
        try:
            await item_bounties.list_bounties(interaction)
        except Exception as e:
            logger.error("Error running list team bounties command", exc_info=e)
            return

    @tree.command(name="close_team_bounty", description="Close a bounty early.")
    @app_commands.describe(item_name="The item name of the bounty", completed_by="The user who completed it")
    async def close_bounty_cmd(interaction: discord.Interaction, item_name: str, completed_by: str):
        logger.info(f"[ITEM BOUNTIES] close bounty command ran with {item_name} {completed_by}")
        try:
            await item_bounties.close_bounty(interaction, item_name=item_name, completed_by=completed_by)
        except Exception as e:
            logger.error("Error running close team bounty command", exc_info=e)
            return

    @tree.command(name="update_team_bounty",
                  description="Update the reward value and/or time remaining for an active bounty.")
    @app_commands.describe(
        item_name="The item name of the bounty to update.",
        reward_amount="New reward amount (optional, e.g. 100k, 2M)",
        time_limit_hours="New time limit in hours (optional, e.g. 10, 15)"
    )
    async def update_bounty_cmd(interaction: discord.Interaction, item_name: str, reward_amount: str = "",
                                time_limit_hours: int = -100):
        logger.info(f"[ITEM BOUNTIES] close bounty command ran with {item_name} {reward_amount} {time_limit_hours}")
        try:
            await item_bounties.update_bounty(interaction, item_name=item_name, reward_amount=reward_amount,
                                              time_limit_hours=time_limit_hours)
        except Exception as e:
            logger.error("Error running update team bounty command", exc_info=e)
            return

#
# # Command to show the top 3 bounty completers per team
# @bot.tree.command(name="bountyleaderboard", description="Show the top 3 bounty completers per team.")
# async def bountyleaderboard(interaction: discord.Interaction):
#     if interaction.channel.id != hunt_bot.command_channel_id:
#         return
#     # Determine which team to show
#     user_roles = {role.name for role in getattr(interaction.user, 'roles', [])}
#     show_teams = []
#     if 'Staff' in user_roles:
#         show_teams = ['Red Team', 'Gold Team']
#     elif 'Red Team' in user_roles or 'Red Team Leader' in user_roles:
#         show_teams = ['Red Team']
#     elif 'Gold Team' in user_roles or 'Gold Team Leader' in user_roles:
#         show_teams = ['Gold Team']
#     else:
#         await interaction.response.send_message("You must be a member or leader of a team to view the leaderboard.")
#         return
#     msg = "**Bounty Leaderboard**\n"
#     for show_team in show_teams:
#         msg += f"\n__{show_team}__\n"
#         team_data = bounty_leaderboard.get(show_team, {})
#         # Show all users who have completed bounties for this team, regardless of current roles
#         filtered = [entry for entry in team_data.values() if entry.get('team') == show_team]
#         if not filtered:
#             msg += "No completions yet.\n"
#         else:
#             top = sorted(filtered, key=lambda x: (x['value'], x['count']), reverse=True)[:3]
#             for idx, entry in enumerate(top, 1):
#                 value_str = f"{int(entry['value']):,}"
#                 msg += f"{idx}. {entry['name']} - {entry['count']} bounties, {value_str} total value\n"
#     await interaction.response.send_message(msg)

# class ConfirmNoWinnerView(View):
#     def __init__(self):
#         super().__init__(timeout=30)
#         self.value = None
#
#     @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
#     async def confirm(self, interaction: discord.Interaction, button: Button):
#         self.value = True
#         self.stop()
#         await interaction.response.edit_message(content="Bounty closed with no winner selected.", view=None)
#
#     @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
#     async def cancel(self, interaction: discord.Interaction, button: Button):
#         self.value = False
#         self.stop()
#         await interaction.response.edit_message(content="Bounty closure cancelled.", view=None)
#
