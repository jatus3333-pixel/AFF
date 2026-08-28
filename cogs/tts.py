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

        vc_client = message.guild.voice_client
        if not vc_client: return

        gid = message.guild.id
        set_vc_id = self.tts_vc.get(gid)
        target_vc_id = set_vc_id if set_vc_id else vc_client.channel.id

        if message.channel.id!= target_vc_id:
            return

        cleaned = clean_text(message.content)
        if not cleaned: return

        if gid not in self.queue:
            self.queue[gid] = []
            self.lock[gid] = False

        is_hindi = any('\u0900' <= c <= '\u097F' for c in cleaned)
        voice = "hi-IN-MadhurNeural" if is_hindi else "en-IN-PrabhatNeural"
        self.queue[gid].append((cleaned, voice))

        if self.lock[gid]: return
        self.lock[gid] = True

        while self.queue[gid]:
            # IMPORTANT FIX: Agar gana baj raha hai to wait karo, usko kaato mat
            while vc_client.is_playing():
                await asyncio.sleep(1)

            text, v = self.queue[gid].pop(0)

            try:
                await edge_tts.Communicate(text, voice=v).save(f"tts_{gid}.mp3")
                vc_client.play(discord.FFmpegPCMAudio(f"tts_{gid}.mp3"))
                while vc_client.is_playing():
                    await asyncio.sleep(0.3)
            except Exception as e:
                print(f"TTS Error: {e}")

            await asyncio.sleep(0.5)

        self.lock[gid] = False

async def setup(bot):
    await bot.add_cog(TTS(bot))