import discord, edge_tts, asyncio
from discord.ext import commands
from discord import app_commands

class TTS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.on = {}
        self.tts_channel = {}
        self.queue = {}
        self.lock = {}

    @app_commands.command(name="join", description="VC me aao")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return await interaction.response.send_message("Pehle VC join kar!", ephemeral=True)
        await interaction.user.voice.channel.connect()
        await interaction.response.send_message("✅ Aa gaya!", ephemeral=True)

    @app_commands.command(name="leave", description="VC se niklo")
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("✅ Nikal gaya!", ephemeral=True)

    @app_commands.command(name="settts", description="Konsa channel padhna hai")
    async def settts(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.tts_channel[interaction.guild.id] = channel.id
        await interaction.response.send_message(f"✅ Ab se sirf {channel.mention} ka padhunga!", ephemeral=True)

    @app_commands.command(name="tts", description="TTS on/off")
    @app_commands.choices(mode=[app_commands.Choice(name="on", value="on"), app_commands.Choice(name="off", value="off")])
    async def tts_cmd(self, interaction: discord.Interaction, mode: str):
        self.on[interaction.guild.id] = mode == "on"
        await interaction.response.send_message(f"TTS {mode.upper()}!", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        if not self.on.get(message.guild.id): return

        ch_id = self.tts_channel.get(message.guild.id)
        if ch_id and message.channel.id!= ch_id: return

        vc = message.guild.voice_client
        if not vc: return

        gid = message.guild.id
        if gid not in self.queue:
            self.queue[gid] = []
            self.lock[gid] = False

        self.queue[gid].append(f"{message.author.display_name} said {message.content[:100]}")

        if self.lock[gid]: return
        self.lock[gid] = True

        while self.queue[gid]:
            text = self.queue[gid].pop(0)
            if vc.is_playing(): vc.stop()
            await edge_tts.Communicate(text, voice="en-US-GuyNeural").save(f"tts_{gid}.mp3")
            vc.play(discord.FFmpegPCMAudio(f"tts_{gid}.mp3"))
            while vc.is_playing():
                await asyncio.sleep(0.5)

        self.lock[gid] = False

async def setup(bot):
    await bot.add_cog(TTS(bot))