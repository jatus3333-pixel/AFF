import discord
from discord.ext import commands
from discord import app_commands
import edge_tts
import asyncio

class TTS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tts_enabled = {}
        self.original_volume = {}

    @app_commands.command(name="tts", description="TTS on/off karo")
    @app_commands.choices(mode=[
        app_commands.Choice(name="on", value="on"),
        app_commands.Choice(name="off", value="off")
    ])
    async def tts_cmd(self, interaction: discord.Interaction, mode: str):
        self.tts_enabled[interaction.guild.id] = True if mode == "on" else False
        await interaction.response.send_message(f"✅ TTS {mode.upper()} - Ab gane ke beech me bhi bolega!", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild or message.content.startswith("/"):
            return
        
        if not self.tts_enabled.get(message.guild.id, False):
            return

        vc = message.guild.voice_client
        if not vc:
            return

        # Jo likha hai usko saaf karo
        clean_text = message.content.replace("@", "")[:150]
        if not clean_text.strip():
            return

        speak_text = f"{message.author.display_name} said {clean_text}"
        
        try:
            # 1. TTS file banao
            communicate = edge_tts.Communicate(speak_text, voice="en-US-GuyNeural")
            await communicate.save("tts.mp3")

            # 2. Agar gaana baj raha hai to uski awaz kam karo (Ducking)
            was_playing = False
            if vc.is_playing() and hasattr(vc.source, 'volume'):
                was_playing = True
                self.original_volume[message.guild.id] = vc.source.volume
                vc.source.volume = 0.10  # 10% pe kar diya
                await asyncio.sleep(0.5) # thoda gap taki ducking feel ho
                vc.stop() # gaana roko
            
            elif vc.is_playing():
                was_playing = True
                vc.stop()

            # 3. TTS bajao
            vc.play(discord.FFmpegPCMAudio("tts.mp3"))
            
            # 4. TTS khatam hone ka wait karo
            while vc.is_playing():
                await asyncio.sleep(0.5)

            # 5. Agar pehle gaana baj raha tha to wapas bajao
            # Ye tera music cog khud next gaana baja dega agar queue me hai
            # Isliye yahan kuch karne ki zarurat nahi, music cog auto continue karega

        except Exception as e:
            print(f"TTS Error: {e}")

async def setup(bot):
    await bot.add_cog(TTS(bot))