from bs4 import BeautifulSoup
import time
import datetime
import random
from updateData import getData, updateData
import traceback
import math
import asyncio
from iso import getPlayerlist, updateISO, collectAllPosts, clearQuotes
import discord

from scraper import retrieve_webpage


class voteObject:

  def __init__(self, player, target, url, postnum):
    self.player = player
    self.target = target
    self.url = url
    self.postnum = postnum


class phaseObject:

  def __init__(self, postnum, phase_name):
    self.postnum = postnum
    self.phase_name = phase_name


def createPhase(gameLetter, postnum=-1, phase_name=""):
  #get the current phases from db
  phases = getData("phases" + gameLetter)

  # ensure the phase's name and post number are unique
  for phase in phases:
    if phase[0] == postnum or phase[1] == phase_name:
      return None

  listofphases = []
  for phase in phases:  #convert list of objects into list of lists
    listofphases.append([phase[0], phase[1]])

  #create new phase
  listofphases.append([postnum, phase_name])

  updateData("phases" + gameLetter, listofphases)
  return


def removePhase(gameLetter, phase_name):
  # get the current phases from the db
  phases = getData("phases" + gameLetter)

  # find the phase to remove
  for phase in phases:
    if phase[1] == phase_name:
      # remove the phase from the list
      phases.remove(phase)
      break

  listofphases = []
  for phase in phases:  #convert list of objects into list of lists
    listofphases.append([phase[0], phase[1]])
  updateData("phases" + gameLetter, listofphases)
  return


def updateVotecount(votecount, player, target, url, postnum):
  for vote in votecount:
    if vote.player == player:
      votecount.remove(vote)
  votecount.append(voteObject(player, target, url, postnum))
  return (votecount)


def collectVoteHistory(gameLetter, firstPost=-1, lastPost=100000):
  votes = []

  for vote in getData("votehistory" + gameLetter):
    postnum = int(vote[3])
    if (postnum >= firstPost and postnum <= lastPost):
      votes.append(vote)
  return (votes)


# Given a postnum, this function does the following:
# 1. Finds the phase with the largest postnum not exceeding the given postnum
# 2. Finds the list of votes placed between the phase's postnum and the given postnum
def getVotesByPostnum(gameLetter, postnum):
  list_of_aliases = getData("list_of_aliases")

  # Get all phases
  phases = getData("phases" + gameLetter)
  # Loop through phases, store the largest postnum not exceeding the given postnum
  phase_start_postnum = 0
  phase_name = ""
  for phase in phases:
    if phase[0] <= postnum and phase[0] > phase_start_postnum:
      phase_start_postnum = phase[0]
      phase_name = phase[1]

  # Find the list of votes between the phase's postnum and the given postnum
  votes = getData("votehistory" + gameLetter)
  votecount = []
  for vote in votes:
    if vote[3] >= phase_start_postnum and vote[3] <= postnum:
      if (vote[1].lower() in list_of_aliases.keys()):
        vote[1] = list_of_aliases[vote[1].lower()]

      votecount = updateVotecount(votecount, vote[0], vote[1].replace(" ", ''),
                                  vote[2], vote[3])
      # Hammer check would go here but is currently disabled as this breaks when playerlist is unknown.

  return phase_name, votecount


async def formatRetrospectiveVCDiscord(gameLetter, postnum):
  phase_name, votecount = getVotesByPostnum(gameLetter, postnum)
  text = phase_name + printVotecount(votecount)
  return (discord.Embed(color=discord.Color.green(), description=text))


def formatRetrospectiveVCWebsite(gameLetter, postnum):
  phase_name, votecount = getVotesByPostnum(gameLetter, postnum)
  text = printVotecountWebsite(votecount, phase_name)
  return text


def formatVotecount(
  votes
):  #generate the votecount, in format {"name":[list of players], "name":[list of players]}
  votecount = {}
  for vote in votes:
    if vote.target in votecount.keys():
      votecount[vote.target].append(vote)
    else:
      votecount[vote.target] = [vote]
  return (votecount)


def printVotecount(votes):

  votecount = formatVotecount(votes)
  text = " Votecount:\n"
  for candidate in votecount.keys():
    if (candidate != "Not voting"):
      try:
        inc = getData("incrementsA")[candidate.lower()]
      except:
        inc = 0
      text = text + "({}) ".format(len(votecount[candidate]) +
                                   inc) + candidate + ": "
      for voter in votecount[candidate]:
        text = text + "[{}]({})".format(voter.player, voter.url) + ", "
      text = text[:-2] + '\n'

  incs = getData("incrementsA")
  for player in incs.keys():
    if player not in votecount.keys() and incs[player] != 0:
      text = text + "({}) {}: ???\n".format(incs[player], player)
  try:
    candidate = "Not voting"
    text = text + "({}) ".format(len(votecount[candidate])) + candidate + ": "
    for voter in votecount[candidate]:
      text = text + voter.player + ", "
    text = text[:-2] + '\n'
  except:
    print("All players are voting.")
  return (text)


def printVotecountWebsite(votes, phase_name):
  text = '<p style="text-align: center"><strong><span style="font-size:22px;">'
  text += phase_name + '</span></strong></p>'

  votecount = formatVotecount(votes)

  for candidate in votecount.keys():
    text = text + "<tr><td><b>{}</b></td> ".format(len(
      votecount[candidate])) + "<td><b>" + candidate + "</td><td><b>"
    for voter in votecount[candidate]:
      text = text + "<a href='{}'>{}</a>, ".format(voter.url, voter.player)
    text = text[:-2] + '</b></td></tr>'
  return text


def checkForHammer(
  votes
):  #return a player name if a player has been hammered, return False if no one has been hammered.
  votecount = formatVotecount(votes)
  for candidate in votecount:
    try:
      inc = getData("incrementsA")[candidate.lower()]
    except:
      inc = 0
    if candidate != "Not voting" and len(
        votecount[candidate]) + inc >= math.ceil((len(votes) + 1) / 2):
      return (candidate)
  return (False)


async def updateVoteHistory(gameLetter):
  try:

    gameLetter = gameLetter.upper()
    URL = getData("url" + gameLetter)
    votes = []
    list_of_aliases = getData("list_of_aliases")

    #get list of alive voters:
    response = retrieve_webpage(URL)
    soup = BeautifulSoup(response, 'html.parser')
    print(soup)
    message = soup.find_all("article", class_='message')[0]
    text = (message.find(class_='bbWrapper')).get_text()
    text = text[text.lower().find("spoiler: living players"):text.lower().
                find("spoiler: dead players")]
    #print(text.encode("utf-8"))

    playerlist = getPlayerlist(gameLetter)

    if playerlist == []:
      return (discord.Embed(
        color=discord.Color.red(),
        description=
        "List of living players is blank - did you format it properly? See /help for info."
      ))

    updateData("playerlist" + gameLetter, playerlist)
    print(playerlist)
    await updateISO(gameLetter)
    print("Getting posts.")
    posts = collectAllPosts(gameLetter, 0, 10000)
    print("Clearing quotes...")
    posts = clearQuotes(posts)
    print("Got posts. Updating votes database...")
    for post in posts:
      voter = post[0]
      post_url = URL + "post-" + str(post[3])
      post_num = post[1]
      text = post[2].lower()
      tag1 = text.rfind("[vote]")
      tag2 = text.rfind("[/vote]")

      if (tag2 > tag1 and tag2 != -1 and tag1 != -1):
        target = (text[tag1 + 6:tag2]).strip().replace("@", "")
        #CHECK FOR ALIASES
        if (target.lower() in list_of_aliases.keys()):
          target = list_of_aliases[target.lower()]

        votes.append(
          voteObject(voter, target.replace(" ", ''), post_url, post_num))

    listofvotes = []
    for vote in votes:  #when all posts are scraped, convert list of objects into list of lists
      listofvotes.append([vote.player, vote.target, vote.url, vote.postnum])
    updateData("votehistory" + gameLetter, listofvotes)
    text = "Finished updating vote history."
    return (discord.Embed(color=discord.Color.green(), description=text))

  except:
    traceback.print_exc()
    errorMessage = traceback.format_exc()
    #pasteURL = pasteData(errorMessage + "\n\n\n\n\n" + str(soup))
    #updateData(("Error " + datetime.datetime.now().isoformat()),pasteURL)
    return (discord.Embed(
      color=discord.Color.red(),
      description=
      """Sorry, there was an error. Is the URL correct, and are the page number(s) right?
    \nIt's also possible the Hypixel website is a bit slow; check back in a bit.\n\nError message: """
      + errorMessage))


async def getStoredVotecount(gameLetter, post1, post2):
  try:
    URL = getData("url" + gameLetter)

    random.seed()

    votecount = []
    list_of_aliases = getData("list_of_aliases")
    #get list of alive voters:
    response = retrieve_webpage(URL)

    soup = BeautifulSoup(response, 'html.parser')
    cycle = ""
    print(soup)
    title = soup.find(class_="p-title-value").get_text()
    if (title.lower().find("day") != -1):
      cycle = "Day " + title[title.lower().find("day") +
                             4:title.lower().find("day") + 5]
    elif (title.lower().find("night") != -1):
      cycle = "Night " + title[title.lower().find("night") +
                               6:title.lower().find("night") + 7]
    print(title)
    message = soup.find_all("article", class_='message')[0]
    text = (message.find(class_='bbWrapper')).get_text()
    text = text[text.lower().find("spoiler: living players"):text.lower().
                find("spoiler: dead players")]
    #print(text.encode("utf-8"))

    playerlist = getPlayerlist(gameLetter)

    if playerlist == []:
      return (discord.Embed(
        color=discord.Color.red(),
        description=
        "List of living players is blank - did you format it properly? See /help for info."
      ))

    for player in playerlist:
      updateVotecount(votecount, player, "Not voting", 0, 0)

    updateData("playerlist" + gameLetter, playerlist)
    print(playerlist)
    await updateISO(gameLetter)
    print("Getting posts.")
    posts = collectAllPosts(gameLetter, page1, page2)
    print("Clearing quotes...")
    posts = clearQuotes(posts)
    print("Got posts. Calculating VC...")
    for post in posts:
      voter = post[0]
      post_url = URL + "post-" + str(post[3])
      post_num = post[1]
      text = post[2].lower()
      tag1 = text.rfind("[vote]")
      tag2 = text.rfind("[/vote]")

      if (tag2 > tag1 and tag2 != -1 and tag1 != -1) and voter in playerlist:
        target = (text[tag1 + 6:tag2]).strip().replace("@", "")
        #CHECK FOR ALIASES
        if (target.lower() in list_of_aliases.keys()):
          target = list_of_aliases[target.lower()]

        votecount = updateVotecount(votecount, voter, target.replace(" ", ''),
                                    post_url, post_num)
        if checkForHammer(votecount) != False:
          text = printVotecount(votecount)
          text = text + "\n**{} has been hammered.** Note that hammer checks can be disabled using the $votecount hammer off command.".format(
            checkForHammer(votecount))
          return (discord.Embed(color=discord.Color.green(), description=text))

    text = cycle + printVotecount(votecount)
    return (discord.Embed(color=discord.Color.green(), description=text))
  except:
    traceback.print_exc()
    errorMessage = traceback.format_exc()
    #pasteURL = pasteData(errorMessage + "\n\n\n\n\n" + str(soup))
    #updateData(("Error " + datetime.datetime.now().isoformat()),pasteURL)
    return (discord.Embed(
      color=discord.Color.red(),
      description=
      """Sorry, there was an error. Is the URL correct, and are the page number(s) right?
    \nIt's also possible the Hypixel website is a bit slow; check back in a bit.\n\nError message: """
      + errorMessage))


async def getVotecount(gameLetter, page1, page2=1000):
  try:
    URL = getData("url" + gameLetter)

    random.seed()

    votecount = []
    list_of_aliases = getData("list_of_aliases")
    #get list of alive voters:
    response = retrieve_webpage(URL)

    soup = BeautifulSoup(response, 'html.parser')
    cycle = ""
    print(soup)
    title = soup.find(class_="p-title-value").get_text()
    if (title.lower().find("day") != -1):
      cycle = "Day " + title[title.lower().find("day") +
                             4:title.lower().find("day") + 5]
    elif (title.lower().find("night") != -1):
      cycle = "Night " + title[title.lower().find("night") +
                               6:title.lower().find("night") + 7]
    print(title)
    message = soup.find_all("article", class_='message')[0]
    text = (message.find(class_='bbWrapper')).get_text()
    text = text[text.lower().find("spoiler: living players"):text.lower().
                find("spoiler: dead players")]
    #print(text.encode("utf-8"))

    playerlist = getPlayerlist(gameLetter)

    if playerlist == []:
      return (discord.Embed(
        color=discord.Color.red(),
        description=
        "List of living players is blank - did you format it properly? See /help for info."
      ))

    for player in playerlist:
      updateVotecount(votecount, player, "Not voting", 0, 0)

    updateData("playerlist" + gameLetter, playerlist)
    print(playerlist)
    await updateISO(gameLetter)
    print("Getting posts.")
    posts = collectAllPosts(gameLetter, page1, page2)
    print("Clearing quotes...")
    posts = clearQuotes(posts)
    print("Got posts. Calculating VC...")
    for post in posts:
      voter = post[0]
      post_url = URL + "post-" + str(post[3])
      post_num = post[1]
      text = post[2].lower()
      tag1 = text.rfind("[vote]")
      tag2 = text.rfind("[/vote]")

      if (tag2 > tag1 and tag2 != -1 and tag1 != -1) and voter in playerlist:
        target = (text[tag1 + 6:tag2]).strip().replace("@", "")
        #CHECK FOR ALIASES
        if (target.lower() in list_of_aliases.keys()):
          target = list_of_aliases[target.lower()]

        votecount = updateVotecount(votecount, voter, target.replace(" ", ''),
                                    post_url, post_num)
        if checkForHammer(votecount) != False:
          text = printVotecount(votecount)
          text = text + "\n**{} has been hammered.** Note that hammer checks can be disabled using the $votecount hammer off command.".format(
            checkForHammer(votecount))
          return (discord.Embed(color=discord.Color.green(), description=text))

    text = cycle + printVotecount(votecount)
    return (discord.Embed(color=discord.Color.green(), description=text))
  except:
    traceback.print_exc()
    errorMessage = traceback.format_exc()
    #pasteURL = pasteData(errorMessage + "\n\n\n\n\n" + str(soup))
    #updateData(("Error " + datetime.datetime.now().isoformat()),pasteURL)
    return (discord.Embed(
      color=discord.Color.red(),
      description=
      """Sorry, there was an error. Is the URL correct, and are the page number(s) right?
    \nIt's also possible the Hypixel website is a bit slow; check back in a bit.\n\nError message: """
      + errorMessage))


def updatePlayerlist(gameLetter):
  URL = getData("url" + gameLetter)
  response = retrieve_webpage(URL)
  soup = BeautifulSoup(response, 'html.parser')

  message = soup.find_all("article", class_='message')[0]
  text = (message.find(class_='bbWrapper')).get_text()
  text = text[text.lower().find("spoiler: living players"):text.lower().
              find("spoiler: dead players")]
  playerlist = []
  while (text.find("@") != -1):
    text = text[text.find("@"):]
    player = text[text.find("@") + 1:text.find('\n')].replace(" ", "")

    playerlist.append(player.lower())
    text = text[text.find('\n'):]
  updateData("playerlist" + gameLetter, playerlist)
  return (playerlist)
