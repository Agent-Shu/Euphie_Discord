import aiohttp
import asyncio
from datetime import datetime
from dotenv import dotenv_values
import discord
from discord.ui import Select
from discord import app_commands
from discord.ext import commands
import io
import math
import motor.motor_asyncio
import ntplib
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageColor, ImageStat
import random
import re
from typing import Optional
import warnings
import yt_dlp

warnings.filterwarnings("ignore", category=RuntimeWarning)

cluster = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://"+dotenv_values('token.env')['username']+":"+dotenv_values('token.env')['password']+"@euphiedatabase.vatvwq8.mongodb.net/?retryWrites=true&w=majority")
db = cluster["EuphieDataBase"]


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

client = commands.Bot(command_prefix='+', activity=discord.Game(name="/help To know more"), intents=intents)

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


# HEX TO RGB

async def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))


#IMAGE FUNC

async def fetch_image(session, url):
    async with session.get(url) as response:
        if response.status == 200:
            data = await response.read()
            return Image.open(io.BytesIO(data))
        else:
            return None  
        
async def brightness(img):
    try:
        stat = ImageStat.Stat(img)
        r,g,b = stat.mean[:3]
        return math.sqrt(0.241*(r**2) + 0.691*(g**2) + 0.068*(b**2))
    except Exception:
        return 255


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


# MUSIC COMMANDS ############################################################################################################################################################

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


@client.tree.command(name="stop", description="Stop song and leave vc")
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


# PROFILE COMMANDS ###########################################################################################################################################################

@client.tree.command(name="profile", description="Your Profile")
@app_commands.describe(user= "Select the User")
async def profile(interaction: discord.Interaction, user: discord.User):
    await interaction.response.defer()
    collection = db["Profile_Data"]
    res = await collection.find_one({"_id":user.id})

    if res == None:
        if interaction.user.id == user.id:
            await interaction.followup.send("Profile doesn't exist, making one")
            reply = await collection.insert_one({"_id":int(f'{interaction.user.id}'), 
                       "bg_link":"https://i.imgur.com/hsZVdRK.jpg", 
                       "color_r":255, "color_g":255, "color_b":255, 
                       "xp":0, "gold":0, "money":0})
            if reply:
                return await interaction.edit_original_response(content="Profile created, /profile again  to see")
        else:
            return await interaction.followup.send("They havent made a profile yet.")
    else:
        await interaction.followup.send("Searching profile card")
        session= aiohttp.ClientSession()
        bg= await fetch_image(session, res["bg_link"])
        black_circle= await fetch_image(session, 'https://i.imgur.com/rwI7hCE.png')
        avatar= await fetch_image(session, str(user.display_avatar))
        coin= await fetch_image(session, 'https://i.imgur.com/8R12h7J.png')
        money= await fetch_image(session, 'https://i.imgur.com/MM3WLMq.png') 
        lv= await fetch_image(session, 'https://i.imgur.com/5Ol60FH.png')
        await session.close()

        if bg is None:
            return await interaction.edit_original_response(content="Background Image doesnt exist, use /edit_profile to set background")
   
        lumen= await brightness(bg)      #AVG BRIGHTNESS VALUE
        black_circle= black_circle.resize((109,109))
        coin= coin.resize((40,40))
        money= money.resize((40,40))
        lv= lv.resize((60,40))
        width, height = bg.size

        if width <10 and height <10:
            return await interaction.edit_original_response(content="Image Size Error, use /edit_profile to change background image")
            
        if(width/height >= 1.33):        #LANDSCAPE IMAGE
            for x in range(0, width):
                if(x/height >=1.33):
                    width_1 = x
                    break
            bg = bg.crop((width/2-width_1/2,0,width/2+width_1/2,height))
        else:                            #PORTRAIT IMAGE
            for x in range(1, height):
                if(width/x <=1.33):
                    height_1 = x
                    break   
            bg = bg.crop((0,height/2-height_1/2,width,height/2+height_1/2))
        bg = bg.resize((800,600))

        draw = ImageDraw.Draw(bg, "RGBA")
        draw.rectangle(((0, 0), (800, 150)), fill=(res["color_r"],res["color_g"], res["color_b"], 140))    # TRANSLUCENT TOP
        draw.rounded_rectangle(((100, 520), (700, 570)), fill=(res["color_r"],res["color_g"], res["color_b"], 120), outline=(res["color_r"],res["color_g"], res["color_b"], 230), radius=50)   #XP BAR BG
        draw.rounded_rectangle(((105, 525), (143+(res["xp"]%1000)/1.808, 565)), fill=(res["color_r"],res["color_g"], res["color_b"], 120), outline=(res["color_r"],res["color_g"], res["color_b"], 200), radius=50)   #XP BAR

        bg1 = bg.copy()
        bg1.paste(black_circle, (5,31), black_circle)
        bg1.paste(money, (38,260), money)
        bg1.paste(coin, (38,370), coin)
        bg1.paste(lv, (680,18), lv)

        avatar = avatar.resize((80,80))
        mask = Image.new("L", avatar.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 80, 80), fill=255)
        bg1.paste(avatar,(19,45), mask)
        if lumen > 80:
            fill_color = "black"
        else:
            fill_color = "white"
        I1 = ImageDraw.Draw(bg1)
        I1.text((115, 56), str(user.display_name), font=ImageFont.truetype('font/DaysOne-Regular.ttf', 26), fill =fill_color, stroke_width=0)     #SERVER NAME
        I1.text((115, 88), str(user), font=ImageFont.truetype('font/helvetica_light.ttf', 20), fill =fill_color)                                  #USERNAME
        I1.text((751-8*len(str({res["xp"]/1000})), 75), str(int(res["xp"]/1000)), font=ImageFont.truetype('font/LEMONMILK-Light.otf',35), fill =fill_color, stroke_width= 1)          #LEVEL
        I1.text((390-8*len(str({res["xp"]%1000})), 530), str(f'{res["xp"]%1000} / 1000'), font=ImageFont.truetype('font/LEMONMILK-Light.otf',20), fill =fill_color, stroke_width= 1)  #XP BAR LEVEL
        I1.text((90, 263), str(f' : {res["money"]} Ĕ'), font=ImageFont.truetype('font/LEMONMILK-Light.otf',25), fill =fill_color, stroke_width= 1)
        I1.text((90, 373), str(f' : {res["gold"]} G'), font=ImageFont.truetype('font/LEMONMILK-Light.otf',25), fill =fill_color, stroke_width= 1)

        asyncio.to_thread(bg1.save(f"Temp_{user.id}.png"))
        await interaction.edit_original_response(content="", attachments=[discord.File(f"Temp_{user.id}.png")])
        os.remove(f"Temp_{user.id}.png")
        return 1
    

@client.tree.command(name="edit_profile", description="Edit your profile")
@app_commands.describe(background= 'Enter a direct imgur image link')
@app_commands.describe(color= 'Enter a hex value for the color')
async def edit_profile(interaction: discord.Interaction, background: Optional[str], color: Optional[str]):
    await interaction.response.defer(ephemeral= True)
    if background and color:
        if re.match(r'^https://i\.imgur\.com/[a-zA-Z0-9]+\.((jpeg)|(jpg))$',background, re.IGNORECASE):
            if re.match(r'^#[A-Fa-f0-9]{6}$', color):
                collection = db["Profile_Data"]
                res = await collection.find_one({"_id":interaction.user.id})
                if res:
                    update = await collection.update_one({"_id": interaction.user.id},{"$set": {"bg_link": background,"color_r": rgb_color[0],"color_g": rgb_color[1],"color_b": rgb_color[2]}})
                    if update:
                        return await interaction.followup.send("Successfully Updated the Background Image and color")
                    else:
                        return await interaction.followup.send("Some error has occured while updating the background image/ color")
                else:
                    return await interaction.followup.send("Profile doesnt exist, make one by /profile")
            else:
                return await interaction.followup.send("Incorrect color format, use just /edit_profile to know more")
        else:
            return await interaction.followup.send("Incorrect Link or Image format, use just /edit_profile to know more")
            
    elif background:
        if re.match(r'^https://i\.imgur\.com/[a-zA-Z0-9]+\.((jpeg)|(jpg))$',background, re.IGNORECASE):
            collection = db["Profile_Data"]
            res = await collection.find_one({"_id":interaction.user.id})
            if res:
                update = await collection.update_one({"_id": interaction.user.id},{"$set": {"bg_link": background}})
                if update:
                    return await interaction.followup.send("Successfully Updated the Background Image")
                else:
                    return await interaction.followup.send("Some error has occured while updating the background image")
            else:
                return await interaction.followup.send("Profile doesnt exist, make one by /profile")
        else:
            return await interaction.followup.send("Incorrect Link or Image format, use just /edit_profile to know more")

    elif color:
        if re.match(r'^#[A-Fa-f0-9]{6}$', color):
            collection = db["Profile_Data"]
            res = await collection.find_one({"_id":interaction.user.id})
            if res:
                rgb_color = await hex_to_rgb(color)
                update = await collection.update_one({"_id": interaction.user.id},{"$set": {"color_r": rgb_color[0],"color_g": rgb_color[1],"color_b": rgb_color[2]}})
                if update:
                    return await interaction.followup.send("Successfully Updated the Background Image")
                else:
                    return await interaction.followup.send("Some error has occured while updating the color")
            else:
                return await interaction.followup.send("Profile doesnt exist, make one by /profile")
        else:
            return await interaction.followup.send("Incorrect color format, use just /edit_profile to know more")
        
    else:
        return await interaction.followup.send("Give a direct image link from imgur to change your background.\nEg: https://i.imgur.com/example.png\nShould be .jpeg or .jpg format\n\nEnter a hex value for the color to use a accent for the profile.\nEg: #f0f0f0\nUse color picker on google to get hex codes of it", ephemeral= True)



















# UTILITY COMMANDS #############################################################################################################################################################

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


# GAME COMMANDS ################################################################################################################################################################

@client.tree.command(name="toss", description="Toss a coin")
async def toss(interaction: discord.Interaction):
    coin = random.randint(0, 1)
    if coin % 2 == 0:
        return await interaction.response.send_message("Heads")
    else:
        return await interaction.response.send_message("Tails")










client.run(dotenv_values("token.env")["BOT_TOKEN"])



#x = datetime.now()
#print(x.strftime("%d"))