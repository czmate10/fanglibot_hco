from enum import Enum
import discord
from discord.ext import commands

from config import servers
from discordbot import discord_bot


class CaptainPicking(Enum):
    BLUE = 1
    RED = 2

class PugStatus(Enum):
    OPEN = 1
    PICKING_CAPTAINS = 2
    PICKING_PLAYERS = 3

class Pug:
    id: str
    name: str
    server: str
    status: PugStatus

    players_needed: int
    players: list
    players_red: list
    players_blue: list

    captain_red: discord.Member
    captain_blue: discord.Member
    captain_picking: CaptainPicking
    picks_remaining = -1


    def __init__(self, server: str, name: str, players_needed: int):
        self.server = server
        self.name = name
        self.id = self.server + '-' + self.name
        self.players_needed = players_needed
        self.reset()

    def reset(self):
        self.status = PugStatus.OPEN
        self.players = []
        self.players_blue = []
        self.players_red = []
        self.captain_blue = None
        self.captain_red = None
        self.captain_picking = CaptainPicking.BLUE
        self.picks_remaining = -1

    def gen_pick_help_str(self):
        msg = []
        picking_captain = self.captain_blue.mention if self.captain_picking == CaptainPicking.BLUE else self.captain_red.mention
        picking_team = "Blue" if self.captain_picking == CaptainPicking.BLUE else "Red"

        msg.append("PUG **{0}**:\n".format(self.name))
        msg.append("**{0}**, please pick {1} players for Team {2}!\n".format(picking_captain, self.picks_remaining, picking_team))

        msg.append("Players: ")
        for k,ply in enumerate(self.players):
            if ply not in self.players_blue and ply not in self.players_red:
                msg.append("**[{0}]** {1}   ".format(k, ply.display_name))

        return ''.join(msg)

    def gen_picked_players_str(self, should_mention: bool = False):
        msg = []

        # Blue
        msg.append("__Team Blue__(**{0}**):  ".format(self.captain_blue.display_name))
        for ply in self.players_blue:
            if ply != self.captain_blue:
                msg.append("*{0}*  ".format(ply.mention if should_mention else ply.display_name))

        # Red
        msg.append("\n__Team Red__(**{0}**):  ".format(self.captain_red.display_name))
        for ply in self.players_red:
            if ply != self.captain_red:
                msg.append("*{0}*  ".format(ply.mention if should_mention else ply.display_name))

        return ''.join(msg)
            

# Setup pugs
pugs = {}
for _,server in servers.items():
    for k,v in server['pugs'].items():
        pug_id = server['id'] + '-' + k
        pugs[pug_id] = Pug(server['id'], k, v['players_needed'])


def is_pug_channel(channel):
    for _,v in servers.items():
        if channel.id == v['channels']['pug']:
            return True
    return False
        

@discord_bot.group(pass_context=True)
async def pug(ctx):
    """Category for pug-related commands"""

    ctx.ignore = False
    if not is_pug_channel(ctx.message.channel):
        ctx.ignore = True
        return

    if ctx.invoked_subcommand is None:
        await discord_bot.reply('Command not found!')


@pug.command(pass_context=True)
async def join(ctx, pug_id: str):
    if(ctx.ignore):
        return

    pugobj: Pug = pugs[ctx.message.server.id + '-' + pug_id]

    if(pugobj is None):
        await discord_bot.reply("This pug does not exist!")
        return 

    if(pugobj.status != PugStatus.OPEN):
        await discord_bot.reply("The pug has already started!")
        return 

    if(ctx.message.author in pugobj.players):
        await discord_bot.reply("You are already in the pug!")
        return 

    pugobj.players.append(ctx.message.author)

    if(len(pugobj.players) >= pugobj.players_needed):
        # Pug is full, close it here
        pugobj.status = PugStatus.PICKING_CAPTAINS

        # Check if only 2 players are needed. If so, restart the pug
        if pugobj.players_needed == 2:
            await discord_bot.say("Pug **{0}** is full, players are: {1} and {2}. Please proceed to make the lobby!"
            .format(pugobj.name, pugobj.players[0].mention, pugobj.players[1].mention))
            pugobj.status = PugStatus.OPEN
            pugobj.reset()
            return

        # Message players
        for ply in pugobj.players:
            discord_bot.send_message(ply, "Pug {0} is full! Type !pug captain in the pug channel to become captain!".format(pugobj.name))

        msg = "Pug {0} is full and picking captains now! Type !pug captain to become captain!\nPlayers: "
        for ply in pugobj.players:
            msg += ply.mention + " "
        await discord_bot.say(msg.format(pugobj.name))
    else:
        await discord_bot.reply("You have joined pug {0} ({1}/{2})".format(pugobj.name, len(pugobj.players), pugobj.players_needed))


@pug.command(pass_context=True)
async def leave(ctx, pug_id: str):
    if(ctx.ignore):
        return

    pugobj: Pug = pugs[ctx.message.server.id + '-' + pug_id]

    if(pugobj is None):
        await discord_bot.reply("This pug does not exist!")
        return

    if(pugobj.status != PugStatus.OPEN):
        await discord_bot.reply("The pug has already started!")
        return

    if(ctx.message.author not in pugobj.players):
        await discord_bot.reply("You aren't in this pug!")
        return

    pugobj.players.remove(ctx.message.author)
    await discord_bot.reply("You have left pug {0} ({1}/{2})".format(pugobj.name, len(pugobj.players), pugobj.players_needed))

@pug.command(pass_context=True)
async def captain(ctx):
    if(ctx.ignore):
        return

    for _,pugobj in pugs.items():
        if(pugobj.server != ctx.message.server.id):
            continue

        if(pugobj.status != PugStatus.PICKING_CAPTAINS):
            continue

        if(ctx.message.author not in pugobj.players):
            continue

        if(pugobj.captain_blue is None):
            # Team Blue
            pugobj.captain_blue = ctx.message.author
            await discord_bot.say("Captain of Team Blue for pug '{0}' is now **{1}**!".format(pugobj.name, ctx.message.author.mention))
            return
        else:
            if pugobj.captain_blue == ctx.message.author:
                await discord_bot.reply("You can't become captains of both teams you silly!")
                return

            # Team Red
            pugobj.captain_red = ctx.message.author
            pugobj.status = PugStatus.PICKING_PLAYERS

            # First captain picks only 1
            pugobj.picks_remaining = 1

            # Put the captains in the team
            pugobj.players_blue.append(pugobj.captain_blue)
            pugobj.players_red.append(pugobj.captain_red)

            await discord_bot.say("Captains of pug '{0}' are **{1}** and **{2}**!\n{3}"
            .format(pugobj.name, pugobj.captain_blue.display_name, pugobj.captain_red.display_name, pugobj.gen_pick_help_str()))

            return

    await discord_bot.reply("There was no full pug you could become a captain of!")


@pug.command(pass_context=True)
async def pick(ctx, picked_ply_id: int):
    if(ctx.ignore):
        return

    ply = ctx.message.author

    for _,pugobj in pugs.items():
        if(pugobj.server != ctx.message.server.id):
            continue

        if pugobj.status != PugStatus.PICKING_PLAYERS:
            continue

        if pugobj.captain_blue != ply and pugobj.captain_red != ply:
            continue

        if picked_ply_id < 0 or picked_ply_id > pugobj.players_needed - 1:
            continue

        if ((ply == pugobj.captain_blue and pugobj.captain_picking != CaptainPicking.BLUE) or (ply == pugobj.captain_red and pugobj.captain_picking != CaptainPicking.RED)):
            await discord_bot.reply("The other captain is picking!")
            return

        picked_ply = pugobj.players[picked_ply_id]

        if(picked_ply in pugobj.players_blue or picked_ply in pugobj.players_red):
            await discord_bot.reply("That player is already picked!")
            return

        # We have checked everything and have the player        
        if ply == pugobj.captain_blue:
            pugobj.players_blue.append(picked_ply)
        else:
            pugobj.players_red.append(picked_ply)

        pugobj.picks_remaining = pugobj.picks_remaining - 1

        # Check if the captain still has picks left
        if pugobj.picks_remaining <= 0:
            pugobj.captain_picking = CaptainPicking.BLUE if pugobj.captain_picking == CaptainPicking.RED else CaptainPicking.RED
            pugobj.picks_remaining = min(2, pugobj.players_needed - len(pugobj.players_blue) - len(pugobj.players_red))

        # Check if all but one players are picked, and put the last player in a team
        if len(pugobj.players_blue) + len(pugobj.players_red) >= pugobj.players_needed - 1:
            for ply in pugobj.players:
                if ply in pugobj.players_blue or ply in pugobj.players_red:
                    continue

                # Last player found
                if pugobj.captain_picking == CaptainPicking.BLUE:
                    pugobj.players_blue.append(ply)
                else:
                    pugobj.players_red.append(ply)

            # All players are picked, start the pug!
            await discord_bot.say(("**Pug {0} is ready**, please proceed to make the in-game lobby and join the voice channels!\n\n" 
                             + pugobj.gen_picked_players_str(True)).format(pugobj.name))

            pugobj.status = PugStatus.OPEN
            pugobj.reset()
            return

        # Picking is still going on, print out info
        await discord_bot.say(pugobj.gen_pick_help_str() + "\n" + pugobj.gen_picked_players_str())


@pug.command(pass_context=True)
async def reset(ctx):
    if(ctx.ignore):
        return

    await discord_bot.reply("WIP")


@pug.command(pass_context=True)
async def list(ctx):
    if(ctx.ignore):
        return

    msg = []
    msg.append("Open pugs: ")
    for _, pugobj in pugs.items():
        if(pugobj.server != ctx.message.server.id):
            continue

        if(pugobj.status != PugStatus.OPEN):
            continue

        msg.append("\n\n__{0}__: {1}/{2}: ".format(pugobj.name,
                                                   len(pugobj.players), pugobj.players_needed))
        for ply in pugobj.players:
            msg.append("*{0}*   ".format(ply.display_name))

    await discord_bot.reply(''.join(msg))
