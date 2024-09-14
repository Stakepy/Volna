import discord
from discord.ext import commands, tasks
import youtube_dl
import asyncio
import os

TOKEN = 'token'  # Замените на ваш реальный токен
VOICE_CHANNEL_ID = id
RADIO_URL = 'https://nashe1.hostingradio.ru:80/nashe-128.mp3'

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

class RadioPlayer:
    def __init__(self, bot):
        self.bot = bot
        self.voice_client = None
        self.voice_channel_id = VOICE_CHANNEL_ID
        self.check_channel_loop.start()

    async def connect(self):
        channel = self.bot.get_channel(self.voice_channel_id)
        if channel:
            if self.voice_client:
                if self.voice_client.channel != channel:
                    try:
                        await self.voice_client.move_to(channel)
                    except discord.DiscordException as e:
                        print(f"Error moving bot to channel: {e}")
            else:
                try:
                    self.voice_client = await channel.connect()
                except discord.DiscordException as e:
                    print(f"Error connecting to channel: {e}")
                    self.voice_client = None

            if self.voice_client:
                await asyncio.sleep(1)  # Wait a moment to ensure the bot is fully connected
                await self.play_radio()  # Play radio only after ensuring connection
        else:
            print("Channel not found!")

    async def play_radio(self):
        if self.voice_client:
            if not self.voice_client.is_playing():
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'quiet': True,
                }
                try:
                    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(RADIO_URL, download=False)
                        url = info['formats'][0]['url']
                        self.voice_client.play(discord.FFmpegPCMAudio(url, **{
                            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                        }))
                    print("Playing radio.")
                except Exception as e:
                    print(f"Error playing radio: {e}")
                    await asyncio.sleep(5)  # Wait a bit before retrying
                    await self.play_radio()  # Retry playing radio
            else:
                print("Already playing.")
        else:
            print("Not connected to voice.")

    @tasks.loop(minutes=1)
    async def check_channel_loop(self):
        if self.voice_client:
            if self.voice_client.channel.id != self.voice_channel_id:
                print("Bot is not in the correct channel. Reconnecting...")
                await self.reconnect()
            elif not self.voice_client.is_playing():
                print("Bot is not playing. Restarting radio...")
                await self.play_radio()
        else:
            print("Bot is not connected. Connecting...")
            await self.connect()

    async def reconnect(self):
        if self.voice_client:
            self.voice_client.stop()
            self.voice_client = None
        await self.connect()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    bot.radio_player = RadioPlayer(bot)
    await bot.radio_player.connect()

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user:
        if after.channel is None or after.channel.id != VOICE_CHANNEL_ID:
            await asyncio.sleep(1)  # Give time for state update
            channel = bot.get_channel(VOICE_CHANNEL_ID)
            if channel:
                voice_client = discord.utils.get(bot.voice_clients, guild=channel.guild)
                if voice_client:
                    if voice_client.channel.id != VOICE_CHANNEL_ID:
                        try:
                            await voice_client.move_to(channel)
                            print(f"Bot moved to {channel.name}.")
                        except discord.DiscordException as e:
                            print(f"Error moving bot to channel: {e}")
                else:
                    try:
                        bot.radio_player.voice_client = await channel.connect()
                        print(f"Bot connected to {channel.name}.")
                    except discord.DiscordException as e:
                        print(f"Error connecting to channel: {e}")

                if bot.radio_player.voice_client and bot.radio_player.voice_client.is_connected():
                    await asyncio.sleep(1)  # Ensure stable connection
                    if not bot.radio_player.voice_client.is_playing():
                        await bot.radio_player.play_radio()
    else:
        # Handle other members' voice state changes if needed
        pass

bot.run(TOKEN)
