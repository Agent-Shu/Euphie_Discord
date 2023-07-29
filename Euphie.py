import datetime
import ntplib
import discord
import asyncio
import yt_dlp



ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
    'key': 'FFmpegExtractAudio',
    'preferredcodec': 'mp3',
    'preferredquality': '192',
    }],
}





from discord import app_commands
from discord.ext import commands

from dotenv import dotenv_values

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning) 

try:
    temp_time = ntplib.NTPClient()
    response = temp_time.request('pool.ntp.org')
    x = datetime.datetime.fromtimestamp(response.tx_time)
    print('Internet date and time:',x.strftime("%d/%m/%Y  %I:%M:%S %p"))
    
except:
    print("Date Time server not Available")

intents = discord.Intents.all()
intents.voice_states = True

client = commands.Bot(command_prefix='+', activity=discord.Game(name="/help"), intents=intents)

song_queue = {}

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord Server\n')
    for guild in client.guilds:
        song_queue[guild.id] = []
        print("Server Name:",guild.name,"  Server ID:",guild.id,'\n')
    
    #print(song_queue)

    try:
        synced = await client.tree.sync()
        print(f"Synced {len(synced)} Commands")

    except Exception as e:
        print(e)


@client.event
async def on_guild_join(guild):
    song_queue[guild] = []
    #print(song_queue)

@client.event
async def on_guild_remove(guild):
    song_queue.pop(guild)
    #print(song_queue)


@client.tree.command(name="hello", description="Simple hello command")
@app_commands.describe(your_name = "Enter your Name")
async def hello(interaction: discord.Interaction, your_name:str):
    await interaction.response.send_message(f"hello {your_name}", ephemeral= True)


@client.tree.command(name="ping", description="Check Latency")
async def ping(interaction: discord.Interaction):
    return await interaction.response.send_message(f"Ping: "+str(1000 * round(client.latency,3))+"ms", ephemeral= True)



@client.tree.command(name="join", description="Join's users voice channel")
async def join(interaction: discord.Interaction):
    if interaction.user.voice is None:
        return await interaction.response.send_message(f"You're not in a vc, cant join", ephemeral= True)
    
    if interaction.user.voice.channel is not None and interaction.guild.voice_client is None:
        vc = interaction.user.voice.channel
        await vc.connect()
        return await interaction.response.send_message(f"Joining {vc}", ephemeral= False)
    
    if interaction.user.voice.channel is not None and interaction.guild.voice_client is not None:
        return await interaction.response.send_message(f"Occupied, cant join your vc", ephemeral= True)


@client.tree.command(name="leave", description="Leaves's users voice channel")
async def leave(interaction: discord.Interaction):
    if interaction.user.voice is None:
        return await interaction.response.send_message(f"Cant leave if you're not in the vc", ephemeral= True)

    if interaction.user.voice is not None and interaction.guild.voice_client is None:
        return await interaction.response.send_message(f"Cant leave vc, if I'm not in one", ephemeral= True)

    if interaction.user.voice.channel != interaction.guild.voice_client.channel:
        return await interaction.response.send_message(f"You're not in the same vc", ephemeral= False)

    if interaction.user.voice.channel == interaction.guild.voice_client.channel:
        vc = interaction.guild.voice_client.channel
        await interaction.response.send_message(f"Leaving {vc}", ephemeral= False)
        return await interaction.guild.voice_client.disconnect()



@client.tree.command(name="getuser", description="Get's Users ID")
@app_commands.describe(user= "Select User")
async def hello(interaction: discord.Interaction, user:discord.User):
    if interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(f"Discord ID: {user.id}", ephemeral= False)
    else:
        return await interaction.response.send_message(f"You dont have permission for this command", ephemeral= True)






@client.tree.command(name="play", description="Play Music")
@app_commands.describe(link= "Enter Youtube Link")
async def play(interaction: discord.Interaction, link:str):

    try:
        await interaction.response.defer(ephemeral=True)
        
        channel = interaction.user.voice.channel
        vc = await channel.connect()

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            filename = ydl.extract_info(link, download= False)

        #source = await discord.FFmpegPCMAudio(filename['url'])

        vc.play(await discord.FFmpegOpusAudio.from_probe(filename['url']))

        return await interaction.followup.send(f"Link : {link}", ephemeral= False)
    

    except Exception as e:
        print(e)
        return
    


client.run(dotenv_values("token.env")["BOT_TOKEN"])


