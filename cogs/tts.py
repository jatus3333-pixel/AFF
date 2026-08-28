import discord, edge_tts, asyncio, re
from discord.ext import commands
from discord import app_commands

def clean_text(text: str):
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[:;][a-z_]+:', '', text)
    return text.strip()[:150]

class TTS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.on = {}
        self.tts_vc = {}
        self.queue = {}
        self.lock = {}
        self.ducking = {} # guild_id -> original volume

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

        full_text = f"{message.author.display_name} said {cleaned}"
        self.queue[gid].append(full_text)

        if self.lock[gid]: return
        self.lock[gid] = True

        while self.queue[gid]:
            text = self.queue[gid].pop(0)

            try:
                await edge_tts.Communicate(text, voice="en-IN-NeerjaNeural").save(f"tts_{gid}.mp3")

                # ====== DUCKING LOGIC ======
                music_cog = self.bot.get_cog("Music")
                player = music_cog.get_player(gid) if music_cog else None
                was_playing_music = False

                if player and player.voice and player.voice.is_playing() and player.current:
                    was_playing_music = True
                    # 1. Volume 20% pe lao
                    if player.voice.source and isinstance(player.voice.source, discord.PCMVolumeTransformer):
                        self.ducking[gid] = player.voice.source.volume
                        player.voice.source.volume = self.ducking[gid] * 0.2
                    await asyncio.sleep(0.6)
                    # 2. Music pause karo
                    player.voice.pause()
                    await asyncio.sleep(0.3)

                # 3. TTS bajao
                vc.play(discord.FFmpegPCMAudio(f"tts_{gid}.mp3"))
                while vc.is_playing():
                    await asyncio.sleep(0.2)

                # 4. Music wapas resume karo
                if was_playing_music and player:
                    try:
                        player.voice.resume()
                        await asyncio.sleep(0.5)
                        if player.voice.source and isinstance(player.voice.source, discord.PCMVolumeTransformer):
                            player.voice.source.volume = self.ducking.get(gid, player.volume)
                    except Exception as e:
                        print(f"Resume error: {e}")
                        # Agar resume fail hua toh gana wapas bajao
                        await player.play_next()

            except Exception as e:
                print(f"TTS Error: {e}")
                # Error aaya toh bhi music resume karo
                try:
                    music_cog = self.bot.get_cog("Music")
                    if music_cog:
                        p = music_cog.get_player(gid)
                        if p and p.voice and p.voice.is_paused():
                            p.voice.resume()
                except: pass

            await asyncio.sleep(0.3)

        self.lock[gid] = False

async def setup(bot):
    await bot.add_cog(TTS(bot))