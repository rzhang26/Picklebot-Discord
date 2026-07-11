import os
import discord
from discord.ext import commands

class FilterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        swear_words = os.getenv('SWEAR_WORDS', '')
        self.banned_vocabulary = {word.strip() for word in swear_words.lower().split(',') if word.strip()}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return 
        
        content_words = set(message.content.lower().split())

        if content_words.intersection(self.banned_vocabulary):
            try:
                await message.delete()
                warning = f'Please use kinder language {message.author.mention}'
                await message.channel.send(warning, delete_after=10.0)
            except discord.Forbidden:
                print('Missing \'Channel Messages\' permissions in channel {message.channel.id}')

async def setup(bot):
    await bot.add_cog(FilterCog(bot))
    