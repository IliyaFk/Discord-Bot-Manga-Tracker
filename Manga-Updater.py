import os
import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv
from pymongo import MongoClient
from MangaTracker import *
import re
from fuzzywuzzy import fuzz

#Get discord token from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN_DEV')

# Database Setup -- do I need this anymore??
MONGO_URI = os.getenv('MONGODB_TOKEN')
clientDB = MongoClient(MONGO_URI)
db = clientDB['DiscordTestDB']
#chapters_collection = db['chapters']
#chapters_collection.create_index([('number', 1)], unique=True)
user_collection = db['users']

################################ Delete specific chapter from database for debugging purposes ############################
#chapter_number_to_delete = 1135  # Change this to the chapter number you want to delete
#result = One_Piece.delete_one({'number': chapter_number_to_delete})
##########################################################################################################################

#Delete collection in the database
#mycol = db["Wistoria: Wand and Sword"]
#mycol.drop() 

# Function to check if inputed Manga Name is similar to another Manga program returns to track

#Site where I extract chapter info from
url = "https://mangafire.to"

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents, case_insensitive=True)

# Command to set the channel the bot can message in
@bot.command(name='setchannel')
@commands.has_permissions(administrator=True)
async def set_channel(ctx, channel: discord.TextChannel):
    guild_id = ctx.guild.id
    channel_id = channel.id

    #Query the database for the guild
    guild = user_collection.find_one({"guilds.guild_id": str(guild_id)})

    if guild:
        user_collection.update_one(
            {"guilds.guild_id": str(guild_id)},
            {"$set": {"guilds.$.channel_id": str(channel_id)}}
        )
        await ctx.send(f"Channel has been set to {channel.mention}.")
    else:
        user_collection.insert_one({
            "guilds": [
                {
                    "guild_id": str(guild_id),
                    "channel_id": str(channel_id)
                }
            ]
        })
        await ctx.send(f"Channel has been set to {channel.mention}.")


@set_channel.error
async def set_tracking_channel_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have admin permissions to use this command.")

async def manga_confirm(ctx, title, link):
    user_id = ctx.author.id
    guild_id = ctx.guild.id

    #Query the database for the user
    user = user_collection.find_one({"user_id": str(user_id), "guilds.guild_id": str(guild_id)})
    
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
                    if title not in existing_collections:
                        db.create_collection(title)
                        existingCollection(title,link)
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
        if title not in existing_collections:
            db.create_collection(title)
            existingCollection(title,link)
        await ctx.send(f"Started tracking {title} for user {ctx.author.display_name}.")


# Command to track a manga
@bot.command(name='track')
async def track(ctx, *, manga_name: str):
    # Reject links upfront
    if re.search(r'\b(?:https?://|www\.)\S+', manga_name, re.IGNORECASE):
        await ctx.send("Links are not allowed. Please enter a valid manga name.")
        return

    mangas = trackManga(manga_name)
    if not mangas:
        await ctx.send("Manga not found. Please enter a valid name.")
        return

    title = mangas[0]['title']
    link = mangas[0]['link']

    if fuzz.partial_ratio(manga_name.lower(), title.lower()) < 80:
        await ctx.send("Manga not found. Try again with a different name.")
        return

    await ctx.send(f"Did you mean {title}? (yes/no)")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        m = await bot.wait_for('message', check=check, timeout=30.0)

        if re.search(r'\b(?:https?://|www\.)\S+', m.content, re.IGNORECASE):
            await ctx.send("Links are not allowed. Please enter a valid manga name.")
            return

        user_input = m.content.lower()

        if user_input == 'yes':
            await manga_confirm(ctx, title, link)
        elif user_input == 'no':
            await ctx.send("Tracking request canceled. Use !track again if needed.")
        else:
            await ctx.send("Invalid response. Please reply with 'yes' or 'no'.")

    except asyncio.TimeoutError:
        await ctx.send('No response received. Cancelling request.')




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
    await bot.wait_until_ready()  # Wait until bot is connected

    while not bot.is_closed():
        new_chapters = checkManga()  # Get new chapters

        if not new_chapters:
            print("No new chapters found.")
        else:
            for chapter in new_chapters:
                chapter_title = chapter.get('title', 'Unknown Title')
                chapter_link = chapter.get('link', '')
                manga_name = chapter.get('manga_name', 'Unknown Manga')

                print(f"Preparing to send update for {manga_name} - {chapter_title}")

                # Fetch all users tracking this manga
                tracked_users = user_collection.find({"guilds.manga_tracking.manga_name": manga_name})
                print(tracked_users)

                notified_guilds = set() # Store guilds that have been notified to avoid duplicates

                for user in tracked_users:
                    print(f"Checking user {user['user_id']}...")  # Debugging step

                    for guild in user["guilds"]:
                        print(f"Checking guild ID: {guild['guild_id']}")  # Debugging step

                        if any(manga["manga_name"] == manga_name for manga in guild["manga_tracking"]):
                            guild_id = int(guild["guild_id"])
                            guild_obj = bot.get_guild(guild_id)

                            if not guild_obj:
                                print(f"⚠️ Guild {guild_id} not found. Is the bot in this server?")
                                continue

                            print(f"✅ Found guild: {guild_obj.name} (ID: {guild_id})")

                            if guild_id in notified_guilds:
                                print("⚠️ Already notified this guild. Skipping...")
                                continue

                            notified_guilds.add(guild_id)

                            # Check available text channels
                            available_channels = [ch for ch in guild_obj.text_channels if ch.permissions_for(guild_obj.me).send_messages]
                            if not available_channels:
                                print(f"⚠️ No channels available to send messages in {guild_obj.name}. Skipping...")
                                continue

                            # Choose the first available text channel
                            # Try to get the preferred tracking channel from the database
                            guild_data = user_collection.find_one(
                                {"guilds.guild_id": str(guild_id)},
                                {"guilds.$": 1}  # This projects only the matching guild
                            )

                            if guild_data and "guilds" in guild_data:
                                preferred_channel_id = guild_data["guilds"][0].get("channel_id")
                            else:
                                preferred_channel_id = None

                            # Fetch the preferred channel if it exists
                            channel = bot.get_channel(int(preferred_channel_id)) if preferred_channel_id else None

                            if not channel:
                                print(f"⚠️ Preferred channel not set or bot lacks access in {guild_obj.name}.")
                                continue

                            print(f"✅ Using channel: {channel.name} (ID: {channel.id}) in {guild_obj.name}")

                            # Send message
                            chapter_title = chapter_title['title']  # Extract the title from the dictionary
                            message = f"📢 New chapter released: **{manga_name} - {chapter_title}**\n📖 Read here: {url}{chapter_link}"

                            await channel.send(message)
                            print(f"✅ Sent update in {guild_obj.name}: {message}")

        await asyncio.sleep(3600)  # Wait 1 hour before checking again

# Event when the bot is ready
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print("Registered commands:", [cmd.name for cmd in bot.commands])
    # for guild in bot.guilds:
    #     print(f"Connected to server: {guild.name} (ID: {guild.id})")
    bot.loop.create_task(check_chapter_updates())  # Start the background task

# Run the bot
bot.run(TOKEN)
