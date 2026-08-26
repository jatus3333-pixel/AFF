import asyncio
import json
import os
import re
from datetime import timedelta

import discord
from discord.ext import commands


# ============================================================
# HSL-CORP SECURITY
# ============================================================

DATA_FILE = "security_data.json"
GALI_FILE = "gali_data.json"


# ============================================================
# BOT OWNERS
# ============================================================

BOT_OWNER_IDS = {
    1519933809402056805,
    1435943252455981080,
    1517901703263944758,
    1128339001548476426,
}


# ============================================================
# OWNER ROLE IDS
# ============================================================

OWNER_ROLE_IDS = {
    1451197118025826364,
}


# ============================================================
# DEFAULT SETTINGS
# ============================================================

DEFAULT_SETTINGS = {
    "antinuke": True,
    "antibot": True,
    "antilink": True,
    "antimod": True,
    "antispam": True,
    "duplicate": True,
    "antigali": True,

    # ONLY Anti-Gali whitelist
    "whitelist_gali": [],

    # ONLY music/link whitelist
    "whitelist_music": [],

    # ONLY Anti-Bot whitelist
    "whitelist_bots": [],
}


# ============================================================
# SECURITY DATA
# ============================================================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data if isinstance(data, dict) else {}

    except Exception as e:
        print("[SECURITY] DATA LOAD ERROR:", repr(e))
        return {}


def save_data(data):
    try:
        temp_file = DATA_FILE + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

        os.replace(temp_file, DATA_FILE)

    except Exception as e:
        print("[SECURITY] DATA SAVE ERROR:", repr(e))


# ============================================================
# GALI DATA
# ============================================================

def load_gali_data():
    if not os.path.exists(GALI_FILE):
        return {}

    try:
        with open(GALI_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data if isinstance(data, dict) else {}

    except Exception as e:
        print("[GALI] DATA LOAD ERROR:", repr(e))
        return {}


def save_gali_data(data):
    try:
        temp_file = GALI_FILE + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

        os.replace(temp_file, GALI_FILE)

    except Exception as e:
        print("[GALI] DATA SAVE ERROR:", repr(e))


# ============================================================
# SECURITY COG
# ============================================================

class Security(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.data = load_data()
        self.gali_data = load_gali_data()

        self.duplicate_cache = {}

        print("🛡️ HSL-CORP Security loaded")


    # ========================================================
    # SETTINGS
    # ========================================================

    def get_settings(self, guild_id):

        guild_id = str(guild_id)

        if guild_id not in self.data:
            self.data[guild_id] = {}

        settings = self.data[guild_id]

        changed = False

        for key, default in DEFAULT_SETTINGS.items():

            if key not in settings:

                if isinstance(default, list):
                    settings[key] = list(default)
                else:
                    settings[key] = default

                changed = True

        # ----------------------------------------------------
        # Normalize all whitelist lists
        # ----------------------------------------------------

        for key in (
            "whitelist_gali",
            "whitelist_music",
            "whitelist_bots"
        ):

            value = settings.get(key, [])

            if not isinstance(value, list):
                value = []
                changed = True

            cleaned = []

            for item in value:
                try:
                    uid = int(item)

                    if uid not in cleaned:
                        cleaned.append(uid)

                except (TypeError, ValueError):
                    changed = True

            if cleaned != value:
                settings[key] = cleaned
                changed = True

        if changed:
            save_data(self.data)

        return settings


    # ========================================================
    # BOT OWNER
    # ========================================================

    async def is_bot_owner(self, user):

        if not user:
            return False

        if user.id in BOT_OWNER_IDS:
            return True

        try:
            return await self.bot.is_owner(user)

        except Exception as e:
            print(
                "[SECURITY] BOT OWNER CHECK ERROR:",
                repr(e)
            )

        return False


    # ========================================================
    # OWNER ROLE
    # ========================================================

    def has_owner_role(self, member):

        if not isinstance(member, discord.Member):
            return False

        return any(
            role.id in OWNER_ROLE_IDS
            for role in member.roles
        )


    # ========================================================
    # MASTER OWNER
    # ========================================================

    async def is_owner(self, member):

        if not isinstance(member, discord.Member):
            return False

        if not member.guild:
            return False

        # Server owner
        if member.id == member.guild.owner_id:
            return True

        # Bot owner
        if await self.is_bot_owner(member):
            return True

        # Configured owner role
        if self.has_owner_role(member):
            return True

        return False


    # ========================================================
    # OWNER ONLY
    # ========================================================

    async def owner_only_message(self, ctx):

        try:
            await ctx.send(
                "❌ **Only the Server Owner, Bot Owner, "
                "or configured Owner Role can use this command.**",
                delete_after=5
            )
        except Exception:
            pass


    # ========================================================
    # STATUS
    # ========================================================

    def status(self, value):
        return "🟢 **ON**" if value else "🔴 **OFF**"


    # ========================================================
    # GALI WORDS
    # ========================================================

    def get_gali_words(self, guild_id):

        guild_id = str(guild_id)

        words = self.gali_data.get(
            guild_id,
            []
        )

        if not isinstance(words, list):
            words = []

        cleaned = []

        for word in words:

            if not isinstance(word, str):
                continue

            word = re.sub(
                r"\s+",
                " ",
                word.strip().lower()
            )

            if word and word not in cleaned:
                cleaned.append(word)

        if cleaned != words:

            self.gali_data[guild_id] = cleaned
            save_gali_data(self.gali_data)

        return cleaned


    # ========================================================
    # FIND GALI
    # ========================================================

    def find_gali(self, guild_id, content):

        if not content:
            return None

        words = self.get_gali_words(guild_id)

        if not words:
            return None

        content = content.lower()

        for word in words:

            if not word:
                continue

            # ------------------------------------------------
            # Phrase
            # ------------------------------------------------

            if " " in word:

                if word in content:
                    return word

                continue

            # ------------------------------------------------
            # Single word
            # ------------------------------------------------

            pattern = (
                r"(?<!\w)"
                + re.escape(word)
                + r"(?!\w)"
            )

            try:

                if re.search(
                    pattern,
                    content,
                    flags=re.IGNORECASE
                ):
                    return word

            except re.error:
                if word in content:
                    return word

        return None


    # ========================================================
    # GALI WHITELIST CHECK
    #
    # VERY IMPORTANT:
    #
    # This checks ONLY whitelist_gali.
    #
    # It does NOT affect:
    # Anti-Link
    # Anti-Spam
    # Duplicate
    # Anti-Bot
    # etc.
    # ========================================================

    def gali_whitelisted(self, guild_id, user_id):

        settings = self.get_settings(guild_id)

        whitelist = settings.get(
            "whitelist_gali",
            []
        )

        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return False

        for allowed_id in whitelist:

            try:
                if int(allowed_id) == user_id:
                    return True

            except (TypeError, ValueError):
                continue

        return False


    # ========================================================
    # GALI BYPASS
    # ========================================================

    async def gali_bypass(self, member):

        if not isinstance(member, discord.Member):
            return False

        # ----------------------------------------------------
        # EXPLICIT GALI WHITELIST
        # ----------------------------------------------------

        if self.gali_whitelisted(
            member.guild.id,
            member.id
        ):
            return True

        # ----------------------------------------------------
        # Server owner
        # ----------------------------------------------------

        if member.id == member.guild.owner_id:
            return True

        # ----------------------------------------------------
        # Bot owners
        # ----------------------------------------------------

        if member.id in BOT_OWNER_IDS:
            return True

        # ----------------------------------------------------
        # Owner role
        # ----------------------------------------------------

        if self.has_owner_role(member):
            return True

        # ----------------------------------------------------
        # discord.py bot owner
        # ----------------------------------------------------

        try:

            if await self.bot.is_owner(member):
                return True

        except Exception:
            pass

        return False


    # ========================================================
    # SECURITY ANIMATION
    # ========================================================

    async def security_animation(self, ctx, enabled):

        try:

            message = await ctx.send(
                "```ansi\n"
                "\u001b[1;32m"
                "╔══════════════════════════════╗\n"
                "║                              ║\n"
                "║       H S L - C O R P        ║\n"
                "║                              ║\n"
                "║       ◐ INITIALIZING         ║\n"
                "║                              ║\n"
                "║       SECURITY SYSTEM        ║\n"
                "║                              ║\n"
                "╚══════════════════════════════╝\n"
                "\u001b[0m"
                "```"
            )

        except Exception:
            return

        spinner = ["◐", "◓", "◑", "◒"]

        systems = [
            ("🔗", "ANTI-LINK", "antilink"),
            ("🤖", "ANTI-BOT", "antibot"),
            ("☢️", "ANTI-NUKE", "antinuke"),
            ("🔨", "ANTI-MOD", "antimod"),
            ("💬", "ANTI-SPAM", "antispam"),
            ("♻️", "DUPLICATE GUARD", "duplicate"),
            ("🤬", "ANTI-GALI", "antigali")
        ]

        settings = self.get_settings(ctx.guild.id)

        # Initial animation
        for i in range(10):

            frame = spinner[i % len(spinner)]

            percentage = min(
                90,
                10 + i * 8
            )

            filled = int(percentage / 10)

            bar = (
                "█" * filled
                +
                "░" * (10 - filled)
            )

            try:

                await message.edit(
                    content=(
                        "```ansi\n"
                        "\u001b[1;32m"
                        "╔══════════════════════════════╗\n"
                        "║       HSL-CORP SECURITY      ║\n"
                        "╠══════════════════════════════╣\n"
                        "║                              ║\n"
                        f"║       {frame} SYSTEM CHECK      ║\n"
                        "║                              ║\n"
                        f"║       [{bar}] {percentage:>3}% ║\n"
                        "║                              ║\n"
                        "║       ▸ INITIALIZING...      ║\n"
                        "║                              ║\n"
                        "╚══════════════════════════════╝\n"
                        "\u001b[0m"
                        "```"
                    )
                )

                await asyncio.sleep(0.16)

            except Exception:
                break

        completed = []

        for index, (
            emoji,
            name,
            key
        ) in enumerate(systems):

            for frame_index in range(7):

                frame = spinner[
                    frame_index % len(spinner)
                ]

                percent = int(
                    (
                        index
                        +
                        frame_index / 7
                    )
                    / len(systems)
                    * 100
                )

                percent = min(percent, 99)

                bar_length = 20

                filled = int(
                    percent / 100 * bar_length
                )

                bar = (
                    "█" * filled
                    +
                    "░" * (
                        bar_length - filled
                    )
                )

                old_lines = ""

                for old in completed:

                    old_lines += (
                        f"║   {old[0]} "
                        f"{old[1]:<18} "
                        "✓ READY ║\n"
                    )

                try:

                    await message.edit(
                        content=(
                            "```ansi\n"
                            "\u001b[1;32m"
                            "╔══════════════════════════════╗\n"
                            "║       HSL-CORP SECURITY      ║\n"
                            "╠══════════════════════════════╣\n"
                            f"{old_lines}"
                            "║                              ║\n"
                            f"║   {frame} "
                            f"\u001b[1;37m"
                            f"{emoji} {name}"
                            "\u001b[1;32m      ║\n"
                            "║                              ║\n"
                            f"║   [{bar}] ║\n"
                            f"║             {percent:>3}%            ║\n"
                            "║                              ║\n"
                            "║   \u001b[1;33m◉ SCANNING SECURITY..."
                            "\u001b[1;32m ║\n"
                            "║                              ║\n"
                            "╚══════════════════════════════╝\n"
                            "\u001b[0m"
                            "```"
                        )
                    )

                    await asyncio.sleep(0.13)

                except Exception:
                    break

            settings[key] = enabled
            save_data(self.data)

            completed.append(
                (emoji, name)
            )

            old_lines = ""

            for old in completed:

                old_lines += (
                    f"║   {old[0]} "
                    f"{old[1]:<18} "
                    "✓ READY ║\n"
                )

            try:

                await message.edit(
                    content=(
                        "```ansi\n"
                        "\u001b[1;32m"
                        "╔══════════════════════════════╗\n"
                        "║       HSL-CORP SECURITY      ║\n"
                        "╠══════════════════════════════╣\n"
                        f"{old_lines}"
                        "║                              ║\n"
                        f"║       {emoji} "
                        f"\u001b[1;37m{name}\u001b[1;32m       ║\n"
                        "║                              ║\n"
                        "║       ████████████████████   ║\n"
                        "║            100%              ║\n"
                        "║                              ║\n"
                        "║       \u001b[1;32m✓ PROTECTED"
                        "\u001b[1;32m         ║\n"
                        "║                              ║\n"
                        "╚══════════════════════════════╝\n"
                        "\u001b[0m"
                        "```"
                    )
                )

                await asyncio.sleep(0.45)

            except Exception:
                pass

        final_text = (
            "SYSTEM ONLINE"
            if enabled
            else
            "SYSTEM OFFLINE"
        )

        for i in range(8):

            frame = spinner[i % len(spinner)]

            try:

                await message.edit(
                    content=(
                        "```ansi\n"
                        "\u001b[1;32m"
                        "╔══════════════════════════════╗\n"
                        "║                              ║\n"
                        "║       H S L - C O R P        ║\n"
                        "║                              ║\n"
                        f"║       {frame} "
                        f"\u001b[1;37m"
                        f"{final_text}"
                        "\u001b[1;32m       ║\n"
                        "║                              ║\n"
                        "║       ✓ ANTI-LINK            ║\n"
                        "║       ✓ ANTI-BOT             ║\n"
                        "║       ✓ ANTI-NUKE            ║\n"
                        "║       ✓ ANTI-MOD             ║\n"
                        "║       ✓ ANTI-SPAM            ║\n"
                        "║       ✓ DUPLICATE GUARD      ║\n"
                        "║       ✓ ANTI-GALI            ║\n"
                        "║                              ║\n"
                        "║   ████████████████████████   ║\n"
                        "║          100% SECURE         ║\n"
                        "║                              ║\n"
                        "╚══════════════════════════════╝\n"
                        "\u001b[0m"
                        "```"
                    )
                )

                await asyncio.sleep(0.18)

            except Exception:
                break

        await asyncio.sleep(5)

        try:
            await message.delete()
        except Exception:
            pass


    # ========================================================
    # ANTINUKE ENABLE
    # ========================================================

    @commands.hybrid_command(
        name="antinukeenable",
        description="Enable HSL-CORP security"
    )
    @commands.guild_only()
    async def antinukeenable(self, ctx):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        await self.security_animation(
            ctx,
            True
        )


    # ========================================================
    # ANTINUKE DISABLE
    # ========================================================

    @commands.hybrid_command(
        name="antinukedisable",
        description="Disable HSL-CORP security"
    )
    @commands.guild_only()
    async def antinukedisable(self, ctx):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        await self.security_animation(
            ctx,
            False
        )


    # ========================================================
    # AUTOMOD STATUS
    # ========================================================

    @commands.hybrid_command(
        name="automodstatus",
        description="Show HSL-CORP security status"
    )
    @commands.guild_only()
    async def automodstatus(self, ctx):

        settings = self.get_settings(
            ctx.guild.id
        )

        embed = discord.Embed(
            title="🛡️ HSL-CORP SECURITY STATUS",
            description=(
                "```ansi\n"
                "\u001b[1;32m"
                "╔══════════════════════════╗\n"
                "║    SECURITY MONITOR      ║\n"
                "╠══════════════════════════╣\n"
                f"║ 🔗 Anti-Link      "
                f"{'🟢 ON' if settings['antilink'] else '🔴 OFF'} ║\n"
                f"║ 🤖 Anti-Bot       "
                f"{'🟢 ON' if settings['antibot'] else '🔴 OFF'} ║\n"
                f"║ ☢️ Anti-Nuke      "
                f"{'🟢 ON' if settings['antinuke'] else '🔴 OFF'} ║\n"
                f"║ 🔨 Anti-Mod       "
                f"{'🟢 ON' if settings['antimod'] else '🔴 OFF'} ║\n"
                f"║ 💬 Anti-Spam      "
                f"{'🟢 ON' if settings['antispam'] else '🔴 OFF'} ║\n"
                f"║ ♻️ Duplicate      "
                f"{'🟢 ON' if settings['duplicate'] else '🔴 OFF'} ║\n"
                f"║ 🤬 Anti-Gali      "
                f"{'🟢 ON' if settings['antigali'] else '🔴 OFF'} ║\n"
                "╚══════════════════════════╝\n"
                "\u001b[0m"
                "```"
            ),
            color=discord.Color.dark_green()
        )

        embed.set_footer(
            text="HSL-CORP • Security System"
        )

        await ctx.send(embed=embed)


    # ========================================================
    # CLEAR
    # ========================================================

    @commands.hybrid_command(
        name="clear",
        description="Delete messages"
    )
    @commands.guild_only()
    async def clear(self, ctx, amount: int):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        if amount < 1 or amount > 100:

            return await ctx.send(
                "❌ Amount `1-100` ke beech hona chahiye.",
                delete_after=4
            )

        try:

            deleted = await ctx.channel.purge(
                limit=amount + 1
            )

            count = len(deleted)

            if (
                ctx.message
                and
                ctx.message in deleted
            ):
                count -= 1

            count = max(0, count)

            msg = await ctx.send(
                f"🧹 **{count} messages cleared.**"
            )

            await asyncio.sleep(3)

            try:
                await msg.delete()
            except Exception:
                pass

        except discord.Forbidden:

            await ctx.send(
                "❌ Mujhe messages delete karne ki permission nahi hai.",
                delete_after=5
            )

        except Exception as e:

            print(
                "[SECURITY] CLEAR ERROR:",
                repr(e)
            )


    # ========================================================
    # SAY
    # ========================================================

    @commands.hybrid_command(
        name="say",
        description="Send a message as HSL-CORP"
    )
    @commands.guild_only()
    async def say(self, ctx, *, text: str):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        if not text or not text.strip():

            return await ctx.send(
                "❌ **Message empty nahi ho sakta.**\n"
                "Use: `!say Hello`",
                delete_after=5
            )

        try:

            await ctx.send(
                text.strip(),
                allowed_mentions=discord.AllowedMentions.none()
            )

            if ctx.message:

                try:
                    await ctx.message.delete()
                except Exception:
                    pass

        except discord.Forbidden:

            try:
                await ctx.send(
                    "❌ **Mujhe message send karne ki permission nahi hai.**",
                    delete_after=5
                )
            except Exception:
                pass

        except Exception as e:

            print(
                "[SECURITY] SAY ERROR:",
                repr(e)
            )


    # ========================================================
    # ADD GALI
    # ========================================================

    @commands.hybrid_command(
        name="addgali",
        description="Add a word to Anti-Gali filter"
    )
    @commands.guild_only()
    async def addgali(self, ctx, *, word: str):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        word = re.sub(
            r"\s+",
            " ",
            word.strip().lower()
        )

        if not word:

            return await ctx.send(
                "❌ Gali word empty nahi ho sakta.",
                delete_after=5
            )

        guild_id = str(ctx.guild.id)

        words = self.get_gali_words(
            guild_id
        )

        if word in words:

            return await ctx.send(
                f"🟡 `{word}` **already Anti-Gali list mein hai.**",
                delete_after=5
            )

        words.append(word)

        self.gali_data[guild_id] = words

        save_gali_data(
            self.gali_data
        )

        await ctx.send(
            f"🔴 **ANTI-GALI**\n"
            f"`{word}` successfully add kar diya.\n"
            f"Total blocked words: **{len(words)}**",
            delete_after=7
        )


    # ========================================================
    # REMOVE GALI
    # ========================================================

    @commands.hybrid_command(
        name="removegali",
        description="Remove a word from Anti-Gali filter"
    )
    @commands.guild_only()
    async def removegali(self, ctx, *, word: str):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        word = re.sub(
            r"\s+",
            " ",
            word.strip().lower()
        )

        words = self.get_gali_words(
            ctx.guild.id
        )

        if word not in words:

            return await ctx.send(
                f"🟡 `{word}` **Anti-Gali list mein nahi hai.**",
                delete_after=5
            )

        words.remove(word)

        self.gali_data[str(ctx.guild.id)] = words

        save_gali_data(
            self.gali_data
        )

        await ctx.send(
            f"🟢 **ANTI-GALI**\n"
            f"`{word}` list se remove kar diya.",
            delete_after=6
        )


    # ========================================================
    # GALI LIST
    # ========================================================

    @commands.hybrid_command(
        name="galilist",
        description="Show Anti-Gali blocked words"
    )
    @commands.guild_only()
    async def galilist(self, ctx):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        words = self.get_gali_words(
            ctx.guild.id
        )

        if not words:

            return await ctx.send(
                "🟢 **Anti-Gali list empty hai.**\n"
                "Use `/addgali word:` to add a word.",
                delete_after=7
            )

        display_words = words[:100]

        description = "\n".join(
            f"`{index}.` `{word}`"
            for index, word in enumerate(
                display_words,
                start=1
            )
        )

        embed = discord.Embed(
            title="🤬 HSL-CORP ANTI-GALI",
            description=description,
            color=discord.Color.red()
        )

        embed.add_field(
            name="Blocked Words",
            value=str(len(words)),
            inline=True
        )

        embed.add_field(
            name="Status",
            value="🟢 ENABLED",
            inline=True
        )

        embed.set_footer(
            text="HSL-CORP • Anti-Gali System"
        )

        await ctx.send(embed=embed)


    # ========================================================
    # WHITELIST GALI
    #
    # USAGE:
    #
    # /whitelistgali @member
    #      -> toggle
    #
    # /whitelistgali @member add
    #      -> add
    #
    # /whitelistgali @member remove
    #      -> remove
    #
    # /whitelistgali
    #      -> list
    #
    # IMPORTANT:
    # whitelist affects ONLY Anti-Gali.
    # ========================================================

    @commands.hybrid_command(
        name="whitelistgali",
        description="Manage Anti-Gali member whitelist"
    )
    @commands.guild_only()
    async def whitelistgali(
        self,
        ctx,
        member: discord.Member = None,
        action: str = "toggle"
    ):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        settings = self.get_settings(
            ctx.guild.id
        )

        users = settings.get(
            "whitelist_gali",
            []
        )

        # Normalize
        normalized = []

        for uid in users:

            try:
                uid = int(uid)

                if uid not in normalized:
                    normalized.append(uid)

            except (TypeError, ValueError):
                pass

        settings["whitelist_gali"] = normalized
        users = normalized

        # ----------------------------------------------------
        # LIST
        # ----------------------------------------------------

        if member is None:

            if not users:

                embed = discord.Embed(
                    title="🤬 HSL-CORP GALI WHITELIST",
                    description=(
                        "No members are currently "
                        "whitelisted for Anti-Gali."
                    ),
                    color=discord.Color.orange()
                )

                embed.set_footer(
                    text="Only Anti-Gali is bypassed."
                )

                return await ctx.send(embed=embed)

            lines = []

            for index, uid in enumerate(
                users,
                start=1
            ):

                guild_member = ctx.guild.get_member(uid)

                if guild_member:

                    lines.append(
                        f"**{index}.** "
                        f"{guild_member.mention} "
                        f"`{uid}`"
                    )

                else:

                    lines.append(
                        f"**{index}.** "
                        f"<@{uid}> "
                        f"`{uid}`"
                    )

            embed = discord.Embed(
                title="🤬 HSL-CORP GALI WHITELIST",
                description="\n".join(lines),
                color=discord.Color.green()
            )

            embed.add_field(
                name="Permission",
                value=(
                    "Whitelisted members can use blocked "
                    "gali words without Anti-Gali action."
                ),
                inline=False
            )

            embed.add_field(
                name="Other Security",
                value="🛡️ UNAFFECTED",
                inline=True
            )

            return await ctx.send(embed=embed)

        # ----------------------------------------------------
        # ACTION NORMALIZE
        # ----------------------------------------------------

        action = str(
            action
        ).strip().lower()

        # ----------------------------------------------------
        # ADD
        # ----------------------------------------------------

        if action in (
            "add",
            "on",
            "enable"
        ):

            if member.id in users:

                return await ctx.send(
                    f"🟢 {member.mention} "
                    "**already Gali whitelist mein hai.**",
                    delete_after=5
                )

            users.append(member.id)

            settings["whitelist_gali"] = list(
                dict.fromkeys(users)
            )

            save_data(self.data)

            return await ctx.send(
                f"🟢 {member.mention} "
                "**Gali whitelist mein add ho gaya.**\n\n"
                "🤬 **Anti-Gali:** BYPASSED\n"
                "🔗 **Anti-Link:** UNAFFECTED\n"
                "💬 **Anti-Spam:** UNAFFECTED\n"
                "♻️ **Duplicate:** UNAFFECTED\n"
                "🤖 **Anti-Bot:** UNAFFECTED",
                delete_after=10
            )

        # ----------------------------------------------------
        # REMOVE
        # ----------------------------------------------------

        if action in (
            "remove",
            "delete",
            "del",
            "off",
            "disable"
        ):

            if member.id not in users:

                return await ctx.send(
                    f"🟡 {member.mention} "
                    "**Gali whitelist mein nahi hai.**",
                    delete_after=5
                )

            users.remove(member.id)

            settings["whitelist_gali"] = users

            save_data(self.data)

            return await ctx.send(
                f"🔴 {member.mention} "
                "**Gali whitelist se remove ho gaya.**\n"
                "❌ Ab Anti-Gali is member par normally apply hoga.",
                delete_after=7
            )

        # ----------------------------------------------------
        # TOGGLE
        # ----------------------------------------------------

        if action == "toggle":

            if member.id in users:

                users.remove(member.id)

                settings["whitelist_gali"] = users

                save_data(self.data)

                return await ctx.send(
                    f"🔴 {member.mention} "
                    "**Gali whitelist se remove ho gaya.**",
                    delete_after=6
                )

            users.append(member.id)

            settings["whitelist_gali"] = list(
                dict.fromkeys(users)
            )

            save_data(self.data)

            return await ctx.send(
                f"🟢 {member.mention} "
                "**Gali whitelist mein add ho gaya.**\n"
                "🤬 Ab sirf Anti-Gali bypass hoga.",
                delete_after=8
            )

        # ----------------------------------------------------
        # INVALID
        # ----------------------------------------------------

        await ctx.send(
            "❌ **Invalid action.**\n\n"
            "`/whitelistgali @User`\n"
            "`/whitelistgali @User add`\n"
            "`/whitelistgali @User remove`",
            delete_after=8
        )


    # ========================================================
    # WHITELIST BOT
    # ========================================================

    @commands.hybrid_command(
        name="whitelistbot",
        description="Whitelist or remove a bot from Anti-Bot"
    )
    @commands.guild_only()
    async def whitelistbot(
        self,
        ctx,
        bot_id: str,
        action: str = "add"
    ):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        try:

            cleaned = (
                bot_id
                .strip()
                .replace("<@", "")
                .replace(">", "")
                .replace("!", "")
            )

            uid = int(cleaned)

            user = await self.bot.fetch_user(uid)

        except Exception:

            return await ctx.send(
                "❌ Sahi Bot ID / Mention daalo.",
                delete_after=5
            )

        if not user.bot:

            return await ctx.send(
                "❌ Ye member bot nahi hai.",
                delete_after=5
            )

        settings = self.get_settings(
            ctx.guild.id
        )

        bots = settings.get(
            "whitelist_bots",
            []
        )

        normalized = []

        for b in bots:

            try:

                b = int(b)

                if b not in normalized:
                    normalized.append(b)

            except (TypeError, ValueError):
                pass

        bots = normalized

        action = str(
            action
        ).strip().lower()

        # Add
        if action in (
            "add",
            "on",
            "enable",
            "toggle"
        ):

            if uid in bots:

                return await ctx.send(
                    f"🟢 {user.mention} "
                    "**already whitelist mein hai.**",
                    delete_after=5
                )

            bots.append(uid)

            settings["whitelist_bots"] = bots

            save_data(self.data)

            return await ctx.send(
                f"🤖 {user.mention} "
                "**successfully bot whitelist mein add ho gaya.**\n"
                "✅ Ab Anti-Bot is bot ko allow karega.",
                delete_after=7
            )

        # Remove
        if action in (
            "remove",
            "delete",
            "del",
            "off",
            "disable"
        ):

            if uid not in bots:

                return await ctx.send(
                    f"🟡 {user.mention} "
                    "**bot whitelist mein nahi hai.**",
                    delete_after=5
                )

            bots.remove(uid)

            settings["whitelist_bots"] = bots

            save_data(self.data)

            return await ctx.send(
                f"🔴 {user.mention} "
                "**bot whitelist se remove ho gaya.**",
                delete_after=6
            )

        await ctx.send(
            "❌ Invalid action.",
            delete_after=5
        )


    # ========================================================
    # LIST WHITELISTED BOTS
    # ========================================================

    @commands.hybrid_command(
        name="whitelistbots",
        description="Show whitelisted bots"
    )
    @commands.guild_only()
    async def whitelistbots(self, ctx):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        settings = self.get_settings(
            ctx.guild.id
        )

        bots = settings.get(
            "whitelist_bots",
            []
        )

        if not bots:

            return await ctx.send(
                "🤖 **No bots are currently whitelisted.**",
                delete_after=6
            )

        lines = []

        for index, bot_id in enumerate(
            bots,
            start=1
        ):

            try:
                bot_id = int(bot_id)
            except:
                continue

            bot_member = ctx.guild.get_member(
                bot_id
            )

            if bot_member:

                lines.append(
                    f"**{index}.** "
                    f"{bot_member.mention} "
                    f"`{bot_member.id}`"
                )

            else:

                lines.append(
                    f"**{index}.** "
                    f"<@{bot_id}> "
                    f"`{bot_id}`"
                )

        embed = discord.Embed(
            title="🤖 HSL-CORP BOT WHITELIST",
            description="\n".join(lines),
            color=discord.Color.green()
        )

        embed.set_footer(
            text="Only Server Owner / Bot Owner / Owner Role can manage this."
        )

        await ctx.send(embed=embed)


    # ========================================================
    # MUSIC WHITELIST
    # ========================================================

    @commands.hybrid_command(
        name="whitelist",
        description="Manage music link whitelist"
    )
    @commands.guild_only()
    async def whitelist(
        self,
        ctx,
        member: discord.Member = None,
        action: str = "toggle"
    ):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        settings = self.get_settings(
            ctx.guild.id
        )

        users = settings.get(
            "whitelist_music",
            []
        )

        normalized = []

        for uid in users:

            try:

                uid = int(uid)

                if uid not in normalized:
                    normalized.append(uid)

            except:
                pass

        users = normalized

        settings["whitelist_music"] = users

        # List
        if member is None:

            if not users:

                return await ctx.send(
                    "🎵 **No members are currently music-whitelisted.**",
                    delete_after=6
                )

            lines = []

            for index, uid in enumerate(
                users,
                start=1
            ):

                guild_member = ctx.guild.get_member(uid)

                if guild_member:

                    lines.append(
                        f"**{index}.** "
                        f"{guild_member.mention} "
                        f"`{uid}`"
                    )

                else:

                    lines.append(
                        f"**{index}.** "
                        f"<@{uid}> "
                        f"`{uid}`"
                    )

            embed = discord.Embed(
                title="🎵 HSL-CORP MUSIC WHITELIST",
                description="\n".join(lines),
                color=discord.Color.green()
            )

            await ctx.send(embed=embed)

            return

        action = str(
            action
        ).strip().lower()

        # Add
        if action in (
            "add",
            "on",
            "enable"
        ):

            if member.id in users:

                return await ctx.send(
                    f"🟢 {member.mention} "
                    "**already music whitelist mein hai.**",
                    delete_after=5
                )

            users.append(member.id)

            settings["whitelist_music"] = users

            save_data(self.data)

            return await ctx.send(
                f"🟢 {member.mention} "
                "**music whitelist mein add ho gaya.**",
                delete_after=8
            )

        # Remove
        if action in (
            "remove",
            "delete",
            "del",
            "off",
            "disable"
        ):

            if member.id not in users:

                return await ctx.send(
                    f"🟡 {member.mention} "
                    "**music whitelist mein nahi hai.**",
                    delete_after=5
                )

            users.remove(member.id)

            settings["whitelist_music"] = users

            save_data(self.data)

            return await ctx.send(
                f"🔴 {member.mention} "
                "**music whitelist se remove ho gaya.**",
                delete_after=6
            )

        # Toggle
        if action == "toggle":

            if member.id in users:

                users.remove(member.id)

                settings["whitelist_music"] = users

                save_data(self.data)

                return await ctx.send(
                    f"🔴 {member.mention} "
                    "**music whitelist se remove ho gaya.**",
                    delete_after=6
                )

            users.append(member.id)

            settings["whitelist_music"] = users

            save_data(self.data)

            return await ctx.send(
                f"🟢 {member.mention} "
                "**music whitelist mein add ho gaya.**",
                delete_after=8
            )

        await ctx.send(
            "❌ Invalid action.",
            delete_after=6
        )


    # ========================================================
    # MUSIC WHITELIST CHECK
    # ========================================================

    def music_whitelisted(
        self,
        guild_id,
        user_id
    ):

        settings = self.get_settings(
            guild_id
        )

        try:
            user_id = int(user_id)
        except:
            return False

        for uid in settings.get(
            "whitelist_music",
            []
        ):

            try:

                if int(uid) == user_id:
                    return True

            except:
                continue

        return False


    # ========================================================
    # MUSIC COMMAND DETECTION
    # ========================================================

    def is_music_command(self, content):

        if not content:
            return False

        content = content.strip().lower()

        if not content:
            return False

        first_word = content.split(
            maxsplit=1
        )[0]

        return first_word in (
            "!play",
            "!p",
            "/play",
            "/p"
        )


    # ========================================================
    # GIVE ROLE
    # ========================================================

    @commands.command(name="giverole")
    @commands.guild_only()
    async def giverole(
        self,
        ctx,
        member: discord.Member,
        role: discord.Role
    ):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        if role.is_default():

            return await ctx.send(
                "❌ `@everyone` role assign nahi kar sakte.",
                delete_after=5
            )

        if role.managed:

            return await ctx.send(
                "❌ Ye managed role hai.",
                delete_after=5
            )

        me = ctx.guild.me

        if not me:

            return await ctx.send(
                "❌ Bot member information unavailable.",
                delete_after=5
            )

        if role >= me.top_role:

            return await ctx.send(
                "❌ Ye role bot ke highest role se upar hai.",
                delete_after=5
            )

        try:

            await member.add_roles(
                role,
                reason=f"HSL Security giverole by {ctx.author}"
            )

            await ctx.send(
                f"✅ {role.mention} "
                f"**{member.mention} ko de diya.**",
                delete_after=5
            )

        except discord.Forbidden:

            await ctx.send(
                "❌ Role assign karne ki permission nahi hai.",
                delete_after=5
            )

        except Exception as e:

            print(
                "[SECURITY] GIVEROLE ERROR:",
                repr(e)
            )


    # ========================================================
    # REMOVE ROLE
    # ========================================================

    @commands.command(name="removerole")
    @commands.guild_only()
    async def removerole(
        self,
        ctx,
        member: discord.Member,
        role: discord.Role
    ):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        if role.is_default():

            return await ctx.send(
                "❌ `@everyone` role remove nahi kar sakte.",
                delete_after=5
            )

        if role.managed:

            return await ctx.send(
                "❌ Ye managed role hai.",
                delete_after=5
            )

        me = ctx.guild.me

        if not me:

            return await ctx.send(
                "❌ Bot member information unavailable.",
                delete_after=5
            )

        if role >= me.top_role:

            return await ctx.send(
                "❌ Ye role bot ke highest role se upar hai.",
                delete_after=5
            )

        if role not in member.roles:

            return await ctx.send(
                f"🟡 {member.mention} ke paas "
                f"{role.mention} role hai hi nahi.",
                delete_after=5
            )

        try:

            await member.remove_roles(
                role,
                reason=f"HSL Security removerole by {ctx.author}"
            )

            await ctx.send(
                f"✅ {role.mention} "
                f"**{member.mention} se remove kar diya.**",
                delete_after=5
            )

        except discord.Forbidden:

            await ctx.send(
                "❌ Role remove karne ki permission nahi hai.",
                delete_after=5
            )

        except Exception as e:

            print(
                "[SECURITY] REMOVEROLE ERROR:",
                repr(e)
            )


    # ========================================================
    # STRICT ANTI-BOT
    # ========================================================

    @commands.Cog.listener()
    async def on_member_join(self, member):

        if not member.bot:
            return

        guild = member.guild

        settings = self.get_settings(
            guild.id
        )

        if not settings.get(
            "antibot",
            True
        ):
            return

        whitelist = settings.get(
            "whitelist_bots",
            []
        )

        try:

            if member.id in {
                int(x)
                for x in whitelist
            }:

                print(
                    f"[SECURITY] ✅ WHITELISTED BOT ALLOWED: "
                    f"{member} ({member.id})"
                )

                return

        except Exception:
            pass

        print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        print(
            "🚨 HSL-CORP ANTI-BOT DETECTED"
        )

        print(
            f"🤖 Bot: {member} ({member.id})"
        )

        inviter = None

        for _ in range(12):

            try:

                await asyncio.sleep(0.75)

                async for entry in guild.audit_logs(
                    limit=50,
                    action=discord.AuditLogAction.bot_add
                ):

                    if not entry.target:
                        continue

                    if entry.target.id != member.id:
                        continue

                    age = (
                        discord.utils.utcnow()
                        -
                        entry.created_at
                    ).total_seconds()

                    if age < 0 or age > 30:
                        continue

                    inviter = entry.user
                    break

                if inviter:
                    break

            except discord.Forbidden:

                print(
                    "[SECURITY] ❌ Cannot read audit logs."
                )

                break

            except discord.HTTPException as e:

                print(
                    "[SECURITY] Audit HTTP error:",
                    repr(e)
                )

            except Exception as e:

                print(
                    "[SECURITY] Audit log error:",
                    repr(e)
                )

        if inviter is None:

            print(
                "[SECURITY] ⚠️ Inviter not found."
            )

            await self.kick_unauthorized_bot(member)

            return

        # Server owner allowed
        if inviter.id == guild.owner_id:

            print(
                f"[SECURITY] 👑 SERVER OWNER "
                f"{inviter} added bot."
            )

            return

        inviter_member = None

        try:

            inviter_member = guild.get_member(
                inviter.id
            )

            if inviter_member is None:

                inviter_member = await guild.fetch_member(
                    inviter.id
                )

        except Exception as e:

            print(
                "[SECURITY] Inviter fetch error:",
                repr(e)
            )

        await self.kick_unauthorized_bot(
            member
        )

        if inviter_member:

            await self.remove_inviter_roles(
                inviter_member
            )

        print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )


    # ========================================================
    # KICK BOT
    # ========================================================

    async def kick_unauthorized_bot(self, member):

        guild = member.guild
        me = guild.me

        if me is None:
            return False

        if not me.guild_permissions.kick_members:

            print(
                "[SECURITY] ❌ HSL-CORP lacks Kick Members."
            )

            return False

        if self.bot.user and member.id == self.bot.user.id:
            return False

        if member.top_role >= me.top_role:

            print(
                "[SECURITY] ❌ KICK BLOCKED BY ROLE HIERARCHY."
            )

            return False

        try:

            await member.kick(
                reason=(
                    "HSL-CORP Security - "
                    "Unauthorized bot addition"
                )
            )

            print(
                f"[SECURITY] ✅ BOT KICKED: {member}"
            )

            return True

        except Exception as e:

            print(
                "[SECURITY] ❌ Kick error:",
                repr(e)
            )

        return False


    # ========================================================
    # REMOVE INVITER ROLES
    # ========================================================

    async def remove_inviter_roles(self, member):

        if not member:
            return

        guild = member.guild

        if member.id == guild.owner_id:
            return

        me = guild.me

        if me is None:
            return

        if not me.guild_permissions.manage_roles:

            print(
                "[SECURITY] ❌ HSL-CORP lacks Manage Roles."
            )

            return

        removable_roles = []

        for role in member.roles:

            if role.is_default():
                continue

            if role.managed:
                continue

            if role >= me.top_role:
                continue

            removable_roles.append(role)

        for role in removable_roles:

            try:

                await member.remove_roles(
                    role,
                    reason=(
                        "HSL-CORP Security - "
                        "Unauthorized bot addition"
                    )
                )

                await asyncio.sleep(0.2)

            except Exception as e:

                print(
                    "[SECURITY] ROLE REMOVE ERROR:",
                    repr(e)
                )


    # ========================================================
    # MESSAGE SECURITY
    # ========================================================

    @commands.Cog.listener()
    async def on_message(self, message):

        # ----------------------------------------------------
        # Ignore bot messages
        # ----------------------------------------------------

        if message.author.bot:
            return

        # ----------------------------------------------------
        # Ignore DMs
        # ----------------------------------------------------

        if not message.guild:
            return

        settings = self.get_settings(
            message.guild.id
        )

        content = (
            message.content
            or ""
        ).strip()

        lower_content = content.lower()

        # ====================================================
        # ANTI-GALI
        # ====================================================

        if settings.get(
            "antigali",
            True
        ):

            # ------------------------------------------------
            # THIS IS THE CRITICAL PART
            #
            # If member is in whitelist_gali:
            # DO NOT even call find_gali()
            # DO NOT delete
            # DO NOT timeout
            # DO NOT warning
            # ------------------------------------------------

            is_gali_whitelisted = (
                self.gali_whitelisted(
                    message.guild.id,
                    message.author.id
                )
            )

            if not is_gali_whitelisted:

                # Owner bypass
                bypass = await self.gali_bypass(
                    message.author
                )

                if not bypass:

                    detected_gali = self.find_gali(
                        message.guild.id,
                        content
                    )

                    if detected_gali:

                        print(
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        )

                        print(
                            "[SECURITY] 🚨 GALI DETECTED"
                        )

                        print(
                            f"[SECURITY] User: "
                            f"{message.author} "
                            f"({message.author.id})"
                        )

                        print(
                            f"[SECURITY] Word: "
                            f"{detected_gali}"
                        )

                        # ------------------------------------
                        # DELETE
                        # ------------------------------------

                        try:

                            await message.delete()

                        except discord.NotFound:
                            pass

                        except discord.Forbidden:

                            print(
                                "[GALI] ❌ Cannot delete message."
                            )

                        except Exception as e:

                            print(
                                "[GALI] DELETE ERROR:",
                                repr(e)
                            )

                        # ------------------------------------
                        # TIMEOUT
                        # ------------------------------------

                        try:

                            await message.author.timeout(
                                timedelta(minutes=10),
                                reason=(
                                    "HSL-CORP Anti-Gali - "
                                    "Blocked word"
                                )
                            )

                        except discord.Forbidden:

                            print(
                                "[GALI] ❌ Cannot timeout user."
                            )

                        except discord.HTTPException as e:

                            print(
                                "[GALI] TIMEOUT HTTP ERROR:",
                                repr(e)
                            )

                        except Exception as e:

                            print(
                                "[GALI] TIMEOUT ERROR:",
                                repr(e)
                            )

                        # ------------------------------------
                        # WARNING
                        # ------------------------------------

                        try:

                            warning = await message.channel.send(
                                f"🤬 {message.author.mention} "
                                "**gali detected — 10 minute timeout.**"
                            )

                            await asyncio.sleep(3)

                            try:
                                await warning.delete()
                            except Exception:
                                pass

                        except Exception:
                            pass

                        print(
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                        )

                        return

        # ====================================================
        # DUPLICATE
        # ====================================================

        if settings.get(
            "duplicate",
            True
        ):

            key = (
                message.guild.id,
                message.author.id
            )

            old = self.duplicate_cache.get(
                key
            )

            if (
                old is not None
                and
                old == message.content
            ):

                try:
                    await message.delete()
                except Exception:
                    pass

                try:

                    warning = await message.channel.send(
                        f"⚠️ {message.author.mention} "
                        "**duplicate message detected.**"
                    )

                    await asyncio.sleep(2)

                    try:
                        await warning.delete()
                    except Exception:
                        pass

                except Exception:
                    pass

                return

            self.duplicate_cache[key] = message.content

            asyncio.create_task(
                self.clear_duplicate(
                    key,
                    message.content
                )
            )

        # ====================================================
        # ANTI-LINK
        # ====================================================

        if settings.get(
            "antilink",
            True
        ):

            link_patterns = (
                "http://",
                "https://",
                "www.",
                "discord.gg/",
                "discord.com/invite/"
            )

            is_link = any(
                pattern in lower_content
                for pattern in link_patterns
            )

            if is_link:

                # Server owner bypass
                if message.author.id == message.guild.owner_id:
                    return

                # Bot owner bypass
                if message.author.id in BOT_OWNER_IDS:
                    return

                # Owner role bypass
                if self.has_owner_role(message.author):
                    return

                # discord.py bot owner
                try:

                    if await self.bot.is_owner(
                        message.author
                    ):
                        return

                except Exception:
                    pass

                # Music command whitelist
                if self.is_music_command(content):

                    if self.music_whitelisted(
                        message.guild.id,
                        message.author.id
                    ):
                        return

                # Delete link
                try:

                    await message.delete()

                except discord.NotFound:
                    pass

                except discord.Forbidden:

                    print(
                        "[SECURITY] ❌ Cannot delete link."
                    )

                except Exception as e:

                    print(
                        "[SECURITY] LINK DELETE ERROR:",
                        repr(e)
                    )

                # Timeout
                try:

                    await message.author.timeout(
                        timedelta(minutes=10),
                        reason=(
                            "HSL Anti-Link - "
                            "Unauthorized link"
                        )
                    )

                except Exception as e:

                    print(
                        "[SECURITY] LINK TIMEOUT ERROR:",
                        repr(e)
                    )

                # Warning
                try:

                    warning = await message.channel.send(
                        f"🔗 {message.author.mention} "
                        "**link detected — 10 minute timeout.**"
                    )

                    await asyncio.sleep(2)

                    try:
                        await warning.delete()
                    except Exception:
                        pass

                except Exception:
                    pass

                return


    # ========================================================
    # CLEAR DUPLICATE CACHE
    # ========================================================

    async def clear_duplicate(
        self,
        key,
        content
    ):

        await asyncio.sleep(10)

        if self.duplicate_cache.get(key) == content:

            self.duplicate_cache.pop(
                key,
                None
            )


    # ========================================================
    # COMMAND ERROR
    # ========================================================

    @commands.Cog.listener()
    async def on_command_error(
        self,
        ctx,
        error
    ):

        # Ignore command not found
        if isinstance(
            error,
            commands.CommandNotFound
        ):
            return

        # Missing argument
        if isinstance(
            error,
            commands.MissingRequiredArgument
        ):

            try:

                await ctx.send(
                    "❌ **Missing argument.** "
                    "Command ko sahi format mein use karo.",
                    delete_after=5
                )

            except Exception:
                pass

            return

        # Member not found
        if isinstance(
            error,
            commands.MemberNotFound
        ):

            try:

                await ctx.send(
                    "❌ **Member nahi mila.**",
                    delete_after=5
                )

            except Exception:
                pass

            return

        # Role not found
        if isinstance(
            error,
            commands.RoleNotFound
        ):

            try:

                await ctx.send(
                    "❌ **Role nahi mila.**",
                    delete_after=5
                )

            except Exception:
                pass

            return

        # Bad argument
        if isinstance(
            error,
            commands.BadArgument
        ):

            try:

                await ctx.send(
                    "❌ **Invalid argument.**",
                    delete_after=5
                )

            except Exception:
                pass

            return

        print(
            "[SECURITY] COMMAND ERROR:",
            repr(error)
        )


    # ========================================================
    # READY
    # ========================================================

    @commands.Cog.listener()
    async def on_ready(self):

        print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        print(
            "🛡️ HSL-CORP SECURITY ONLINE"
        )

        print(
            "👑 Server Owner: ALLOWED"
        )

        print(
            "🤖 Bot Owners: ALLOWED"
        )

        print(
            f"🎭 Owner Roles: "
            f"{len(OWNER_ROLE_IDS)}"
        )

        print(
            "🤖 Strict Anti-Bot: ENABLED"
        )

        print("🔗 Anti-Link")
        print("☢️ Anti-Nuke")
        print("🔨 Anti-Mod")
        print("💬 Anti-Spam")
        print("♻️ Duplicate Protection")
        print("🤬 Anti-Gali")
        print("🤬 Gali Member Whitelist")
        print("🧹 Clear")
        print("🎵 Music Whitelist")
        print("🤖 Bot Whitelist")
        print("📢 Say Command")
        print("🎭 Give Role")
        print("🎭 Remove Role")

        total_gali = sum(
            len(v)
            for v in self.gali_data.values()
            if isinstance(v, list)
        )

        print(
            f"🤬 Gali Words: {total_gali}"
        )

        print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        Security(bot)
    )

    print(
        "🛡️ security.py successfully loaded"
    )