from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from other.global_constants import *
from other.utility import *


class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="leaderboard", description="Display the leaderboard for a particular mod")
    @app_commands.describe(leaderboard_type="The leaderboard you want to show.")
    @app_commands.choices(leaderboard_type=[
        Choice(name="Overall", value="overall"),
        Choice(name="NoMod", value="nm"),
        Choice(name="HD", value="hd"),
        Choice(name="HR", value="hr"),
        Choice(name="DT", value="dt"),
        Choice(name="HT", value="ht")
    ])
    @app_commands.describe(page="The page of the leaderboard you want to show. Leave blank to show the first page.")
    @is_verified()
    async def leaderboard(self, interaction: discord.Interaction, leaderboard_type: Choice[str], page: int = 1):
        """
        /leaderboard <leadboard type> <page number>
        Shows the leaderboard for a particular mod type, including the user's position.
        If no argument is passed, then the overall leaderboard will be shown (total).
        """
        
        # Set parameters in the db queries
        num_results_displayed_per_page = 10
        offset = (page - 1) * num_results_displayed_per_page
        lb_type = leaderboard_type.value
        
        async with aiosqlite.connect("./data/database.db") as conn:
            cursor = await conn.cursor()
            
            # Check if inputted page is out of range
            await cursor.execute("SELECT COUNT(*) FROM exp_table")  # Counts the number of rows in exp_table
            data = await cursor.fetchone()
        
            assert data is not None
            num_pages: int = data[0] // num_results_displayed_per_page + 1
            if page < 1 or page > num_pages:
                await interaction.response.send_message(f"Invalid page number! Enter a page from 1 - {num_pages}")
                return
            
            # Initialize embed
            embed = discord.Embed(title=f"{leaderboard_type.name} Leaderboard")
            
            # Add stuff to leaderboard
            await self.populate_leaderboard(cursor, embed, lb_type, num_results_displayed_per_page, offset)
            embed.add_field(name='', value='-------------------------')  # Separate the leaderboard results from the user's personal stats at the bottom
            await self.add_user_to_leaderboard(interaction, cursor, embed, lb_type)

        # Change embed colour depending on the mod
        self.change_embed_colour_based_on_mod(embed, leaderboard_type)
        
        # Show the number of pages of the leaderboard in the footer
        embed.set_footer(text=f"Page {page} of {num_pages}")
        
        await interaction.response.send_message(embed=embed)
    
    def add_one_row_to_leaderboard(self, embed: discord.Embed, row):
        """Helper function. Given a row containing a user's rank, username, level, and exp, adds it to the leaderboard."""
        
        ranking = row[0]
        osu_username = row[1]
        level = row[2]
        exp = row[3]
        embed.add_field(name=f"{ranking}. {osu_username}", value = f"Level: {level} | EXP: {exp}", inline=False)

    async def populate_leaderboard(self, cursor: aiosqlite.Cursor, embed: discord.Embed, lb_type: str, num_results_displayed_per_page: int, offset: int):
        """
        Populates the leaderboard with other users' stats.
        num_results_displayed_per_page determines the number of users that are displayed.
        offset determines the starting row number for the query.
        """
        
        # Fetch sorted player data
        # dense_rank() is a window function, which adds a column called "ranking" based on the data sorted by exp descending
        # LIMIT limits the number of results shown at once
        # OFFSET is the row number that it starts from, 0-indexed
        query = f"""
                    SELECT 
                        dense_rank() OVER (ORDER BY {lb_type}_exp DESC) AS ranking, 
                        osu_username, {lb_type}_level, {lb_type}_exp 
                    FROM exp_table 
                    ORDER BY {lb_type}_exp DESC 
                    LIMIT {num_results_displayed_per_page}
                    OFFSET {offset}
                """
        await cursor.execute(query)
        table = await cursor.fetchall()
        
        # Populate page with users, with their levels and exp
        for row in table:
            self.add_one_row_to_leaderboard(embed, row)

    async def add_user_to_leaderboard(self, interaction: discord.Interaction, cursor: aiosqlite.Cursor, embed: discord.Embed, lb_type: str):
        """Add the user's stats and ranking at the bottom of the leaderboard."""
        
        # Get the user's position and statistics
        query = f"""
                    WITH data AS 
                        (SELECT 
                        dense_rank() OVER (ORDER BY {lb_type}_exp DESC) AS ranking, 
                        osu_username, {lb_type}_level, {lb_type}_exp, discord_id
                        FROM exp_table 
                        ORDER BY {lb_type}_exp DESC)

                    SELECT ranking, osu_username, {lb_type}_level, {lb_type}_exp FROM data
                    WHERE discord_id = {interaction.user.id}
                """
        await cursor.execute(query)
        row = await cursor.fetchone()

        # Attach the user's position and stats at the end of the embed
        self.add_one_row_to_leaderboard(embed, row)

    def change_embed_colour_based_on_mod(self, embed: discord.Embed, leaderboard_type: Choice[str]):
        """Change the embed's colour based on the mod."""
        
        match leaderboard_type.value:
            case "overall":
                embed.colour = discord.Color.blurple()
            case "nm":
                embed.colour = discord.Color.from_rgb(255, 255, 255)    # White
            case "hd":
                embed.colour = discord.Color.from_rgb(238, 241, 8)      # Yellow
            case "hr":
                embed.colour = discord.Color.from_rgb(244, 18, 18)      # Red
            case "dt":
                embed.colour = discord.Color.from_rgb(135, 68, 255)     # Purple
            case "ht":
                embed.colour = discord.Color.from_rgb(144, 144, 144)    # Gray
                
async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))