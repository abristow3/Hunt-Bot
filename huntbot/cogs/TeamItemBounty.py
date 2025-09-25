from discord.ext import commands
from huntbot.HuntBot import HuntBot
import logging
import discord
from datetime import datetime

logger = logging.getLogger(__name__)

class TeamItemBounty:
    def __init__(self, item_name: str, reward_amount: float, time_limit_hours: int = 48):
        self.item_name = item_name
        self.reward_amount = reward_amount
        self.time_limit_hours = time_limit_hours
        self.active = True
        self.completed_by = ""
        self.start_time = datetime.utcnow()
        self.time_remaining = self.time_limit_hours

class TeamItemBountyCog(commands.Cog):
    def __init__(self, hunt_bot: HuntBot):
        self.hunt_bot = hunt_bot
        self.target_roles = {f"{hunt_bot.team_one_name} team leader", f"{hunt_bot.team_two_name} team leader", "staff"}

        # Setup dict format: {"team1":[], "team2":[]}
        self.active_bounties = {self.hunt_bot.team_one_name: [], self.hunt_bot.team_two_name: []}

        # Set empty bounty leaderboard (same structure as active bounties)
        self.bounty_leaderboard = self.active_bounties

    async def _get_team_name(self, interaction: discord.Interaction) -> str | None:
        """
        Determines the team name based on the channel in which the interaction occurred.

        This method checks the `channel_id` of the provided Discord interaction to determine
        whether it belongs to team one or team two. If it matches a known team channel, the
        corresponding team name is returned. If the channel is unrecognized, an error message
        is sent to the user and `None` is returned.

        Parameters:
            interaction (discord.Interaction): The interaction object received from a Discord command
                                            or component interaction.

        Returns:
            str | None: The name of the team ("Team One" or "Team Two") if the channel matches;
                        otherwise, `None` if the team could not be determined.
        """
        if interaction.channel_id == self.hunt_bot.team_one_chat_channel_id:
            return self.hunt_bot.team_one_name
        elif interaction.channel_id == self.hunt_bot.team_two_chat_channel_id:
            return self.hunt_bot.team_two_name
        else:
            await interaction.followup.send("Error: Could not determine the correct team.", ephemeral=True)
            return None

    def _is_duplicate_bounty(self, team_name: str, item_name: str) -> bool:
        """
            Checks if a bounty for the given item already exists and is active for the specified team.

            This method performs a case-insensitive comparison to determine if an active bounty
            with the same item name already exists in the active bounties list for the provided team.

            Parameters:
                team_name (str): The name of the team to check (e.g., "Team One" or "Team Two").
                item_name (str): The name of the item to check for duplication.

            Returns:
                bool: True if a matching active bounty exists for the team; False otherwise.
        """
        item_name = item_name.lower()
        return any(
            (bounty.item_name.lower() == item_name and bounty.active)
            for bounty in self.active_bounties.get(team_name, [])
        )

    async def update_bounty_time_remaining(self):
        """
        Updates the remaining time for all active bounties across all teams.

        Iterates through the list of active bounties for each team and, if a bounty is still active,
        calls an internal method to update its time remaining.

        This method is intended to be run periodically (e.g., on a timer or task loop) to keep bounty timers accurate.

        Returns:
            None
        """
        for team_bounties in self.active_bounties.values():
            for bounty in team_bounties:
                if bounty.active:
                    await self._update_single_bounty_time(bounty)

    @staticmethod
    async def _update_single_bounty_time(bounty: TeamItemBounty):
        """
        Updates the time remaining for a single active bounty.

        Calculates how much time has elapsed since the bounty started and updates its
        `time_remaining` accordingly. If the bounty has expired (i.e., time remaining is
        less than or equal to 0), it sets the bounty as inactive.

        Parameters:
            bounty (TeamItemBounty): The bounty object whose remaining time is to be updated.

        Returns:
            None
        """
        if not bounty.active:
            return

        elapsed_time = datetime.utcnow() - bounty.start_time
        elapsed_hours = elapsed_time.total_seconds() / 3600
        bounty.time_remaining = round(bounty.time_limit_hours - elapsed_hours, 2)

        if bounty.time_remaining <= 0:
            bounty.time_remaining = 0
            bounty.active = False

    async def _check_user_roles(self, interaction: discord.Interaction) -> bool:
        """
        Checks whether the user invoking the interaction has one of the required roles.

        Compares the user's role names (case-insensitive) against a predefined set of target roles.
        If the user lacks the required role, an ephemeral message is sent denying permission.

        Parameters:
            interaction (discord.Interaction): The interaction object containing the user context.

        Returns:
            bool: True if the user has one of the valid roles; False otherwise.
        """
        member = interaction.user
        role_names = [role.name.lower() for role in member.roles]
        normalized_targets = {r.lower() for r in self.target_roles}

        logger.info(f"[TeamItemBounty Cog] Checking user roles: {role_names}, valid roles: {normalized_targets}")

        if not any(role in role_names for role in normalized_targets):
            await interaction.followup.send("You don't have permission to run that command.", ephemeral=True)
            return False

        return True

    async def _check_channel_id(self, interaction: discord.Interaction) -> bool:
        """
        Verifies that the interaction was triggered in a valid team chat channel.

        This method checks whether the interaction's channel ID matches either of the predefined
        team chat channels (`team_one_chat_channel_id` or `team_two_chat_channel_id`). If the check fails,
        an ephemeral error message is sent to the user.

        Parameters:
            interaction (discord.Interaction): The interaction object that triggered the command.

        Returns:
            bool: True if the interaction occurred in a valid team chat channel; False otherwise.
        """
        logger.info(f"[TeamItemBounty Cog] interaction channel id {interaction.channel_id}")
        logger.info(f"[TeamItemBounty Cog] team one general channel id {self.hunt_bot.team_one_chat_channel_id}")
        logger.info(f"[TeamItemBounty Cog] team two general channel id {self.hunt_bot.team_two_chat_channel_id}")
        if interaction.channel.id != self.hunt_bot.team_one_chat_channel_id and interaction.channel.id != self.hunt_bot.team_two_chat_channel_id:
            await interaction.followup.send("This command can only be ran in the team chat channels",
                                                    ephemeral=True)
            return False
        else:
            logger.info("[TeamItemBounty Cog] Chat channel check passed")
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
                await interaction.followup.send(
                    "Reward amount cannot be negative.", ephemeral=True
                )
                return None
            return reward_val
        except ValueError:
            await interaction.followup.send(
                "Reward amount must be a number (optionally with 'K' for thousand or 'M' for million).",
                ephemeral=True
            )
            return None

    async def _create_bounty_table(self, team_name: str) -> str:
        """
        Generates a formatted text table of all bounties for a given team.

        Retrieves the list of bounties associated with the specified team name,
        sorts them by active status and remaining time, and constructs a bordered
        table as a string. Each row includes details such as item name, status,
        reward, time left, and who completed it.

        If there are no bounties for the team, a simple message is returned instead.

        Parameters:
            team_name (str): The name of the team for which to generate the bounty table.

        Returns:
            str: A formatted string representing the bounty table, or a message indicating
                that no bounties are listed for the team.
        """
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

    async def create_bounty(self, interaction: discord.Interaction, item_name: str, reward_amount: str,
                            time_limit_hours: int = 48) -> None:
        """
        Handles the creation of a new item bounty for the invoking user's team.

        This method performs the following:
        - Defers the interaction response.
        - Validates the command context (channel and user permissions).
        - Parses the reward amount and validates input.
        - Ensures the same item is not already listed as an active bounty.
        - Creates a new bounty and appends it to the team's active bounty list.
        - Sends a formatted message displaying the bounty in a table.

        Parameters:
            interaction (discord.Interaction): The interaction that triggered the command.
            item_name (str): The name of the item being placed on bounty.
            reward_amount (str): The string input representing the reward (to be parsed).
            time_limit_hours (int, optional): The number of hours the bounty should last. Defaults to 48.

        Returns:
            None
        """
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
            await interaction.followup.send("Time limit must be greater than 0.", ephemeral=True)
            return

        logger.info(f"[TeamItemBounty Cog] create bounty arguments validated: {item_name} {reward_val} {time_limit_hours}")
       # Determine team and embed color
        if interaction.channel_id == self.hunt_bot.team_one_chat_channel_id:
            team_name = self.hunt_bot.team_one_name
        elif interaction.channel_id == self.hunt_bot.team_two_chat_channel_id:
            team_name = self.hunt_bot.team_two_name
        else:
            await interaction.followup.send("Error: Could not determine the correct team.", ephemeral=True)
            return

        # Check for duplicate bounty
        if self._is_duplicate_bounty(team_name=team_name, item_name=item_name):
            await interaction.followup.send("Error: Your team already has a bounty out for this item.",
                                                    ephemeral=True)
            return

        # Create and add bounty
        new_bounty = TeamItemBounty(item_name=item_name.lower(), reward_amount=reward_val, time_limit_hours=time_limit_hours)

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
        """
        Lists all current bounties for the invoking user's team in a formatted table.

        This method:
        - Defers the interaction response.
        - Verifies the command was run in a valid team chat channel.
        - Determines the user's team based on the interaction.
        - Updates the remaining time on all active bounties.
        - Generates and sends a formatted bounty table as a code block.

        Parameters:
            interaction (discord.Interaction): The interaction that triggered the command.

        Returns:
            None
        """
        # Check correct channel
        if not await self._check_channel_id(interaction=interaction):
            return

        # Determine team and embed color
        team_name = await self._get_team_name(interaction=interaction)
        if not team_name:
            await interaction.followup.send("Error: Could not determine the correct team.", ephemeral=True)
            return

        # Only update when command is used (uses less resources and clock)
        await self.update_bounty_time_remaining()

        # Generate table
        message = await self._create_bounty_table(team_name)
        await interaction.followup.send(f"```\n{message}\n```")


    async def close_bounty(self, interaction: discord.Interaction, item_name: str, completed_by: str):
        """
        Marks an active bounty as completed for the invoking user's team.

        This method:
        - Verifies the command was run in a valid team channel.
        - Ensures the user has the appropriate role to close bounties.
        - Locates the bounty based on the provided item name.
        - Sets the bounty as inactive, assigns the completer, and sets remaining time to 0.

        Parameters:
            interaction (discord.Interaction): The interaction that triggered the command.
            item_name (str): The name of the item whose bounty is being closed.
            completed_by (str): The name or identifier of the person who completed the bounty.

        Returns:
            None
        """
        # Check correct channel
        if not await self._check_channel_id(interaction=interaction):
            return

        # Check user roles for privileges
        if not await self._check_user_roles(interaction):
            return

        # Determine team
        team_name = await self._get_team_name(interaction=interaction)
        if not team_name:
            await interaction.followup.send("Error: Could not determine the correct team.", ephemeral=True)
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
            await interaction.followup.send("Error closing bounty.", ephemeral=True)
            return

        logger.info(f"{team_name} team bounty for {item_name} closed successfully")
        await interaction.followup.send(f"Bounty for {item_name} closed successfully", ephemeral=True)

    async def update_bounty(self, interaction: discord.Interaction, item_name: str, reward_amount: str = "",
                            time_limit_hours: int = -100):
        """
        Updates the reward amount and/or time limit for an existing bounty.

        This method:
        - Validates the interaction context and user roles.
        - Ensures at least one of reward or time limit is provided.
        - Parses the reward amount if provided.
        - Resets the bounty's timer if a new time limit is set.
        - Applies updates and refreshes bounty time calculations.

        Parameters:
            interaction (discord.Interaction): The interaction that triggered the command.
            item_name (str): The name of the bounty item to update.
            reward_amount (str, optional): New reward amount. Pass an empty string to leave unchanged.
            time_limit_hours (int, optional): New time limit in hours. Set to -100 to leave unchanged.

        Returns:
            None
        """
        # Check correct channel
        if not await self._check_channel_id(interaction):
            return

        # Check user roles for privileges
        if not await self._check_user_roles(interaction):
            return

        # Determine team
        team_name = await self._get_team_name(interaction=interaction)

        if not team_name:
            await interaction.followup.send("Error: Could not determine the correct team.", ephemeral=True)
            return

        if reward_amount == "" and time_limit_hours == -100:
            await interaction.followup.send("Error: You must update either the reward amount, or the time "
                                                    "remaining.", ephemeral=True)
            return

        reward_val = None
        if reward_amount != "":
            reward_val = await self._parse_reward_amount(interaction, reward_amount)
            if reward_val is None:
                return

        if time_limit_hours != -100 and time_limit_hours <= 0:
            await interaction.followup.send("Time limit must be greater than 0.", ephemeral=True)
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
            await interaction.followup.send(f"Error: Could not find bounty item '{item_name}' and update it.",
                                                    ephemeral=True)
            return

        await interaction.followup.send(f"Bounty for {item_name} updated successfully!", ephemeral=True)
        return
