from updateData import getData, updateData, pasteData
from bs4 import BeautifulSoup
import os
from inspect import getsourcefile
from os.path import abspath
import math
import datetime
import pytz
import random
import traceback
import asyncio

from scraper import retrieve_webpage

random.seed()

#URL = "https://hypixel.net/threads/hypixel-mafia-l-died-carpe-jugulum-game-c-day-1.4439668"
#set active directory to app location
directory = abspath(getsourcefile(lambda: 0))
#check if system uses forward or backslashes for writing directories
if (directory.rfind("/") != -1):
  newDirectory = directory[:(directory.rfind("/") + 1)]
else:
  newDirectory = directory[:(directory.rfind("\\") + 1)]
os.chdir(newDirectory)


def getPlayerlist(gameLetter):
  playerlist = []

  response = retrieve_webpage(getData("url" + gameLetter))

  soup = BeautifulSoup(response, 'html.parser')
  #print(soup.encode("utf-8"))
  message = soup.find_all("article", class_='message')[0]
  text = (message.find(class_='bbWrapper')).get_text()
  text = text[text.lower().find("spoiler: living players"):text.lower().
              find("spoiler: dead players")]
  #print(text.encode("utf-8"))

  while (text.find("@") != -1):
    text = text[text.find("@"):]
    player = text[text.find("@") + 1:text.find('\n')].replace(" ", "").replace(
      "\u200b", "")
    print(player)
    playerlist.append(player)
    text = text[text.find('\n'):]
  return playerlist


def Sort_Tuple(tup):
  return sorted(tup, key=lambda x: (-x[1], x[0]))


def rankActivity(gameLetter, activeOnly=True):
  listofposts = getData("listofposts" + gameLetter)
  playerlist = getPlayerlist(gameLetter)
  gameLetter = gameLetter.upper()
  sortedISOs = {}
  rankings = []
  for post in listofposts:
    if post[0] not in sortedISOs.keys():
      sortedISOs.update({post[0]: [post]})
    else:
      sortedISOs[post[0]].append(post)
  print("Sorted posts.")
  format = "**Player activity rankings:\n**"
  for player in sortedISOs.keys():
    if player in playerlist or activeOnly == False:
      rankings.append((player, len(sortedISOs[player])))

  rankings = Sort_Tuple(rankings)
  format = "**Activity rankings for game {}:**\n".format(gameLetter)
  for player in rankings:
    format = format + "{}: {} posts\n".format(player[0], player[1])
  return (format)


async def getISO(URL, listofposts):
  firstpost = 1
  if listofposts != []:
    firstpost = listofposts[-1][1] + 1  #firstpost that the bot should scrape

  class post:  #object to store post data

    def __init__(self, user, number, text, id, date, html):
      self.user = user
      self.number = number
      self.text = text
      self.id = id
      self.date = date
      self.HTML = html

  scrapedPosts = []  #post objects stored here

  page = math.ceil(firstpost / 20.0)

  print("Starting at page " + str(page) + ". First post: " + str(firstpost))
  oldtag = 0
  while (
      page <= 1000
  ):  #the bot automatically ends at the end of thread; this is a failsafe
    print(page, end="   first post number: ")
    await asyncio.sleep(1.5 + random.random())
    try:
      response = retrieve_webpage(URL + "page-" + str(page))
    except:
      print("Response error! Returned scrapped posts.")
      traceback.print_exc()
      break
  # driver.get(URL+"/page-"+str(page))
  #response = driver.page_source
    soup = BeautifulSoup(response, 'html.parser')

    firstpostnumber = int(
      soup.find("article", class_='message').find(
        "ul", {
          "class":
          "message-attribution-opposite message-attribution-opposite--list"
        }).text.replace(",", "").replace("\n", "").replace(
          "#", ""))  #first post number of the page
    print(firstpostnumber)
    if firstpostnumber == oldtag:
      print("Detected end of thread.")
      break
    oldtag = firstpostnumber

    for message in soup.find_all("article", class_='message'):
      quotes = []
      for quote in (message.find_all("blockquote")):
        quotes.append(quote.get_text())

      username = message.find(class_='username').get_text().replace(
        "\n", "").replace(" ", "")
      postnumber = int(
        message.find(
          "ul", {
            "class":
            "message-attribution-opposite message-attribution-opposite--list"
          }).text.replace("\n", "").replace(",", "").replace("#", ""))
      timestamp = int(message.find("time").get("data-time"))

      # Get a timezone object for the desired timezone
      tz = pytz.timezone('US/Eastern')

      # Convert the timestamp to a datetime object
      dt = datetime.datetime.fromtimestamp(timestamp, tz)
      postdate = dt.strftime('%Y-%m-%d %H:%M %Z')

      text = (message.find(class_='bbWrapper')).get_text()

      for quote_original in quotes:
        #print(quote)
        quote = quote_original[:200]

        if (quote.find("said") == -1):
          quoted_player = ""
        else:
          quoted_player = quote[:quote.find("said") - 1]
        quote_html = """
          <aside class="quote">
            <p class="quote-label">{}</p>
            <p class="quote-text">{}</p>

        </aside>""".format(quoted_player, quote[quote.find("said") + 5:])
        text = text.replace(quote_original, quote_html)
      text = text.replace("\n", "<br>")
      text = text.replace("Click to expand...", "")
      while (text.find("<br><br><br>") != -1):
        text = text.replace("<br><br>", "<br>")
      postid = message.find("a", rel='nofollow')["href"]
      postid = int(postid[postid.find("post-") + 5:])

      if postnumber >= firstpost:
        scrapedPosts.append(post(username, postnumber, text, postid, postdate, str(message)))

    page = page + 1

  for post in scrapedPosts:  #when all posts are scraped, convert list of objects into list of lists
    listofposts.append([post.user, post.number, post.text, post.id, post.date, post.HTML])

  return (listofposts)


async def updateISO(gameLetter):
  gameLetter = gameLetter.upper()
  data = await getISO(getData("url" + gameLetter),
                      getData("listofposts" + gameLetter))
  updateData("listofposts" + gameLetter, data)
  print("Game {} update complete. Database contains {} posts.".format(
    gameLetter, len(getData("listofposts" + gameLetter))))
  return ("Update complete. Game {} database contains {} posts.".format(
    gameLetter, len(getData("listofposts" + gameLetter))))


def wipeISO(gameLetter):
  updateData("listofposts{}".format(gameLetter), [])
  print("Wiped ISO data for game {}.".format(gameLetter))
  return


def collectISOinList(gameLetter, player, lowerbound=-1, upperbound=100000):
  posts = []

  for post in getData("listofposts" + gameLetter):
    pageNumber = math.ceil(int(post[1]) / 20)
    if (post[0].lower() == player.lower() and pageNumber >= lowerbound
        and pageNumber <= upperbound):
      posts.append(post)
  return (posts)


def collectAllPosts(gameLetter, lowerbound=-1, upperbound=10000000):
  posts = []
  i = 0
  for post in getData("listofposts" + gameLetter):
    pageNumber = math.ceil(int(post[1]) / 20)
    if (pageNumber >= lowerbound and pageNumber <= upperbound):
      i = i + 1
      posts.append(post)
  return (posts)


def collectAllISOs(gameLetter, lowerbound=-1, upperbound=1000000):
  gameLetter = gameLetter.upper()
  sortedISOs = {}
  for post in getData("listofposts" + gameLetter):
    if post[0] not in sortedISOs.keys():
      sortedISOs.update({post[0]: [post]})
    else:
      sortedISOs[post[0]].append(post)
  print("Sorted posts.")
  format = "List of collected ISOs: \n"
  for player in sortedISOs.keys():
    ISO = sortedISOs[player]
    format = format + "{}".format(ISO[0][0]) + ": "
    quotes = ""
    for post in ISO:
      quotes = quotes + """[QUOTE="{}, post: {}, member: 1"]{}[/QUOTE]\n""".format(
        post[0], post[3], post[2])
    format = format + pasteData(quotes, "ONE_DAY") + "\n"

  return (format)


def playerHasPosted(gameLetter, player):
  posts = getData("listofposts" + gameLetter)
  for post in posts:
    if (post[0].lower() == player.lower()):
      return (True)
  return (False)


def listPlayers(gameLetter):
  players = []
  for post in getData("listofposts" + gameLetter):
    if post[0] not in players:
      players.append(post[0])
  return (players)


def clearQuotes(posts):
  cleaned = []
  for comment in posts:
    i = 0
    text = comment[2]
    while (text.find("""<aside class="quote">""") != -1):
      tag1 = text.find("""<aside class="quote">""")
      tag2 = text.find("</aside>")
      text = text.replace(text[tag1:tag2 + 8], "")
      i = i + 1
      if (i > 1000):
        print("Stuck in quotes loop")
        break
    cleaned.append([comment[0], comment[1], text, comment[3], comment[4]])
  return (cleaned)
