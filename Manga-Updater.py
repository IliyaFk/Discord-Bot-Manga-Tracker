import os
import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv
from pymongo import MongoClient
from MangaTracker import *

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Database Setup
MONGO_URI = os.getenv('MONGODB_TOKEN')
clientDB = MongoClient(MONGO_URI)
db = clientDB['DiscordDB']
chapters_collection = db['chapters']
chapters_collection.create_index([('number', 1)], unique=True)

################################ Delete specific chapter from database for debugging purposes ############################
# chapter_number_to_delete = 1133  # Change this to the chapter number you want to delete
# result = chapters_collection.delete_one({'number': chapter_number_to_delete})
##########################################################################################################################

# Line to delete entries in chapters_collection for debugging purposes
# chapters_collection.delete_many({})

url = "https://mangafire.to"

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Command to track a manga
@bot.command(name='track')
async def track(ctx, *, manga_name: str):
    print(f'Command triggered by {ctx.author.name}')
    await ctx.send(f'Tracking Manga: {manga_name}')

# Simple ping command
@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('Pong!')

# Background task to check for chapter updates
async def check_chapter_updates():
    await bot.wait_until_ready()  # Wait until the bot has connected to Discord

    while not bot.is_closed():  # Keep running the task until the bot is closed
        chapter = checkUpdates(url)

        if chapter:
            print(chapter)
            #Send message to the channel
            channel = bot.get_channel(809917094388039713)  # Ensure correct channel ID is used
            if channel:
                asyncio.run_coroutine_threadsafe(channel.send(url + chapter['link']), bot.loop)

        await asyncio.sleep(3600)  # Wait for 1 hour before checking again

# Event when the bot is ready
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    bot.loop.create_task(check_chapter_updates())  # Start the background task

# Run the bot
bot.run(TOKEN)
