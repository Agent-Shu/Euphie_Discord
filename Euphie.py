import asyncio
import datetime
from dotenv import dotenv_values
import discord
from discord import app_commands
from discord.ext import commands
import ntplib
import re
import warnings
import yt_dlp

warnings.filterwarnings("ignore", category=RuntimeWarning)

ydl_opts = {
    'format': 'worstaudio/worst',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

#try:
    #temp_time = ntplib.NTPClient()
    #response = temp_time.request('pool.ntp.org')
    #x = datetime.datetime.fromtimestamp(response.tx_time)
    #print('Internet date and time:',x.strftime("%d/%m/%Y  %I:%M:%S %p"))
    
#except:
    #print("Date Time server not Available")

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


# TEST

@client.tree.command(name="hello", description="Simple hello command")
@app_commands.describe(your_name = "Enter your Name")
async def hello(interaction: discord.Interaction, your_name:str):
    return await interaction.response.send_message(f"hello {your_name}", ephemeral= True)


# UTILITY

@client.tree.command(name="ping", description="Check Latency")
async def ping(interaction: discord.Interaction):
    return await interaction.response.send_message(f"Ping: "+str(1000 * round(client.latency,3))+"ms", ephemeral= True)


@client.tree.command(name="getuser", description="Get's Users ID")
@app_commands.describe(user= "Select User")
async def hello(interaction: discord.Interaction, user:discord.User):
    if interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(f"Discord ID: {user.id}", ephemeral= False)
    else:
        return await interaction.response.send_message(f"You dont have permission for this command", ephemeral= True)
    

# MUSIC FUNC

async def search_link(amount, link, get_url= False):
    info = await client.loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(f"ytsearch{amount}:{link}", download= False))
    if len(info["entries"]) == 0:
        return None
    return [entry["webpage_url"] for entry in info["entries"]] if get_url else info

async def search_title(amount, link, get_url= False):
    info = await client.loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(f"ytsearch{amount}:{link}", download= False))
    if len(info["entries"]) == 0:
        return None
    return [entry["title"] for entry in info["entries"]] if get_url else info

async def embed_result(interaction, link, vidid, get_url=False):
    title = await search_title(1, link, get_url= True)
    embed = discord.Embed(title=title[0], description=link, colour=discord.Colour.magenta())
    embed.set_thumbnail(url=f'https://img.youtube.com/vi/'+vidid+'/maxresdefault.jpg')
    await interaction.followup.send(embed=embed)

async def play_song(interaction, link, vidid, get_url= False):
    title = await search_title(1, link, get_url= True)
    embed = discord.Embed(title="Now Playing", description=title[0], color=discord.Color.magenta())
    embed.set_thumbnail(url=f'https://img.youtube.com/vi/'+vidid+'/maxresdefault.jpg')

    await interaction.followup.send(embed=embed)

    filename = await asyncio.get_event_loop().run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(link, download= False))
    interaction.guild.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(filename['url']),volume=0.32), after=lambda error:client.loop.create_task(check_queue(interaction, get_url= True)))

async def check_queue(interaction, get_url= False):
    if len(song_queue[interaction.guild_id]) > 0:
        vidid= await extract_vidid(song_queue[interaction.guild_id][0])
        await play_song(interaction, song_queue[interaction.guild_id][0], vidid, get_url=True)
        song_queue[interaction.guild_id].pop(0)
    else:
        interaction.guild.voice_client.stop()

async def extract_vidid(link):
    vidid = re.search(r"^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube(-nocookie)?\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|live\/|v\/)?)([\w\-]+)(\S+)?$", link)
    if vidid:
        return vidid.group(6)


# MUSIC COMMANDS

@client.tree.command(name="join", description="Join's users voice channel")
async def join(interaction: discord.Interaction):
    if interaction.user.voice is None:
        return await interaction.response.send_message(f"You're not in a vc, cant join", ephemeral= True)
    if interaction.guild.voice_client is not None:
        return await interaction.response.send_message(f"Occupied, cant join your vc", ephemeral= True)
    if interaction.user.voice.channel is not None:
        await interaction.user.voice.channel.connect()
        return await interaction.response.send_message(f"Joining {interaction.user.voice.channel} Channel", ephemeral= False)
    

@client.tree.command(name="leave", description="Leaves's users voice channel")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client is None:
        return await interaction.response.send_message(f"Not connected to any vc at the moment", ephemeral= True)
    if interaction.guild.voice_client is not None:
        if interaction.user.voice is None:
            return await interaction.response.send_message(f"You're not in the vc", ephemeral= True)
        elif interaction.user.voice.channel == interaction.guild.voice_client.channel:
            await interaction.response.send_message(f"Leaving the {interaction.guild.voice_client.channel}", ephemeral= False)
            return await interaction.guild.voice_client.disconnect()
        else:
            return await interaction.response.send_message(f"You cant use this", ephemeral= True)
        

@client.tree.command(name="play", description="Play Music")
@app_commands.describe(song= "Enter Youtube Link or Song Name")
async def play(interaction: discord.Interaction, song:str):
    if interaction.user.voice is None:
        return await interaction.response.send_message(f"You're not in a vc, cant play", ephemeral= True)
    else:
        if interaction.guild.voice_client is None:
            await interaction.user.voice.channel.connect()
            #await interaction.response.send_message(f"Joined the {interaction.user.voice.channel} Channel", ephemeral= False)

        elif interaction.guild.voice_client is not None:
            if interaction.user.voice.channel != interaction.guild.voice_client.channel:
                return await interaction.response.send_message(f"Already playing, cant join your vc", ephemeral= True)
        
    if re.match(r"^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube(-nocookie)?\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|live\/|v\/)?)([\w\-]+)(\S+)?$", song):
        vidid = re.search(r"^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube(-nocookie)?\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|live\/|v\/)?)([\w\-]+)(\S+)?$", song)
        if vidid:
            await interaction.response.defer()
            #print(vidid.group(6))
            await embed_result(interaction, song, vidid.group(6), get_url=True)

    else:
        await interaction.response.defer()
        result = await search_link(1, song, get_url=True)
        if result is None:
            return await interaction.edit_original_response(content="Sorry, Could not find the given song")
        else:
            vidid = re.search(r"^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube(-nocookie)?\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|live\/|v\/)?)([\w\-]+)(\S+)?$", result[0])
            if vidid:
                #print(vidid.group(6))
                await embed_result(interaction, result[0], vidid.group(6), get_url=True)
                song= result[0]

    if interaction.guild.voice_client.source is not None:
        if len(song_queue[interaction.guild_id]) < 15:
            song_queue[interaction.guild_id].append(song)
            return await interaction.followup.send(content="Added to Queue", ephemeral= True)
        else:
            return await interaction.followup.send(content="Queue at max", ephemeral= True)

    await play_song(interaction, song, vidid.group(6), get_url= True)

        
@client.tree.command(name="pause", description="Pause Current Song")
async def pause(interaction: discord.Interaction):
    if interaction.guild.voice_client is None:
        return await interaction.response.send_message("Not connected to any vc", ephemeral= True)
    else:
        if interaction.user.voice is not None:
            if interaction.guild.voice_client.channel == interaction.user.voice.channel:
                if not interaction.guild.voice_client.is_playing():
                    return await interaction.response.send_message("Song is already paused", ephemeral= False, delete_after= 120)
                else:
                    interaction.guild.voice_client.pause()
                    return await interaction.response.send_message("Paused", ephemeral= False, delete_after= 120)
            else:
                return await interaction.response.send_message("You're not in the same vc", ephemeral= True)
        else:
            return await interaction.response.send_message("You're not in the vc", ephemeral= True)


@client.tree.command(name="resume", description="Resume Current Song")
async def resume(interaction: discord.Interaction):
    if interaction.guild.voice_client is None:
        return await interaction.response.send_message("Not connected to any vc", ephemeral= True)
    else:
        if interaction.user.voice is not None:
            if interaction.guild.voice_client.channel == interaction.user.voice.channel:
                if interaction.guild.voice_client.is_playing():
                    return await interaction.response.send_message("Song is already playing", ephemeral= False, delete_after= 120)
                else:
                    interaction.guild.voice_client.resume()
                    return await interaction.response.send_message("Resumed", ephemeral= False, delete_after= 120)
            else:
                return await interaction.response.send_message("You're not in the same vc", ephemeral= True)
        else:
            return await interaction.response.send_message("You're not in the vc", ephemeral= True)


@client.tree.command(name="stop", description="Resume Current Song")
async def stop(interaction: discord.Interaction): 
    if interaction.guild.voice_client is None:
        return await interaction.response.send_message("Not connected to any vc", ephemeral= True)
    else:
        if interaction.user.voice is not None:
            if interaction.user.voice.channel == interaction.guild.voice_client.channel:
                if len(song_queue[interaction.guild_id]) == 0:
                    interaction.guild.voice_client.stop()
                    await interaction.guild.voice_client.disconnect()
                    return await interaction.response.send_message("Stopping", ephemeral= False, delete_after= 480)
                else:
                    song_queue[interaction.guild_id].clear()
                    interaction.guild.voice_client.stop()
                    await interaction.guild.voice_client.disconnect()
                    return await interaction.response.send_message("Stopping", ephemeral= False, delete_after= 480)
            else:
                return await interaction.response.send_message("You're not in the same vc", ephemeral= True)
        else:
            return await interaction.response.send_message("You're not in the vc", ephemeral= True)


@client.tree.command(name="skip", description="Resume Current Song")
async def skip(interaction: discord.Interaction):
    if interaction.guild.voice_client is None:
        return await interaction.response.send_message("Not connected to any vc", ephemeral= True)
    else:
        if interaction.user.voice is not None:
            if interaction.user.voice.channel == interaction.guild.voice_client.channel:
                if len(song_queue[interaction.guild_id]) >0:
                    interaction.guild.voice_client.stop()
                    return await interaction.response.send_message("Skipping", ephemeral= False, delete_after= 480)
                else:
                    return await interaction.response.send_message("Queue is empty", ephemeral= True)
            else:
                return await interaction.response.send_message("You're not in the same vc", ephemeral= True)
        else:
            return await interaction.response.send_message("You're not in the vc", ephemeral= True)
    

@client.tree.command(name="queue", description="Song Queue")
async def queue(interaction: discord.Interaction):
    await interaction.response.defer()
    if len(song_queue[interaction.guild_id]) == 0:
        return await interaction.followup.send("Queue is empty", ephemeral= True)
    else:
        vidid= await extract_vidid(song_queue[interaction.guild_id][0])
        embed = discord.Embed(title='Queue - UP NEXT', colour=discord.Colour.magenta())
        embed.set_thumbnail(url=f'https://img.youtube.com/vi/'+vidid+'/maxresdefault.jpg')

        for i in song_queue[interaction.guild_id]:
            x = await search_title(1, i, get_url= True)
            embed.add_field(name=f'{song_queue[interaction.guild_id].index(i)+ 1}) {x[0]}', value='', inline= False)

        return await interaction.followup.send(embed=embed)










client.run(dotenv_values("token.env")["BOT_TOKEN"])




#disabled=(True if len(song_queue[interaction.guild_id]) % 5 else False)