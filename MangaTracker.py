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
#chapters_collection = db['chapters']
#chapters_collection.create_index([('number', 1)], unique=True)
user_collection = db['users']
manga_names = []

link = "https://mangafire.to/filter?keyword="

#response = requests.get('https://mangafire.to/manga/one-piece.dkw')
#soup = BeautifulSoup(response.content, 'html.parser')

#Find manga and link based on user input gathered from track command
def trackManga(mangaName):
    filter = requests.get(link+mangaName)
    soupy = BeautifulSoup(filter.content, 'html.parser')

    main_section = soupy.find('main')
    elem = main_section.find('div', class_='inner')
    #elem = soupy.find('div', class_='inner')
    manga = []
    if elem:
        manga_title = elem.find_all('a')[1].text if len (elem.find('a')) >= 1 else None
        manga_link = elem.find('a')['href'] if elem.find('a') else None
        manga.append({'title': manga_title, 'link': manga_link})
    return manga

def store_chapter(collection_name,chapter):
    try:
        db[collection_name].insert_one(chapter)
        if db[collection_name].count_documents({}) > 1:
            db[collection_name].delete_one({'number':0})
        print(f"Latest chapter added to the database.")
        return chapter
    except DuplicateKeyError:
        print(f"Latest chapter already exists in the database.")
        return False

def checkCollections():
    existing_collections = db.list_collection_names()
    print(manga_names)
    for manga in manga_names:
        manga_name = manga['name']
        manga_link = manga['link']
        if manga_name in existing_collections:
            print(f"Collection for '{manga_name}' already exists.")
            print(f" Manga: {manga_name}, Link: {manga_link}")
            existingCollection(manga_name, manga_link)
        else:
            # Create collection if it doesn't exist
            db.create_collection(manga_name)
            print(f"Created collection for '{manga_name}'.")
            existingCollection(manga_name, manga_link)

def existingCollection(manga_name, manga_link):
    response = requests.get('https://mangafire.to'+manga_link)
    soup = BeautifulSoup(response.content, 'html.parser')
    collection_name = db[manga_name]
    chapters = []
    number = 0
    # Get the latest chapter from the website
    print(f"Fetching manga page: https://mangafire.to{manga_link}")
    print(f"Response Status Code: {response.status_code}")

    elem = soup.find('li', class_='item')
    if elem:
        chapter_info = elem.find('span').get_text() if elem.find('span') else None
        chapter_link = elem.find('a')['href'] if elem.find('a') else None
        chapters.append({'number': number, 'title': chapter_info, 'link': chapter_link})
    latest_chapter = chapters[0]

    print(latest_chapter['title'] + latest_chapter['link'])

    last_chapter = collection_name.find_one({}, sort=[('number', -1)])  # Last chapter entry in the database
    print(last_chapter)

    #Check if the latest chapter is new
    if db[manga_name].count_documents({}) == 0:
        return store_chapter(manga_name,latest_chapter)

    elif latest_chapter['title'] != last_chapter['title']:
        latest_chapter['number'] = last_chapter['number'] + 1  # Increment chapter number
        return store_chapter(manga_name,latest_chapter)
    return False

def checkManga():
    new_chapters = []  # Store newly detected chapters

    all_users = user_collection.find()
    for user in all_users:
        for guild in user.get("guilds", []):
            for manga in guild.get("manga_tracking", []):
                manga_name = manga["manga_name"]
                manga_link = manga.get("manga_link", "No link available")  # In case a link was never stored
                
                if manga_name not in manga_names:
                    manga_names.append({'name': manga_name, 'link': manga_link})
                
                # Check for new chapters
                new_chapter = existingCollection(manga_name, manga_link)  # Returns latest chapter if new
                if new_chapter:
                    new_chapters.append({
                        "manga_name": manga_name,  # Appending manga name
                        "title": new_chapter,      # Title or chapter name
                        "link": manga_link         # Link to the chapter
                })
    print(new_chapters)
    return new_chapters  # Return list of new chapters