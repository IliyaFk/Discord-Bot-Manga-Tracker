import os
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv('MONGODB_TOKEN')
clientDB = MongoClient(MONGO_URI)
db = clientDB['DiscordDB']
chapters_collection = db['chapters']
chapters_collection.create_index([('number', 1)], unique=True)
user_collection = db['users']
manga_names = []

link = "https://mangafire.to/filter?keyword="

response = requests.get('https://mangafire.to/manga/one-piece.dkw')
soup = BeautifulSoup(response.content, 'html.parser')

#Find manga and link based on user input gathered from track command
def trackManga(mangaName):
    filter = requests.get(link+mangaName)
    soupy = BeautifulSoup(filter.content, 'html.parser')
    elem = soupy.find('div', class_='inner')
    manga = []
    if elem:
        manga_title = elem.find_all('a')[1].text if len (elem.find('a')) >= 1 else None
        manga_link = elem.find('a')['href'] if elem.find('a') else None
        manga.append({'title': manga_title, 'link': manga_link})
    return manga

def store_chapter(chapter):
    try:
        chapters_collection.insert_one(chapter)
        print(f"Chapter {chapter['number']} added to the database.")
        return chapter
    except DuplicateKeyError:
        print(f"Chapter {chapter['number']} already exists in the database.")
        return False

def checkCollections():
    existing_collections = db.list_collection_names()
    print(manga_names)
    for manga in manga_names:
        manga_name = manga['name']
        if manga_name in existing_collections:
            print(f"Collection for '{manga_name}' already exists.")
        else:
            # Create collection if it doesn't exist
            db.create_collection(manga_name)
            print(f"Created collection for '{manga_name}'.")

def checkManga():
    all_users = user_collection.find()

    for user in all_users:
        user_id = user["user_id"]
        print(f"User ID: {user_id}")

        for guild in user.get("guilds", []):
            guild_id = guild["guild_id"]
            print(f" Guild ID: {guild_id}")

        for manga in guild.get("manga_tracking", []):
            manga_name = manga["manga_name"]
            manga_link = manga.get("manga_link", "No link available") #in case a link was never stored
            if manga_name not in manga_names:
                manga_names.append({'name':manga_name, 'link': manga_link})
            print(f" Manga: {manga_name}, Link: {manga_link}")
        
    checkCollections()

def checkUpdates(url):
    checkManga()
    # chapters = []
    # number = 0
    # # Get the latest chapter from the website
    # elem = soup.find('li', class_='item')
    # if elem:
    #     chapter_info = elem.find('span').get_text() if elem.find('span') else None
    #     chapter_link = elem.find('a')['href'] if elem.find('a') else None
    #     chapters.append({'number': number, 'title': chapter_info, 'link': chapter_link})
    # latest_chapter = chapters[0]

    # print(url + latest_chapter['link'])

    # last_chapter = chapters_collection.find_one({}, sort=[('number', -1)])  # Last chapter entry in the database
    # print(last_chapter)

    # Check if the latest chapter is new
    # if latest_chapter['title'] != last_chapter['title']:
    #     latest_chapter['number'] = last_chapter['number'] + 1  # Increment chapter number
    #     return store_chapter(latest_chapter)
    # return False