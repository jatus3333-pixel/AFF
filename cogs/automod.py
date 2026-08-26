import re
import time
import json
import os
from collections import defaultdict, deque
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands


# =========================================================
# FILE
# =========================================================

WHITELIST_FILE = "gali_whitelist.json"


# =========================================================
# AUTOMOD
# =========================================================

class AutoMod(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # -------------------------------------------------
        # MEMORY
        # -------------------------------------------------

        self.message_history = defaultdict(
            lambda: deque(maxlen=20)
        )

        self.last_messages = {}

        self.duplicate_counts = defaultdict(int)

        # -------------------------------------------------
        # SETTINGS
        # -------------------------------------------------

        self.settings = defaultdict(
            lambda: {
                "links": True,
                "spam": True,
                "duplicates": True,
                "badwords": True
            }
        )

        # -------------------------------------------------
        # GALI WHITELIST
        #
        # {
        #   "guild_id": [user_id, user_id]
        # }
        # -------------------------------------------------

        self.gali_whitelist = {}

        self.load_gali_whitelist()

        # -------------------------------------------------
        # LINK REGEX
        # -------------------------------------------------

        self.link_pattern = re.compile(
            r"(https?://\S+|www\.\S+|discord\.gg/\S+|discord\.com/invite/\S+)",
            re.IGNORECASE
        )

        # -------------------------------------------------
        # BAD WORDS
        # -------------------------------------------------

        self.bad_words = {
            "mc",
            "bc",
            "bkl",
            "bsdk",
            "randi",
            "maderchod",
            "madarchod",
            "chakka",
            "bhenchod",
            "bhenchod",
            "bhosdika",
            "bhosdike",
            "chutiye",
            "chutiya",
            "gand",
            "gand mara",
            "muh me lele",
            "teri maa chod dunga",
            "tun chakka hai",
            "lodu",
            "bhen ka loda",
            "maa ka bhosda",
            "chut",
            "bhund",
            "fudda",
            "sex",
            "radn",
            "randdd",
            "pussy"
        }

        # -------------------------------------------------
        # LIMITS
        # -------------------------------------------------

        self.max_messages = 5
        self.time_window = 5

        self.max_duplicates = 3

        self.automod_timeout_minutes = 10

    # =====================================================
    # WHITELIST FILE
    # =====================================================

    def load_gali_whitelist(self):

        try:

            if not os.path.exists(WHITELIST_FILE):
                self.gali_whitelist = {}
                return

            with open(
                WHITELIST_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            self.gali_whitelist = {
                str(guild_id): [
                    int(user_id)
                    for user_id in users
                ]
                for guild_id, users in data.items()
            }

            print(
                f"[AUTOMOD] Loaded gali whitelist: "
                f"{len(self.gali_whitelist)} servers"
            )

        except Exception as e:

            print(
                f"[AUTOMOD] Whitelist load error: {e}"
            )

            self.gali_whitelist = {}

    # =====================================================

    def save_gali_whitelist(self):

        try:

            with open(
                WHITELIST_FILE,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    self.gali_whitelist,
                    f,
                    indent=4
                )

        except Exception as e:

            print(
                f"[AUTOMOD] Whitelist save error: {e}"
            )

    # =====================================================

    def is_gali_whitelisted(
        self,
        guild_id: int,
        user_id: int
    ):

        guild_users = self.gali_whitelist.get(
            str(guild_id),
            []
        )

        return user_id in guild_users

    # =====================================================

    def add_gali_whitelist(
        self,
        guild_id: int,
        user_id: int
    ):

        guild_id = str(guild_id)

        if guild_id not in self.gali_whitelist:
            self.gali_whitelist[guild_id] = []

        if user_id not in self.gali_whitelist[guild_id]:

            self.gali_whitelist[guild_id].append(
                user_id
            )

            self.save_gali_whitelist()

            return True

        return False

    # =====================================================

    def remove_gali_whitelist(
        self,
        guild_id: int,
        user_id: int
    ):

        guild_id = str(guild_id)

        if guild_id not in self.gali_whitelist:
            return False

        if user_id not in self.gali_whitelist[guild_id]:
            return False

        self.gali_whitelist[guild_id].remove(
            user_id
        )

        if not self.gali_whitelist[guild_id]:
            del self.gali_whitelist[guild_id]

        self.save_gali_whitelist()

        return True

    # =====================================================
    # SERVER OWNER
    # =====================================================

    def is_server_owner(
        self,
        message: discord.Message
    ):

        return (
            message.guild is not None
            and message.guild.owner_id == message.author.id
        )

    # =====================================================
    # TIMEOUT
    # =====================================================

    async def timeout_member(
        self,
        member,
        reason
    ):

        try:

            await member.timeout(
                timedelta(
                    minutes=self.automod_timeout_minutes
                ),
                reason=reason
            )

            return True

        except discord.Forbidden:

            print(
                f"[AUTOMOD] Cannot timeout "
                f"{member} - permissions/role hierarchy."
            )

            return False

        except Exception as e:

            print(
                f"[AUTOMOD] Timeout error: {e}"
            )

            return False

    # =====================================================
    # EMBED
    # =====================================================

    def security_embed(
        self,
        title,
        description,
        color
    ):

        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )

        embed.set_footer(
            text="HSL SECURITY • AutoMod Protection"
        )

        return embed

    # =====================================================
    # READY
    # =====================================================

    @commands.Cog.listener()
    async def on_ready(self):

        for guild in self.bot.guilds:

            try:

                row = (
                    self.bot.db.get_guild(guild.id)
                    if hasattr(self.bot, "db")
                    else None
                )

                if row:

                    self.settings[guild.id]["links"] = bool(
                        row.get(
                            "automod_links",
                            True
                        )
                    )

                    self.settings[guild.id]["spam"] = bool(
                        row.get(
                            "automod_spam",
                            True
                        )
                    )

                    self.settings[guild.id]["duplicates"] = bool(
                        row.get(
                            "automod_duplicates",
                            True
                        )
                    )

                    self.settings[guild.id]["badwords"] = bool(
                        row.get(
                            "automod_badwords",
                            True
                        )
                    )

            except Exception as e:

                print(
                    f"[AUTOMOD] Database load error: {e}"
                )

        print("💾 AutoMod settings loaded")
        print("🛡️ Gali whitelist system loaded")

    # =====================================================
    # MESSAGE LISTENER
    # =====================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message
    ):

        # -------------------------------------------------
        # IGNORE BOT / DM
        # -------------------------------------------------

        if message.author.bot:
            return

        if message.guild is None:
            return

        # -------------------------------------------------
        # SERVER OWNER BYPASS
        #
        # Owner gets complete automod bypass.
        # -------------------------------------------------

        if self.is_server_owner(message):
            return

        settings = self.settings[
            message.guild.id
        ]

        # =================================================
        # ANTI LINK
        # =================================================

        if (
            settings["links"]
            and self.link_pattern.search(
                message.content
            )
        ):

            try:
                await message.delete()
            except Exception:
                pass

            timed_out = await self.timeout_member(
                message.author,
                "HSL AutoMod: Unauthorized link"
            )

            if timed_out:

                embed = self.security_embed(
                    "🔗 LINK BLOCKED",

                    f"""
### 🛡️ Security Action

👤 **Member:** {message.author.mention}

🔗 **Violation:** Unauthorized link

🟢 **Action:** 10 Minute Timeout

🗑️ **Message:** Deleted
""",

                    discord.Color.red()
                )

                embed.set_thumbnail(
                    url=message.author.display_avatar.url
                )

                try:

                    await message.channel.send(
                        embed=embed,
                        delete_after=7
                    )

                except Exception:
                    pass

            return

        # =================================================
        # ANTI BADWORD
        # =================================================

        if settings["badwords"]:

            # ------------------------------------------------
            # IMPORTANT:
            # Whitelist ONLY affects badwords.
            #
            # It does NOT bypass:
            # - links
            # - spam
            # - duplicates
            # ------------------------------------------------

            if self.is_gali_whitelisted(
                message.guild.id,
                message.author.id
            ):

                # Whitelisted member's message is allowed
                # to contain bad words.
                #
                # Continue so other protections still work.
                pass

            else:

                content = message.content.lower()

                found_word = None

                for word in self.bad_words:

                    pattern = (
                        r"(?<!\w)"
                        + re.escape(word.lower())
                        + r"(?!\w)"
                    )

                    if re.search(
                        pattern,
                        content,
                        re.IGNORECASE
                    ):

                        found_word = word
                        break

                # --------------------------------------------
                # BADWORD FOUND
                # --------------------------------------------

                if found_word is not None:

                    try:
                        await message.delete()
                    except Exception:
                        pass

                    timed_out = await self.timeout_member(
                        message.author,
                        "HSL AutoMod: Inappropriate language"
                    )

                    if timed_out:

                        embed = self.security_embed(
                            "🚨 LANGUAGE VIOLATION",

                            f"""
### 🛡️ Security Action

👤 **Member:** {message.author.mention}

⚠️ **Violation:** Inappropriate language

🟢 **Action:** 10 Minute Timeout

🗑️ **Message:** Deleted
""",

                            discord.Color.red()
                        )

                        embed.set_thumbnail(
                            url=message.author.display_avatar.url
                        )

                        try:

                            await message.channel.send(
                                embed=embed,
                                delete_after=7
                            )

                        except Exception:
                            pass

                    else:

                        try:

                            await message.channel.send(
                                f"⚠️ **AutoMod Alert:** "
                                f"{message.author.mention} ne bad word use kiya, "
                                f"lekin bot ke paas **Timeout** dene ki permission "
                                f"/ role priority nahi hai!",
                                delete_after=7
                            )

                        except Exception:
                            pass

                    return

        # =================================================
        # ANTI SPAM
        # =================================================

        if settings["spam"]:

            user_id = message.author.id

            now = time.monotonic()

            history = self.message_history[
                user_id
            ]

            history.append(now)

            while (
                history
                and now - history[0]
                > self.time_window
            ):

                history.popleft()

            if len(history) >= self.max_messages:

                try:
                    await message.delete()
                except Exception:
                    pass

                timed_out = await self.timeout_member(
                    message.author,
                    "HSL AutoMod: Spamming"
                )

                if timed_out:

                    embed = self.security_embed(
                        "🚨 SPAM DETECTED",

                        f"""
### 🛡️ Security Action

👤 **Member:** {message.author.mention}

📊 **Violation:** Message spam

🟢 **Action:** 10 Minute Timeout
""",

                        discord.Color.red()
                    )

                    embed.set_thumbnail(
                        url=message.author.display_avatar.url
                    )

                    try:

                        await message.channel.send(
                            embed=embed,
                            delete_after=7
                        )

                    except Exception:
                        pass

                history.clear()

                return

        # =================================================
        # ANTI DUPLICATE
        # =================================================

        if settings["duplicates"]:

            user_id = message.author.id

            content = (
                message.content
                .strip()
                .lower()
            )

            if (
                content
                and self.last_messages.get(user_id)
                == content
            ):

                self.duplicate_counts[
                    user_id
                ] += 1

                if (
                    self.duplicate_counts[user_id]
                    >= self.max_duplicates
                ):

                    try:
                        await message.delete()
                    except Exception:
                        pass

                    timed_out = await self.timeout_member(
                        message.author,
                        "HSL AutoMod: Repeated messages"
                    )

                    if timed_out:

                        embed = self.security_embed(
                            "🔁 REPEATED MESSAGE",

                            f"""
### 🛡️ Security Action

👤 **Member:** {message.author.mention}

⚠️ **Violation:** Repeated message

🟢 **Action:** 10 Minute Timeout
""",

                            discord.Color.red()
                        )

                        embed.set_thumbnail(
                            url=message.author.display_avatar.url
                        )

                        try:

                            await message.channel.send(
                                embed=embed,
                                delete_after=7
                            )

                        except Exception:
                            pass

                    self.duplicate_counts[
                        user_id
                    ] = 0

                    return

            else:

                self.duplicate_counts[
                    user_id
                ] = 0

            self.last_messages[
                user_id
            ] = content

    # =====================================================
    # WHITELIST GALI
    # =====================================================

    @app_commands.command(
        name="whitelistgali",
        description="Allow a member to use bad words without AutoMod punishment"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    @app_commands.describe(
        member="Member who should be allowed to use bad words"
    )
    async def whitelistgali(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):

        added = self.add_gali_whitelist(
            interaction.guild.id,
            member.id
        )

        if added:

            await interaction.response.send_message(
                f"✅ {member.mention} ko **Gali Whitelist** kar diya.\n\n"
                f"Ab Anti-Badword uski gali delete nahi karega.\n"
                f"⚠️ Anti-Link, Anti-Spam aur Anti-Duplicate ab bhi active rahenge.",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                f"ℹ️ {member.mention} already **Gali Whitelist** me hai.",
                ephemeral=True
            )

    # =====================================================
    # UNWHITELIST GALI
    # =====================================================

    @app_commands.command(
        name="unwhitelistgali",
        description="Remove a member from the badword whitelist"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    @app_commands.describe(
        member="Member to remove from Gali Whitelist"
    )
    async def unwhitelistgali(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):

        removed = self.remove_gali_whitelist(
            interaction.guild.id,
            member.id
        )

        if removed:

            await interaction.response.send_message(
                f"✅ {member.mention} ko **Gali Whitelist** se remove kar diya.\n\n"
                f"Ab uski bad words AutoMod detect karega.",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                f"ℹ️ {member.mention} Gali Whitelist me tha hi nahi.",
                ephemeral=True
            )

    # =====================================================
    # LIST GALI WHITELIST
    # =====================================================

    @app_commands.command(
        name="galiwhitelist",
        description="Show members who are allowed to use bad words"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def galiwhitelist(
        self,
        interaction: discord.Interaction
    ):

        users = self.gali_whitelist.get(
            str(interaction.guild.id),
            []
        )

        if not users:

            await interaction.response.send_message(
                "📋 **Gali Whitelist empty hai.**",
                ephemeral=True
            )

            return

        mentions = []

        for user_id in users:

            member = interaction.guild.get_member(
                user_id
            )

            if member:

                mentions.append(
                    f"• {member.mention} (`{member.id}`)"
                )

            else:

                mentions.append(
                    f"• <@{user_id}> (`{user_id}`)"
                )

        embed = discord.Embed(
            title="🤬 GALI WHITELIST",
            description="\n".join(mentions),
            color=discord.Color.green()
        )

        embed.set_footer(
            text="HSL SECURITY • AutoMod"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # =====================================================
    # AUTOMOD STATUS
    # =====================================================

    @app_commands.command(
        name="automod_status",
        description="Show AutoMod security status"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def automod_status(
        self,
        interaction: discord.Interaction
    ):

        settings = self.settings[
            interaction.guild.id
        ]

        def status(value):

            return (
                "🟢 **ONLINE**"
                if value
                else
                "🔴 **OFFLINE**"
            )

        whitelist_count = len(
            self.gali_whitelist.get(
                str(interaction.guild.id),
                []
            )
        )

        embed = discord.Embed(
            title="🛡️ HSL SECURITY",
            description=(
                "### SECURITY STATUS\n\n"
                "━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="🔗 Anti-Link",
            value=status(settings["links"]),
            inline=True
        )

        embed.add_field(
            name="🚨 Anti-Spam",
            value=status(settings["spam"]),
            inline=True
        )

        embed.add_field(
            name="🔁 Anti-Duplicate",
            value=status(settings["duplicates"]),
            inline=True
        )

        embed.add_field(
            name="🤬 Anti-Badword",
            value=status(settings["badwords"]),
            inline=True
        )

        embed.add_field(
            name="🔇 Auto Timeout",
            value="🟢 **10 MINUTES**",
            inline=True
        )

        embed.add_field(
            name="🤬 Gali Whitelist",
            value=f"🟢 **{whitelist_count} MEMBER(S)**",
            inline=True
        )

        embed.set_footer(
            text="HSL SECURITY • Protection System"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# =========================================================
# SETUP
# =========================================================

async def setup(bot):

    await bot.add_cog(
        AutoMod(bot)
    )