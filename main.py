import config
from discordbot import discord_bot
from commands import pug

if __name__ == "__main__":
    print("Starting FangliBot...")
    discord_bot.run(config.discord_token)
    print("Shutting down...")