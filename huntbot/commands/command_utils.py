from typing import Optional
import discord
from discord.ext.commands import Bot, Cog

async def fetch_cog(interaction: discord.Interaction, discord_bot: Bot, cog_name: str) -> Optional[Cog]:
    cog: Optional[Cog] = discord_bot.get_cog(cog_name)
    if not cog:
        await interaction.response.send_message(f"{cog_name} is not loaded or active.", ephemeral=True)
        return
    else:
        return cog
    
async def check_user_roles(interaction: discord.Interaction, authorized_roles: list) -> bool:
    user_roles = [role.name.lower() for role in getattr(interaction.user, "roles", [])]
    authorized_roles = [role.lower() for role in authorized_roles]

    if any(role in user_roles for role in authorized_roles):
        return True
    else:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return False