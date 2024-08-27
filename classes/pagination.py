import math
from typing import Any, Optional

import discord
from discord.ext import commands


class PaginationView(discord.ui.View):
    current_page: int = 1
    items_per_page: int = 5
    data: list[Any]
    number_of_pages: int
    
    def __init__(self, data: list[Any], items_per_page: Optional[int] = None):
        super().__init__()
        if items_per_page is not None:
            self.items_per_page = items_per_page
        self.data = data
        self.number_of_pages = math.ceil(len(data) / self.items_per_page)
    
    async def send(self, ctx: commands.Context):
        self.message = await ctx.send(view=self)
        await self.update_message(from_item=0, until_item=self.items_per_page)
    
    def create_embed(self, from_item: int, until_item: int) -> discord.Embed:
        embed = discord.Embed(title="something")
        for item in self.data[from_item:until_item]:
            embed.add_field(name=item, value=item, inline=False)
        embed.set_footer(text=f"Page {self.current_page} of {self.number_of_pages}")
        return embed
    
    async def update_message(self, from_item: int, until_item: int):
        self.update_buttons()
        await self.message.edit(embed=self.create_embed(from_item, until_item), view=self)
    
    def update_buttons(self):
        if self.current_page == 1:
            self.first_page_button.disabled = True
            self.prev_button.disabled = True
            self.next_button.disabled = False
            self.last_page_button.disabled = False
            
            self.first_page_button.style = discord.ButtonStyle.gray
            self.prev_button.style = discord.ButtonStyle.gray
            self.next_button.style = discord.ButtonStyle.green
            self.last_page_button.style = discord.ButtonStyle.green
            
        elif self.current_page == self.number_of_pages:
            self.first_page_button.disabled = False
            self.prev_button.disabled = False
            self.next_button.disabled = True
            self.last_page_button.disabled = True
            
            self.first_page_button.style = discord.ButtonStyle.green
            self.prev_button.style = discord.ButtonStyle.green
            self.next_button.style = discord.ButtonStyle.gray
            self.last_page_button.style = discord.ButtonStyle.gray
        
        else:
            self.first_page_button.disabled = False
            self.prev_button.disabled = False
            self.next_button.disabled = False
            self.last_page_button.disabled = False
            
            self.first_page_button.style = discord.ButtonStyle.green
            self.prev_button.style = discord.ButtonStyle.green
            self.next_button.style = discord.ButtonStyle.green
            self.last_page_button.style = discord.ButtonStyle.green
            
    @discord.ui.button(label="|<", style=discord.ButtonStyle.primary)
    async def first_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page = 1
        until_item: int = self.current_page * self.items_per_page
        from_item: int = until_item - self.items_per_page
        await self.update_message(from_item, until_item)

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page -= 1
        until_item: int = self.current_page * self.items_per_page
        from_item: int = until_item - self.items_per_page
        await self.update_message(from_item, until_item)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page += 1
        until_item: int = self.current_page * self.items_per_page
        from_item: int = until_item - self.items_per_page
        await self.update_message(from_item, until_item)
        
    @discord.ui.button(label=">|", style=discord.ButtonStyle.primary)
    async def last_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_page = self.number_of_pages
        until_item: int = self.current_page * self.items_per_page
        from_item: int = until_item - self.items_per_page
        await self.update_message(from_item, until_item)