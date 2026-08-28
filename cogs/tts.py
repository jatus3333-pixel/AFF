import discord
from discord.ext import commands
from discord import app_commands
import edge_tts
import asyncio

class TTS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tts_enabled = {}

    @app_commands.command(name="join", description="Bot ko VC me bulao")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return await interaction.response.send_message("❌ Pehle VC join kar!", ephemeral=True)
        channel = interaction.user.voice.channel
        await channel.connect()
        await interaction.response.send_message(f"✅ {channel.name} me aa gaya!")

    @app_commands.command(name="leave", description="Bot ko VC se nikalo")
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("✅ VC se nikal gaya!")
        else:
            await interaction.response.send_message("❌ Me VC me hi nahi hu!", ephemeral=True)

    @app_commands.command(name="tts", description="TTS on/off karo")
    @app_commands.choices(mode=[
        app_commands.Choice(name="on", value="on"),
        app_commands.Choice(name="off", value="off")
    ])
    async def tts_cmd(self, interaction: discord.Interaction, mode: str):
        self.tts_enabled[interaction.guild.id] = True if mode == "on" else False
        await interaction.response.send_message(f"✅ TTS {mode.upper()}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild or message.content.startswith("/"):
            return
        if not self.tts_enabled.get(message.guild.id, False):
            return
        vc = message.guild.voice_client
        if not vc: return

        clean_text = message.content.replace("@", "")[:150]
        if not clean_text.strip(): return

        speak_text = f"{message.author.display_name} said {clean_text}"
        try:
            communicate = edge_tts.Communicate(speak_text, voice="en-US-GuyNeural")
            await communicate.save("tts.mp3")
            
            if vc.is_playing():
                vc.stop()
            
            vc.play(discord.FFmpegPCMAudio("tts.mp3"))
            while vc.is_playing():
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"TTS Error: {e}")

async def setup(bot):
    await bot.add_cog(TTS(bot))