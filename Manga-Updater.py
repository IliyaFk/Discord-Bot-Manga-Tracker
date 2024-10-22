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
user_collection = db['users']

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
    user_id = ctx.author.id
    guild_id = ctx.guild.id

    #Query the database for the user
    user = user_collection.find_one({"user_id": str(user_id), "guilds.guild_id": str(guild_id)})

    mangas = trackManga(manga_name)
    title = (mangas[0])['title']
    link = (mangas[0])['link']
    print(title)


    if user:
        #Check if the manga is already being tracked by the user
        for guild in user['guilds']:
            if guild['guild_id'] == str(guild_id):
                tracked_manga = guild.get('manga_tracking', [])
                if not any(manga['manga_name'] == title for manga in tracked_manga):
                    guild['manga_tracking'].append({
                        'manga_name': title,
                        'manga_link': link
                    })
                    user_collection.update_one(
                        {"user_id": str(user_id), "guilds.guild_id": str(guild_id)},
                        {"$set": {"guilds.$.manga_tracking": guild['manga_tracking']}}
                    )
                    existing_collections = db.list_collection_names()
                    if manga_name not in existing_collections:
                        db.create_collection(title)
                        newCollection(title,link)
                    await ctx.send(f"Started tracking {title} for user {ctx.author.display_name}.")
                else:
                    await ctx.send(f"You are already tracking {title}.")
                break
    else:
        #Insert new user tracking data if not found
        user_collection.insert_one({
            "user_id": str(user_id),
            "guilds": [
                {
                    "guild_id": str(guild_id),
                    "manga_tracking": [
                        {
                            "manga_name": title,
                            "manga_link": link
                        }
                    ]
                }
            ]
        })
        existing_collections = db.list_collection_names()
        if manga_name not in existing_collections:
            db.create_collection(title)
            newCollection(title,link)
        await ctx.send(f"Started tracking {title} for user {ctx.author.display_name}.")


@bot.command(name='mymanga')
async def my_manga(ctx):
    user_id = ctx.author.id
    guild_id = ctx.guild.id

    user = user_collection.find_one({"user_id": str(user_id), "guilds.guild_id": str(guild_id)})

    if user:
        for guild in user['guilds']:
            if guild['guild_id'] == str(guild_id):
                tracked_manga = guild.get('manga_tracking', [])
                if tracked_manga:
                    manga_list = "\n".join([f"{manga['manga_name']}" for manga in tracked_manga])
                    await ctx.send(f"Here is the list of manga you are tracking:\n{manga_list}")
                else:
                    await ctx.send("You are not tracking any manga.")
    else:
        await ctx.send("You are not tracking any manga.")

# Simple ping command
@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('Pong!')

@bot.command(name='untrack')
async def untrack(ctx, *, manga_name: str ):
    user_id = ctx.author.id
    guild_id = ctx.guild.id

    mangas = trackManga(manga_name)
    title = (mangas[0])['title']
    link = (mangas[0])['link']

    #Query the database for the user
    user = user_collection.find_one({"user_id": str(user_id), "guilds.guild_id": str(guild_id)})

    if user:
        #Check if the manga is being tracked by the user
        for guild in user['guilds']:
            if guild['guild_id'] == str(guild_id):
                tracked_manga = guild.get('manga_tracking', [])
                if any(manga['manga_name'] == title for manga in tracked_manga):
                    user_collection.update_one(
                        {"user_id": str(user_id), "guilds.guild_id": str(guild_id)},
                        {"$pull": {"guilds.$.manga_tracking": {"manga_name": title}}}
                    )
                    await ctx.send(f"Stopped tracking {title} for user {ctx.author.display_name}.")
                else:
                    await ctx.send(f"{title} is not being tracked")
                break
    else:
        await ctx.send(f"User not found")

# Background task to check for chapter updates
async def check_chapter_updates():
    await bot.wait_until_ready()  # Wait until the bot has connected to Discord

    while not bot.is_closed():  # Keep running the task until the bot is closed
        checkManga()

        # if chapter:
        #     print(chapter)
        #     #Send message to the channel
        #     channel = bot.get_channel(809917094388039713)  # Ensure correct channel ID is used
        #     if channel:
        #         asyncio.run_coroutine_threadsafe(channel.send(url + chapter['link']), bot.loop)

        await asyncio.sleep(3600)  # Wait for 1 hour before checking again

# Event when the bot is ready
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    
    # for guild in bot.guilds:
    #     print(f"Connected to server: {guild.name} (ID: {guild.id})")
    bot.loop.create_task(check_chapter_updates())  # Start the background task

# Run the bot
bot.run(TOKEN)
