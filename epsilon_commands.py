import discord
import asyncio
import math
from discord.ext import tasks, commands
import datetime
import traceback
import os
from keep_alive import keep_alive
from discord import app_commands
from typing import Literal
from vcbot import getVotecount, updatePlayerlist, updateVoteHistory
from updateData import getToken, getData, updateData, listData
from iso import wipeISO, updateISO, rankActivity, playerHasPosted
from queue_manager import get_queue


def is_host(interaction: discord.Interaction) -> bool:
    for role in interaction.user.roles:
        if (role.name in ["Mafia", "Puppeteer (Host)", "God"]):
            print("Passed check.")
            return True
    print("FAILED check.")
    return False


class Special(app_commands.Group):

    @app_commands.command()
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Still here!")

    @app_commands.command()
    async def list(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=discord.Embed(
            color=discord.Color.green(), description=listData()))


class Queue(app_commands.Group):

    @app_commands.command()
    @app_commands.check(is_host)
    async def update(self, interaction: discord.Interaction):
        await interaction.response.send_message("Updating!", ephemeral=True)
        for guild in interaction.client.guilds:
            for channel in guild.channels:
                if channel.name == "mafia-hosting-queues":
                    print("-------------")
                    queues = getData("queues")
                    if queues is None:
                        queues = {}
                    if str(channel.id) in list(queues.keys()):
                        try:
                            msg = await channel.fetch_message(queues[str(
                                channel.id)])
                            await msg.edit(content=get_queue())
                        except:
                            msg = await channel.send(get_queue())
                            queues.update({channel.id: str(msg.id)})
                            updateData("queues", queues)
                            print("New queue msg created.")

                    else:
                        msg = await channel.send(get_queue())
                        queues.update({channel.id: str(msg.id)})
                        updateData("queues", queues)
                        print("New queue msg created.")


class riva(app_commands.Group):

    @app_commands.command()
    @app_commands.check(is_host)
    @app_commands.describe(game='Available Games',
                           player="Player you want to add a vote to")
    async def add(self, interaction: discord.Interaction,
                  game: Literal['A', 'B', 'C'], player: str):
        increments = getData("increments" + game)
        #of form {'player':'increment'}
        increments.update({player.lower(): increments[player.lower()] + 0.2})
        updateData("increments" + game, increments)
        await interaction.response.send_message(
            'Added 0.2 votes to {}. Total increments added: {}'.format(
                player, increments[player.lower()]))

    @app_commands.command()
    @app_commands.check(is_host)
    @app_commands.describe(game='Available Games',
                           player="Player you want to subtract a vote to")
    async def sub(self, interaction: discord.Interaction,
                  game: Literal['A', 'B', 'C'], player: str):
        increments = getData("increments" + game)
        #of form {'player':'increment'}
        increments.update({player.lower(): increments[player.lower()] - 0.2})
        updateData("increments" + game, increments)
        await interaction.response.send_message(
            'Subtracted 0.2 votes to {}. Total increments added: {}'.format(
                player, increments[player.lower()]))

    @app_commands.command()
    @app_commands.check(is_host)
    @app_commands.describe(game='Available Games')
    async def reset_counter(self, interaction: discord.Interaction,
                            game: Literal['A', 'B', 'C']):
        playerlist = updatePlayerlist(game)  # playerlist
        increments = {}
        for player in playerlist:
            increments.update({player.lower(): 0})
        updateData("increments" + game, increments)
        await interaction.response.send_message(
            'Reset counters to 0. Players in game: {}'.format(playerlist))

    @app_commands.command()
    @app_commands.check(is_host)
    @app_commands.describe(game='Available Games')
    async def print_counter(self, interaction: discord.Interaction,
                            game: Literal['A', 'B', 'C']):
        await interaction.response.send_message(getData("increments" + game))


class Alias(app_commands.Group):

    @app_commands.command()
    @app_commands.describe(alias='alias',
                           true_name='forum username (not case sensitive)')
    async def add(self, interaction: discord.Interaction, alias: str,
                  true_name: str):
        list_of_aliases = getData("list_of_aliases")
        list_of_aliases.update({alias.lower(): true_name.lower()})
        updateData("list_of_aliases", list_of_aliases)
        await interaction.response.send_message("{} is an alias of {}.".format(
            alias, true_name))

    @app_commands.command()
    @app_commands.describe(old_name="old forum name",
                           new_name="new forum name")
    async def change_forum_name(self, interaction: discord.Interaction,
                                old_name: str, new_name: str):
        list_of_aliases = getData("list_of_aliases")
        for key in list_of_aliases.keys():
            if (list_of_aliases[key].lower() == old_name.lower()):
                list_of_aliases.update({key: new_name.lower()})
        updateData("list_of_aliases", list_of_aliases)
        await interaction.response.send_message(
            "Switched name from {} to {}.".format(old_name, new_name))

    @app_commands.command()
    async def print(self, interaction: discord.Interaction):
        list_of_aliases = getData("list_of_aliases")
        format = "**List of aliases:**\n"
        for alias in list_of_aliases.keys():
            format = format + alias + "->" + list_of_aliases[alias] + "\n"
        await interaction.response.send_message(format)
