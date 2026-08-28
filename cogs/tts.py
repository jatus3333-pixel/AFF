import discord, edge_tts, asyncio, re, subprocess, json, os
from discord.ext import commands
from discord import app_commands

def clean_text(text: str):
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[:;][a-z_]+:', '', text)
    return text.strip()[:120]

def get_duration(file):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", file],
            capture_output=True, text=True, timeout=5
        )
        return float(json.loads(r.stdout)["format"]["duration"])
    except:
        return 3.0

class TTS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.on = {}
        self.tts_vc = {}
        self.queue = {}
        self.lock = {}

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

        full_text = f"{message.author.display_name} says {cleaned}"
        self.queue[gid].append(full_text)

        if self.lock[gid]: return
        self.lock[gid] = True

        while self.queue[gid]:
            text = self.queue[gid].pop(0)
            tts_file = f"tts_{gid}.mp3"
            mixed_file = f"mixed_{gid}.mp3"

            try:
                # 1. TTS banao - MALE + FAST
                await edge_tts.Communicate(text, voice="hi-IN-MadhurNeural", rate="+20%").save(tts_file)
                tts_dur = get_duration(tts_file) + 0.5

                music_cog = self.bot.get_cog("Music")
                player = music_cog.get_player(gid) if music_cog else None

                # 2. Agar gana baj raha hai to MIX karo
                if player and player.voice and player.voice.is_playing() and player.current:
                    # Current stream ka URL nikalo
                    stream_data = await player.get_audio_stream(player.current)
                    if stream_data and vc.source and isinstance(vc.source, discord.PCMVolumeTransformer):
                        original_vol = vc.source.volume
                        # Volume halka karo bina pause kiye
                        vc.source.volume = original_vol * 0.18
                        await asyncio.sleep(0.15)

                        # Music ko pause karo, ab mixed wala bajayenge jisme music low + tts dono hai
                        # Isse gana band nahi lagega
                        player.voice.pause()

                        # FFMPEG MIX: music stream + tts
                        # Music ko background me low volume pe mix
                        try:
                            # Music ka thoda hissa + TTS ko mix karke ek file banao
                            cmd = [
                                "ffmpeg", "-y",
                                "-i", stream_data["url"],
                                "-i", tts_file,
                                "-filter_complex",
                                f"[0:a]volume=0.18,atrim=duration={tts_dur}[a0];[1:a]volume=2.0[a1];[a0][a1]amix=inputs=2:duration=shortest:dropout_transition=0",
                                "-t", str(tts_dur),
                                mixed_file
                            ]
                            # headers ke liye before nahi, direct try karte hai
                            proc = await asyncio.to_thread(lambda: subprocess.run(cmd, capture_output=True, timeout=10))

                            if os.path.exists(mixed_file):
                                vc.play(discord.FFmpegPCMAudio(mixed_file))
                                while vc.is_playing():
                                    await asyncio.sleep(0.1)
                                # Wapas music resume
                                vc.source = discord.PCMVolumeTransformer(
                                    discord.FFmpegPCMAudio(stream_data["url"], executable=player.bot.get_cog("Music").players[gid].voice, before_options="", options="-vn"),
                                    volume=original_vol
                                )
                                # Simple resume
                                player.voice.resume()
                                if isinstance(player.voice.source, discord.PCMVolumeTransformer):
                                    player.voice.source.volume = original_vol
                            else:
                                # Fallback agar mix fail hua to simple TTS
                                vc.play(discord.FFmpegPCMAudio(tts_file))
                                while vc.is_playing():
                                    await asyncio.sleep(0.1)
                                player.voice.resume()
                                if isinstance(player.voice.source, discord.PCMVolumeTransformer):
                                    player.voice.source.volume = original_vol

                        except Exception as e:
                            print(f"Mix error: {e}")
                            # Fallback
                            vc.play(discord.FFmpegPCMAudio(tts_file))
                            while vc.is_playing():
                                await asyncio.sleep(0.1)
                            try:
                                player.voice.resume()
                                if isinstance(player.voice.source, discord.PCMVolumeTransformer):
                                    player.voice.source.volume = original_vol
                            except: pass
                    else:
                        # Normal TTS agar music source volume wala nahi hai
                        if player.voice.is_playing():
                            player.voice.pause()
                        vc.play(discord.FFmpegPCMAudio(tts_file))
                        while vc.is_playing():
                            await asyncio.sleep(0.1)
                        try: player.voice.resume()
                        except: pass
                else:
                    # Gana nahi baj raha to direct TTS
                    vc.play(discord.FFmpegPCMAudio(tts_file))
                    while vc.is_playing():
                        await asyncio.sleep(0.1)

            except Exception as e:
                print(f"TTS Error: {e}")
                try:
                    music_cog = self.bot.get_cog("Music")
                    if music_cog:
                        p = music_cog.get_player(gid)
                        if p and p.voice and p.voice.is_paused():
                            p.voice.resume()
                except: pass

            await asyncio.sleep(0.1)

        self.lock[gid] = False

async def setup(bot):
    await bot.add_cog(TTS(bot))