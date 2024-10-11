import os
import discord
import asyncio
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

#Database Setup
MONGO_URI = os.getenv('MONGODB_TOKEN')
clinetDB = MongoClient(MONGO_URI)
db = clinetDB['DiscordDB']
chapters_collection = db['chapters']
chapters_collection.create_index([('number', 1)], unique=True)

#Line to delete entries in chapters_collection for debugging purposes
#chapters_collection.delete_many({})

response = requests.get('https://mangafire.to/manga/one-piece.dkw')
soup = BeautifulSoup(response.content,'html.parser')

#Discord Bot Setup

intents = discord.Intents.default()

client = discord.Client(intents=intents)

def store_chapter(chapter):
    try:
        chapters_collection.insert_one(chapter)
        print(f"Chapter {chapter['number']} added to the database.")
    except DuplicateKeyError:
        print(f"Chapter {chapter['number']} already exists in the database.")


async def check_chapter_updates():
    await client.wait_until_ready()  # Wait until the bot has connected to Discord
    channel = client.get_channel(809917094388039713)  # Replace CHANNEL_ID with your channel's ID


    while not client.is_closed():  # Keep running the task until the bot is closed

        #Scraping Logic
        chapters = []
        number = 0
        #Get the latest chapter from the mangafire.to website
        elem = soup.find('li', class_='item')
        if elem:
            chapter_info = elem.find('span').get_text() if elem.find('span') else None
            chapter_link = elem.find('a')['href'] if elem.find('a') else None
            chapters.append({'number': number,'title': chapter_info, 'link': chapter_link})
        latest_chapter = chapters[0]
        
        last_chapter = chapters_collection.find_one({}, sort=[('number', -1)])  #Last chapter entry in the database
        print(last_chapter)

        #Check if the latest chapter from the last time website scraped is a new chapter not in the database
        #If it is then add it to the database
        #Also want to add a discord message here to alert that a chapter released
        if (latest_chapter)['title'] != last_chapter['title']:
            latest_chapter['number'] = latest_chapter['number'] + 1
            store_chapter(latest_chapter)


        ######################################################################################################################################
       
        #This snippet should be used when first scraping data for a new manga and adding all chapter entries to the database ############
        #Not being used  right now because chapter entries already for one piece ##############
        #Will work on this when adding funtionality to request tracking a new manga #############
        # for elem in soup.find_all('li',class_='item'):
        #     chapter_info = elem.find('span').get_text() if elem.find('span') else None
        #     chapter_link = elem.find('a')['href'] if elem.find('a') else None
        #     chapters.append({'number': number,'title': chapter_info, 'link': chapter_link})
            #store_chapter(chapters[number])
            #number+=1

        #To align the id numbers and chapter numbers together
        # for chapter in reversed(chapters):
        #     chapter['number'] = number
        #     store_chapter(chapter)
        #     number+=1

        #######################################################################################################################################

        #await channel.send(chapters[0][1])  # Send the latest chapter for now ---- Latest link is stored under chapters[0][1]
        await asyncio.sleep(3600)  # Wait for 3600 seconds (1 hour) or whatever time I set it to be later


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    client.loop.create_task(check_chapter_updates())

client.run(TOKEN)
