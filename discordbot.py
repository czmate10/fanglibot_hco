import traceback
import datetime
import asyncio

import discord
from discord.ext import commands as discord_commands

from config import servers


discord_bot = discord_commands.Bot(
    command_prefix='!', description='FangliBot written to host pugs and OWL betting for')


@discord_bot.event
async def on_ready():
    print("Connected to Discord as " + discord_bot.user.name)
    print("Number of servers: {0}".format(len(servers)))

    for _, v in servers.items():
        print(v['channels']['dev'])
        if(v['channels']['dev']):
            await discord_bot.send_message(discord_bot.get_channel(v['channels']['dev']), "FangliBot started!")
