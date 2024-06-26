from discord.ext import commands
from other.global_constants import *


@bot.event
async def on_command_error(ctx: commands.Context, error):
    """
    Generic error handler for all text commands.
    Note that both command-specific and cog-specific error handlers are called before this generic handler.
    """
    
    await ctx.send(f"An exception occurred: {error}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """
    Generic error handler for all slash commands.
    Note that both command-specific and cog-specific error handlers are called before this generic handler.
    """
    if interaction.response.is_done():
        original_response = await interaction.original_response()
        await original_response.edit(content=f"An exception occurred: {error}")
        
    elif isinstance(error, discord.app_commands.CommandOnCooldown):
        await interaction.response.send_message(error)
        
    else:
        await interaction.response.send_message(f"An exception occurred: {error}")