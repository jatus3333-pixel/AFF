import discord, edge_tts, asyncio, re, subprocess, os, json
from discord.ext import commands
from discord import app_commands

def clean_text(text: str):
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[:;][a-z_]+:', '', text)
    return text.strip()[:100]

def get_duration(file):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", file],
            capture_output=True, text=True, timeout=5)
        return float(json.loads(r.stdout)["format"]["duration"])
    except: return 2.5

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
            duck_file = f"duck_{gid}.mp3"

            try:
                await edge_tts.Communicate(text, voice="hi-IN-MadhurNeural", rate="+15%").save(tts_file)
                dur = get_duration(tts_file) + 0.3

                music_cog = self.bot.get_cog("Music")
                player = music_cog.get_player(gid) if music_cog else None

                if player and player.voice and player.voice.is_playing() and player.current:
                    stream = await player.get_audio_stream(player.current)
                    if not stream:
                        vc.play(discord.FFmpegPCMAudio(tts_file))
                        while vc.is_playing(): await asyncio.sleep(0.1)
                        continue

                    original_vol = player.volume
                    player.voice.stop()
                    await asyncio.sleep(0.2)

                    try:
                        cmd = [
                            "ffmpeg", "-y",
                            "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_at_eof", "1",
                            "-i", stream["url"],
                            "-i", tts_file,
                            "-filter_complex",
                            f"[0:a]volume=0.25,atrim=duration={dur}[m];[1:a]volume=1.8[t];[m][t]amix=inputs=2:duration=shortest:dropout_transition=0",
                            "-t", str(dur),
                            duck_file
                        ]
                        await asyncio.to_thread(lambda: subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15))

                        if os.path.exists(duck_file):
                            vc.play(discord.FFmpegPCMAudio(duck_file))
                            while vc.is_playing(): await asyncio.sleep(0.1)
                        else:
                            vc.play(discord.FFmpegPCMAudio(tts_file))
                            while vc.is_playing(): await asyncio.sleep(0.1)
                    except Exception as e:
                        print(f"Duck mix error: {e}")
                        vc.play(discord.FFmpegPCMAudio(tts_file))
                        while vc.is_playing(): await asyncio.sleep(0.1)

                    try:
                        headers = stream.get("headers") or {}
                        header_lines = [f"{k}: {v}" for k, v in headers.items() if v]
                        ffmpeg_headers = "\r\n".join(header_lines) + "\r\n"
                        before_options = f"-nostdin -reconnect 1 -reconnect_streamed 1 -reconnect_at_eof 1 -reconnect_on_network_error 1 -reconnect_on_http_error 403,404,408,429,500,502,503,504 -reconnect_delay_max 3 -rw_timeout 10000000 -headers \"{ffmpeg_headers}\""
                        ffmpeg_options = "-vn -loglevel warning -ar 48000 -ac 2 -bufsize 512k"
                        source = discord.FFmpegPCMAudio(stream["url"], before_options=before_options, options=ffmpeg_options)
                        source = discord.PCMVolumeTransformer(source, volume=original_vol)

                        def after_resume(err):
                            if err: print(err)
                            asyncio.run_coroutine_threadsafe(player.finished(player.play_token), self.bot.loop)

                        vc.play(source, after=after_resume)
                        player.voice = vc
                    except Exception as e:
                        print(f"Resume error: {e}")
                        await player.play_next()

                else:
                    vc.play(discord.FFmpegPCMAudio(tts_file))
                    while vc.is_playing(): await asyncio.sleep(0.1)

            except Exception as e:
                print(f"TTS Error: {e}")

            await asyncio.sleep(0.2)

        self.lock[gid] = False

async def setup(bot):
    await bot.add_cog(TTS(bot))