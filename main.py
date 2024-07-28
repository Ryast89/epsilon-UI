import math
import datetime
import traceback
import os
from typing import Literal
import time
from initDB import initJsonData

import discord
from discord import app_commands
from discord.ext import tasks, commands
import asyncio

from keep_alive import keep_alive
from vcbot import getVotecount, updatePlayerlist, updateVoteHistory, createPhase, removePhase, getVotesByPostnum, formatRetrospectiveVCDiscord
from updateData import getToken, getData, updateData
from iso import wipeISO, updateISO, rankActivity, playerHasPosted
from epsilon_commands import Special, Queue, riva, Alias

intents = discord.Intents.default()
intents.message_content = True
test_guild = discord.Object(id="1256364965510512680")
help_message = discord.Embed(colour=discord.Color.teal(),
                             description="""
    Epsilon is a combined votecount and ISO bot. It simultaneously handles three games (named A, B, and C), handles ISOs, posts automatic and manual votecounts, and checks for any hammers that occur.

    Note for mods: please ensure that the "Living Players" spoiler is up-to-date in the OP, as only people tagged in this list will have their votes counted. Ensure that each living player is tagged properly. The 'Living Players' spoiler should be immediately followed by a 'Dead Players' spoiler. See one of Mark's games for a sample of how to set it up.

    Also note that due to popular request, the [unvote] tag has been disabled.

    **Mod Commands** *Requires the user to be the host or part of the mod team*\n
    `/url <game> <url>` - sets the game URL.\n
    `/new_phase <game> <postnum> <phase_name>` - creates a new phase for the game.\n
    `/wipe <game>` - wipes the ISO database.\n
    `/vc_auto_on <game> first_page>` - turns on the auto VC function.\n
    `/vc_auto_off <game>` - turns it off.\n
    `/vc_delay <game> <delay>` - sets the auto VC delay in minutes.\n
    `/queue update` - updates the queue. (Mod team use only)\n\n

    **Public Commands** *Anyone can use these.*\n
    `/updateISO <game>` - manually updates the ISO database for that game.\n
    `/updatevotehistory <game>` - updates the votes for that game.\n
    `/iso <game> <player>` - links you to the ISO for that player.\n
    `/votehistory <game>` - links you to the vote history.\n
    `/votecount <game>` - links you to the current votecount for that game.\n
    `/rank_activity <game>` - lists every player and their postcount.\n
    `/alias add <alias> <truename>` - create an alias for a player.\n
    `/change_forum_name old_name new_name` - if you change your forum name, use this command to shift all your old aliases to your new name.\n
    `/alias print` - prints all aliases stored.\n
    `/getvc <game> <p1> <p2>` - gets a votecount for that game, from page 1 to page 2.
    """)
#phrases banned in serious-discussion
banned_phrases = []

keep_alive()
TOKEN = getToken("discord")


def getChannelByName(guild, name):
  for channel in guild.channels:
    if (channel.name) == name:
      return channel
  return (0)


def getRoleByName(guild, name):
  for role in guild.roles:
    if (role.name == name):
      return (role)
  return (0)


async def updateStatus(status):
  game = discord.Game(status)
  await client.change_presence(status=discord.Status.online, activity=game)
  print("Updated status to {}".format(status))
  return


async def announce(game, text, embed=False):
  for channel in channels[game]:
    if embed:
      await client.get_channel(channel).send(embed=text)
    else:
      await client.get_channel(channel).send(text)
  return


def is_host(interaction: discord.Interaction) -> bool:
  for role in interaction.user.roles:
    if (role.name in ["Mafia", "Puppeteer (Host)", "God"]):
      print("Passed check.")
      return True
  print("FAILED check.")
  return False


async def dm(user, message):
  try:
    channel = await user.create_dm()
    await channel.send(embed=message)
    return (True)
  except:
    return (False)


async def postVCs():
  for game in ["A", "B", "C"]:
    delta = round((datetime.datetime.now() - datetime.datetime.fromisoformat(
      getData("last_time" + game))).total_seconds())
    timeSpentOn = round(
      (datetime.datetime.now() - datetime.datetime.fromisoformat(
        getData("start_time" + game))).total_seconds())
    print("delta: {}    timeSpentOn: {}   status: {}".format(
      delta, timeSpentOn, getData("vcStatus" + game)))
    if (getData("vcStatus" + game) == "on"
        and timeSpentOn > 3600 * 48):  #turn off after 48 hours
      print("AUTO VOTECOUNTS TURNED OFF BY TIMER")
      await announce(
        game,
        "The automatic votecount has been on for 48 consecutive hours. It will now turn off. Use $votecount auto on <page number> to resume, or $votecount <firstpage> <lastpage> to generate a single votecount."
      )
      updateData("vcStatus" + game, "off")

    if (getData("vcStatus" + game) == "on"
        and delta > getData("delay" + game) * 60):
      print("Scanning")
      await announce(
        game, "Getting a votecount. This may take some time. First page: " +
        str(getData("first_page" + game)))
      updateData("last_time" + game, datetime.datetime.now().isoformat())
      votecount = await getVotecount(game, getData("first_page" + game), 1000)
      await announce(game, votecount, embed=True)
      await announce(
        game, "The next votecount will be processed in " +
        str(getData("delay" + game) / 60) +
        " hours. You can view this votecount and all previous votecounts in the #votecounts channel in Discord."
      )

  return


class MyClient(discord.Client):

  def __init__(self, *, intents: discord.Intents, application_id: int):
    super().__init__(intents=intents, application_id=application_id)

  #initJsonData()  # uncomment this if using a new repl

  async def setup_hook(self) -> None:
    self.my_background_task.start()  # start the task to run in the background

  @tasks.loop(seconds=30)  # task runs every 30 seconds
  async def my_background_task(self):
    try:
      await postVCs()
    except:
      print("Loop error!")
      traceback.print_exc()

  @my_background_task.before_loop
  async def before_my_task(self):
    await self.wait_until_ready()  # wait until the bot logs in


client = MyClient(intents=intents, application_id=1256365031998750761)
tree = app_commands.CommandTree(client)
tree.add_command(Special())
tree.add_command(Queue())
tree.add_command(riva())
tree.add_command(Alias())

#ISO MANAGEMENT


@tree.command()
@app_commands.check(is_host)
@app_commands.describe(game='Available Games', url="game url")
async def url(interaction: discord.Interaction, game: Literal['A', 'B', 'C'],
              url: str):
  updateData("url{}".format(game), url)
  wipeISO(game)
  await interaction.response.send_message(
    'Wiped post database and Set url for game {} to {}.'.format(game, url))


@tree.command()
@app_commands.check(is_host)
@app_commands.describe(game='Available Games')
async def wipe(interaction: discord.Interaction, game: Literal['A', 'B', 'C']):
  wipeISO(game)
  await interaction.response.send_message('Wiped ISO for game {}.'.format(game)
                                          )


#ISO - PUBLIC COMMANDS


@tree.command()
@app_commands.describe(game='Available Games')
async def update(interaction: discord.Interaction, game: Literal['A', 'B',
                                                                 'C']):
  await interaction.response.send_message(
    'Updating database for game {}. This may take a while.'.format(game))
  await updateISO(game)
  channel = getChannelByName(interaction.guild, "iso-bot")
  await channel.send("Update for game {} complete.".format(game))


@tree.command()
@app_commands.describe(game='Available Games', player="player")
async def iso(interaction: discord.Interaction, game: Literal['A', 'B', 'C'],
              player: str):
  if (playerHasPosted(game, player) == True):
    text = "Found desired ISO: https://c6cb5bfe-38c9-4d4a-a59d-a1aa87b4fb6c-00-1n57276fyrj8i.kirk.replit.dev/{}/{}. Happy scumhuntung!".format(
      game, player)
  else:
    text = "Nothing found for {} in game {}.".format(player, game)
  await interaction.response.send_message(text, ephemeral=True)


@tree.command()
@app_commands.describe(game='Available Games')
async def votehistory(interaction: discord.Interaction, game: Literal['A', 'B',
                                                                      'C']):
  text = "Found vote history: https://c6cb5bfe-38c9-4d4a-a59d-a1aa87b4fb6c-00-1n57276fyrj8i.kirk.replit.dev/{}/votes.".format(
    game)
  await interaction.response.send_message(text, ephemeral=True)


@tree.command()
@app_commands.describe(game='Available Games')
async def votecount(interaction: discord.Interaction, game: Literal['A', 'B',
                                                                    'C']):
  text = "Found votecount: https://c6cb5bfe-38c9-4d4a-a59d-a1aa87b4fb6c-00-1n57276fyrj8i.kirk.replit.dev/{}/votecount.".format(
    game)
  await interaction.response.send_message(text, ephemeral=True)


@tree.command()
@app_commands.describe(game='Available Games')
async def rank_activity(interaction: discord.Interaction,
                        game: Literal['A', 'B', 'C'],
                        select_players: Literal['alive', 'all']):
  await interaction.response.send_message(
    "Ranking activity for game {}...".format(game))
  text = rankActivity(game, select_players == 'alive')
  channel = getChannelByName(interaction.guild, "iso-bot")
  await channel.send(
    embed=discord.Embed(color=discord.Color.teal(), description=text))


#VOTECOUNT commands
@tree.command()
@app_commands.check(is_host)
@app_commands.describe(game='Available Games',
                       postnum="Phase start post number",
                       phasename="Name of phase")
async def new_phase(interaction: discord.Interaction, game: Literal['A', 'B',
                                                                    'C'],
                    postnum: int, phasename: str):
  createPhase(game, postnum, phasename)
  await interaction.response.send_message(
    'Created new phase named {} in game {}'.format(phasename, game))


@tree.command()
@app_commands.check(is_host)
@app_commands.describe(game='Available Games', phasename="Name of phase")
async def remove_phase(interaction: discord.Interaction,
                       game: Literal['A', 'B', 'C'], phasename: str):
  removePhase(game, phasename)
  await interaction.response.send_message('Removed phase {} in game {}'.format(
    phasename, game))


@tree.command()
@app_commands.check(is_host)
@app_commands.describe(game='Available Games', first_page="Number >= 1")
async def vc_auto_on(interaction: discord.Interaction,
                     game: Literal['A', 'B', 'C'], first_page: int):
  await interaction.response.send_message(
    "Auto VC for game {} set to on. First page: {}".format(game, first_page))
  updateData("vcStatus{}".format(game), "on")
  updateData("first_page" + game, first_page)
  updateData("start_time" + game, datetime.datetime.now().isoformat())


@tree.command()
@app_commands.check(is_host)
@app_commands.describe(game='Available Games')
async def vc_auto_off(interaction: discord.Interaction, game: Literal['A', 'B',
                                                                      'C']):
  await interaction.response.send_message(
    "Auto VC for game {} set to off.".format(game))
  updateData("vcStatus" + game, "off")


@tree.command()
@app_commands.check(is_host)
@app_commands.describe(game='Available Games', delay='Time delay in minutes')
async def vc_delay(interaction: discord.Interaction,
                   game: Literal['A', 'B', 'C'], delay: int):
  await interaction.response.send_message(
    "Auto VC delay for game {} set to {} minutes.".format(game, delay))
  updateData("delay" + game, delay)


@tree.command()
async def getvc(interaction: discord.Interaction, game: Literal["A", "B", "C"],
                p1: int, p2: int):
  await interaction.response.send_message(
    "Getting votecount. This might take a bit...")
  text = await getVotecount(game, p1, p2)
  print(text)
  await interaction.channel.send(embed=text)


@tree.command()
async def updatevotehistory(interaction: discord.Interaction,
                            game: Literal["A", "B", "C"]):
  await interaction.response.send_message(
    "Updating votes. This might take a bit...")
  text = await updateVoteHistory(game)
  print(text)
  await interaction.channel.send(embed=text)


@tree.command()
async def getretrospectivevc(interaction: discord.Interaction,
                             game: Literal["A", "B", "C"], post: int):
  await interaction.response.send_message(
    "Getting votecount. This might take a bit...")
  text = await formatRetrospectiveVCDiscord(game, post)
  print(text)
  await interaction.channel.send(embed=text)


@tree.command()
async def list_phases(interaction: discord.Interaction, game: Literal["A", "B",
                                                                      "C"]):
  await interaction.response.send_message(
    "Getting votecount. This might take a bit...")
  await announce(game,
                 "The existing phases are: \n" + str(getData("phases" + game)))


@tree.command()
async def help(interaction: discord.Interaction):
  await interaction.response.send_message(embed=help_message, ephemeral=True)


@tree.command(guild=test_guild)
async def ping(interaction: discord.Interaction):
  await interaction.response.send_message("Still here!")


@client.event
async def tree_eh(interaction, command, error):
  if isinstance(error, discord.app_commands.CheckFailure):
    error = "Error. To use this command, you must have role `God`, `Puppeteer (Host)`, or `Mafia`."
  try:
    await interaction.response.send_message(
      embed=discord.Embed(color=discord.Color.red(), description=error))
  except:
    await interaction.channel.send(
      embed=discord.Embed(color=discord.Color.red(), description=error))


tree.on_error = tree_eh


@client.event
async def on_ready():
  await updateStatus("/help")
  await client.change_presence(status=discord.Status.online)
  print('Logged in as')
  print(client.user.name)
  print(client.user.id)
  #last_time = getData("last_time")
  global channels
  channels = {'A': [], 'B': [], 'C': []}
  for guild in client.guilds:
    print(guild.name)
    for game in ['A', 'B', 'C']:
      for channel in guild.channels:
        if channel.name == "votecount-game-" + game.lower():
          channels[game].append(channel.id)
  updateData("channels", channels)
  tree.copy_global_to(guild=test_guild)
  await tree.sync(guild=test_guild)
  print('------')


@client.event
async def on_message(message):
  if message.author.bot == False:
    if message.channel.type == discord.ChannelType.private:
      await message.channel.send("no u")
    elif (message.channel.name == "serious-discussion"):
      if len(message.attachments) > 0:
        await message.delete()
      else:
        for phrase in banned_phrases:
          if (message.content.find((phrase)) != -1):
            await dm(
              message.author,
              discord.Embed(
                description=
                "Please don't post images in #serious-discussion. Post the original source instead. Thanks!",
                color=discord.Color.red()))
            await message.delete()
            break

    if (message.content == "$sync" and message.guild.id == test_guild.id):
      await tree.sync()
      await message.channel.send(
        "Synced commands to global. This may take a few hours to propogate.")
      print("Synced commands.")


try:
  client.run(getToken("discord"))
except discord.errors.HTTPException:
  import os
  os.system("kill 1")
