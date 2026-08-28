import discord, edge_tts, asyncio, re, subprocess, os, json, time
from discord.ext import commands
from discord import app_commands

def clean_text(text: str):
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()[:70]

class TTS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.on = {}
        self.tts_vc = {}
        self.queue = {}
        self.lock = {}

    @app_commands.command(name="join", description="VC me aao")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return await interaction.response.send_message("Pehle VC join kar!", ephemeral=True)
        await interaction.user.voice.channel.connect()
        await interaction.response.send_message(f"✅ {interaction.user.voice.channel.name} me aa gaya!", ephemeral=True)

    @app_commands.command(name="leave", description="VC se niklo")
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("✅ Nikal gaya!", ephemeral=True)

    @app_commands.command(name="settts", description="Kis VC ka chat padhna hai")
    async def settts(self, interaction: discord.Interaction, vc: discord.VoiceChannel):
        self.tts_vc[interaction.guild.id] = vc.id
        await interaction.response.send_message(f"✅ Set! Ab **{vc.name}** ka chat padhunga", ephemeral=True)

    @app_commands.command(name="tts", description="TTS on/off")
    @app_commands.choices(mode=[app_commands.Choice(name="on", value="on"), app_commands.Choice(name="off", value="off")])
    async def tts_cmd(self, interaction: discord.Interaction, mode: str):
        self.on[interaction.guild.id] = mode == "on"
        await interaction.response.send_message(f"TTS {mode.upper()}!", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        if not self.on.get(message.guild.id): return
        if not message.content: return
        vc = message.guild.voice_client
        if not vc: return

        gid = message.guild.id
        target_vc_id = self.tts_vc.get(gid) or vc.channel.id
        if message.channel.id!= target_vc_id: return

        cleaned = clean_text(message.content)
        if not cleaned: return

        if gid not in self.queue:
            self.queue[gid] = []
            self.lock[gid] = False

        self.queue[gid].append(f"{message.author.display_name} says {cleaned}")

        if self.lock[gid]: return
        self.lock[gid] = True

        while self.queue[gid]:
            text = self.queue[gid].pop(0)
            tts_file = f"tts_{gid}.mp3"

            try:
                # FASTEST MALE
                await edge_tts.Communicate(text, voice="hi-IN-MadhurNeural", rate="+40%").save(tts_file)

                music_cog = self.bot.get_cog("Music")
                player = music_cog.get_player(gid) if music_cog else None

                if player and player.voice and player.voice.is_playing() and player.current:
                    # 1. Volume halka karo - 20% (slow jaisa)
                    original_vol = player.volume
                    try:
                        if player.voice.source and isinstance(player.voice.source, discord.PCMVolumeTransformer):
                            player.voice.source.volume = original_vol * 0.20
                    except: pass

                    await asyncio.sleep(0.15)

                    # 2. Gana PAUSE - stop nahi, taki wahin se resume ho
                    player.voice.pause()
                    await asyncio.sleep(0.1)

                    # 3. TTS bajao - bina music ka source hataye
                    # Hum vc.play use nahi karenge, warna music source delete ho jayega
                    # Direct audio packet bhejenge
                    source = discord.FFmpegPCMAudio(tts_file)
                    vc.play(source)
                    while vc.is_playing():
                        await asyncio.sleep(0.05)

                    # 4. Wapas volume full aur RESUME - wahin se bajega, restart nahi
                    await asyncio.sleep(0.1)
                    try:
                        # Purana music source wapas lagao agar delete ho gaya ho to
                        # Agar pause tha to resume kaam karega
                        if player.voice.is_paused() or not player.voice.is_playing():
                            # Source abhi bhi hai to bas resume
                            try:
                                player.voice.resume()
                                if player.voice.source and isinstance(player.voice.source, discord.PCMVolumeTransformer):
                                    player.voice.source.volume = original_vol
                            except:
                                # Agar source delete ho gaya to seek ke saath wapas bajao
                                elapsed = 0
                                if hasattr(player, 'song_start_time') and player.song_start_time:
                                    elapsed = time.monotonic() - player.song_start_time
                                stream = await player.get_audio_stream(player.current)
                                if stream:
                                    headers = stream.get("headers") or {}
                                    header_lines = [f"{k}: {v}" for k, v in headers.items() if v]
                                    ffmpeg_headers = "\r\n".join(header_lines) + "\r\n"
                                    seek_sec = int(elapsed)
                                    before_options = f"-nostdin -ss {seek_sec} -reconnect 1 -reconnect_streamed 1 -reconnect_at_eof 1 -reconnect_on_network_error 1 -reconnect_on_http_error 403,404,408,429,500,502,503,504 -reconnect_delay_max 3 -rw_timeout 10000000 -headers \"{ffmpeg_headers}\""
                                    ffmpeg_options = "-vn -loglevel warning -ar 48000 -ac 2 -bufsize 512k"
                                    src = discord.FFmpegPCMAudio(stream["url"], before_options=before_options, options=ffmpeg_options)
                                    src = discord.PCMVolumeTransformer(src, volume=original_vol)
                                    def after_resume(err):
                                        asyncio.run_coroutine_threadsafe(player.finished(player.play_token), self.bot.loop)
                                    vc.play(src, after=after_resume)
                                    player.voice = vc
                                    player.song_start_time = time.monotonic() - seek_sec
                    except Exception as e:
                        print(f"Resume error: {e}")

                else:
                    # Gana nahi baj raha to direct TTS
                    vc.play(discord.FFmpegPCMAudio(tts_file))
                    while vc.is_playing():
                        await asyncio.sleep(0.05)

            except Exception as e:
                print(f"TTS Error: {e}")

        self.lock[gid] = False

async def setup(bot):
    await bot.add_cog(TTS(bot))