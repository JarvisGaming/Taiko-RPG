import datetime
import os
import traceback

from discord import app_commands
from discord.ext import commands
from other.global_constants import *


@bot.event
async def on_interaction(interaction: discord.Interaction):
    """If user is running /submit, add the user in users_currently_running_submit_command."""
    assert interaction.command is not None
    if interaction.command.name == "submit":
        users_currently_running_submit_command.add(interaction.user.id)

@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command: app_commands.Command):
    """When /submit finishes, remove the user from users_currently_running_submit_command."""
    if command.name == "submit":
        users_currently_running_submit_command.discard(interaction.user.id)

# Activate error handling only for live version
if not os.getcwd().endswith("test"):
    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.errors.CommandInvokeError):
        """
        Generic error handler for all text commands.
        Note that both command-specific and cog-specific error handlers are called before this generic handler.
        """

        if isinstance(error, commands.NotOwner):
            await ctx.send("You can't run admin commands!")
            return
        
        # Command checks like is_verified and cooldowns are already handled
        elif isinstance(error, commands.CheckFailure):
            return
        
        await ctx.send(f"An exception occurred: {error}")
        
        write_error_to_log(error)

    @bot.tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        """
        Generic error handler for all slash commands.
        Note that both command-specific and cog-specific error handlers are called before this generic handler.
        """
        
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(error)
            return
        
        # Checks like is_verified are already handled
        if isinstance(error, app_commands.CheckFailure):
            return
        
        # Remove user from users_currently_running_submit_command if /submit exited early
        assert interaction.command is not None
        if interaction.command.name == "submit":
            users_currently_running_submit_command.remove(interaction.user.id)
        
        # Send error message
        if interaction.response.is_done():
            original_response = await interaction.original_response()
            await original_response.edit(content=f"An exception occurred: {error}")
            
        else:
            await interaction.response.send_message(f"An exception occurred: {error}")
        
        write_error_to_log(error)

def write_error_to_log(error: commands.errors.CommandInvokeError | app_commands.AppCommandError):
    """Errors caught by on_command_error and on_app_command_error are not written to logs, so it has to be done manually."""
    
    with open("./logs.log", "a", encoding="utf-8") as file:
        time = datetime.datetime.now()
        formatted_time = time.strftime('%Y-%m-%d %H:%M:%S')
        file.write(f"[{formatted_time}] [ERROR]\n")
        traceback.print_tb(tb=error.__traceback__, file=file)
        file.write(str(error))
        file.write("\n")
