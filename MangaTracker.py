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

link = "https://mangafire.to/filter?keyword="

response = requests.get('https://mangafire.to/manga/one-piece.dkw')
soup = BeautifulSoup(response.content, 'html.parser')

def trackManga(mangaName):
    filter = requests.get(link+mangaName)
    soupy = BeautifulSoup(filter.content, 'html.parser')
    elem = soupy.find('div', class_='inner')
    manga = []
    if elem:
        manga_title = elem.find_all('a')[1].text if len (elem.find('a')) >= 1 else None
        manga_link = elem.find('a')['href'] if elem.find('a') else None
        manga.append({'title': manga_title, 'link': manga_link})
    #print(mangaName)
    #print(manga)
    return manga

def store_chapter(chapter):
    try:
        chapters_collection.insert_one(chapter)
        print(f"Chapter {chapter['number']} added to the database.")
        return chapter
    except DuplicateKeyError:
        print(f"Chapter {chapter['number']} already exists in the database.")
        return False

def checkUpdates(url):
    chapters = []
    number = 0
    # Get the latest chapter from the website
    elem = soup.find('li', class_='item')
    if elem:
        chapter_info = elem.find('span').get_text() if elem.find('span') else None
        chapter_link = elem.find('a')['href'] if elem.find('a') else None
        chapters.append({'number': number, 'title': chapter_info, 'link': chapter_link})
    latest_chapter = chapters[0]

    print(url + latest_chapter['link'])

    last_chapter = chapters_collection.find_one({}, sort=[('number', -1)])  # Last chapter entry in the database
    print(last_chapter)

    # Check if the latest chapter is new
    if latest_chapter['title'] != last_chapter['title']:
        latest_chapter['number'] = last_chapter['number'] + 1  # Increment chapter number
        return store_chapter(latest_chapter)
    return False