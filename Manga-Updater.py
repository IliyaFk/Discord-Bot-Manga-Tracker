import os
import discord
import asyncio
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

response = requests.get('https://mangafire.to/manga/one-piece.dkw')
soup = BeautifulSoup(response.content,'html.parser')

chapters = []

for elem in soup.find_all('li',class_='item'):
    chapter_info = elem.find('span').get_text() if elem.find('span') else None
    chapter_link = elem.find('a')['href'] if elem.find('a') else None
    chapters.append([chapter_info,chapter_link])

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()

client = discord.Client(intents=intents)

async def check_chapter_updates():
    await client.wait_until_ready()  # Wait until the bot has connected to Discord
    channel = client.get_channel(809917094388039713)  # Replace CHANNEL_ID with your channel's ID

    while not client.is_closed():  # Keep running the task until the bot is closed
        await channel.send(chapters[0][1])  # Send the latest chapter for now ---- Latest link is stored under chapters[0][1]
        await asyncio.sleep(3600)  # Wait for 3600 seconds (1 hour)


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    client.loop.create_task(check_chapter_updates())

client.run(TOKEN)
