import asyncio

import other.utility
from discord.ext import commands
from other.global_constants import *


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    @other.utility.is_admin()
    async def shutdown(self, ctx: commands.Context, seconds_to_wait_before_shutdown: int | str = 30, reason: str = "No reason provided."):
        """
        Disconnects the bot after a certain delay. 
        If <seconds_to_wait_before_shutdown> is "now" or 0, the shutdown is immediate.
        """
        
        if seconds_to_wait_before_shutdown not in ["now", 0]:
            await other.utility.send_in_all_channels(f"**Bot will shut down in {seconds_to_wait_before_shutdown} seconds!** Reason: {reason}")
            await asyncio.sleep(seconds_to_wait_before_shutdown)  # type: ignore
        
        await other.utility.send_in_all_channels("Shutting down...")
        await http_session.close_http_session()
        await bot.close()
    
    @commands.command()
    @other.utility.is_admin()
    async def reload(self, ctx: commands.Context, cog_name: str):
        """
        Reloads a specific extension specified by <cog_name>.
        cog_name does not include the ".py" extension.
        Reloads all extensions if <cog_name> = "all".
        """
        
        # Stores all cogs needed to be updated
        cog_list: list[str] = []
        
        # Adds all cog files to cog_list if <cog_name> = "all"
        if cog_name == "all":
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py"):
                    cog_list.append(filename[:-3])  # Removes the ".py" at the end

        # Otherwise, only add <cog_name> to the list
        else:
            cog_list.append(cog_name)
        
        # Reload each cog in cog_list
        for cog in cog_list:
            message = await ctx.channel.send(f"Reloading {cog}.py")
            
            try:
                await bot.reload_extension(f"cogs.{cog}")
            except Exception as error:
                await message.edit(content=f"Failed to reload {cog}.py: {error}")
            else:
                await message.edit(content=f"{cog}.py successfully reloaded.")
    
    @commands.command()
    @other.utility.is_admin()
    async def sync(self, ctx: commands.Context):
        """Sync all slash commands to discord."""
        
        synced = await bot.tree.sync()
        await ctx.channel.send(f"Synced {len(synced)} commands.")
        
async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))