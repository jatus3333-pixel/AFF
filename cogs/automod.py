import asyncio
import re
import time

from collections import defaultdict, deque
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands


class AutoMod(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # =========================================================
        # MEMORY
        # =========================================================

        self.message_history = defaultdict(
            lambda: deque(maxlen=20)
        )

        self.last_messages = {}

        self.duplicate_counts = defaultdict(int)

        # =========================================================
        # BADWORD WHITELIST
        #
        # guild_id -> set(user_ids)
        #
        # IMPORTANT:
        # This whitelist ONLY bypasses badword protection.
        # It does NOT bypass links, spam or duplicate protection.
        # =========================================================

        self.badword_whitelist = defaultdict(set)

        # =========================================================
        # MODULE SETTINGS
        # =========================================================

        self.settings = defaultdict(
            lambda: {
                "links": True,
                "spam": True,
                "duplicates": True,
                "badwords": True
            }
        )

        # =========================================================
        # LINK REGEX
        # =========================================================

        self.link_pattern = re.compile(
            r"(https?://\S+|www\.\S+|discord\.gg/\S+|discord\.com/invite/\S+)",
            re.IGNORECASE
        )

        # =========================================================
        # BADWORDS
        # =========================================================

        self.bad_words = {
            "mc",
            "bc",
            "randi",
            "maderchod",
            "chakka",
            "bhenchod",
            "bhosdika",
            "chutiye",
            "bsdk",
            "gand",
            "gand mara",
            "muh me lele",
            "teri maa chod dunga",
            "tun chakka hai",
            "bhosdike",
            "chutiya",
            "lodu",
            "bkl",
            "bhen ka loda",
            "maa ka bhosda",
            "chut",
            "bhund",
            "fudda",
            "sex",
            "radn",
            "randdd",
            "pussy",
        }

        # =========================================================
        # LIMITS
        # =========================================================

        self.max_messages = 5
        self.time_window = 5

        self.max_duplicates = 3

        self.automod_timeout_minutes = 10

        print("🛡️ HSL AutoMod initialized")

    # =============================================================
    # SERVER OWNER
    # =============================================================

    def is_server_owner(self, message):

        return (
            message.guild is not None
            and message.guild.owner_id == message.author.id
        )

    # =============================================================
    # BADWORD WHITELIST CHECK
    # =============================================================

    def is_badword_whitelisted(self, message):

        if message.guild is None:
            return False

        return (
            message.author.id
            in self.badword_whitelist[message.guild.id]
        )

    # =============================================================
    # TIMEOUT
    # =============================================================

    async def timeout_member(self, member, reason):

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
                f"[AUTOMOD] Cannot timeout {member} "
                f"- Missing permissions or role hierarchy."
            )

            return False

        except Exception as e:

            print(
                f"[AUTOMOD] Timeout error: {e}"
            )

            return False

    # =============================================================
    # SECURITY EMBED
    # =============================================================

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

    # =============================================================
    # LOAD SETTINGS
    # =============================================================

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

    # =============================================================
    # MESSAGE LISTENER
    # =============================================================

    @commands.Cog.listener()
    async def on_message(self, message):

        # ---------------------------------------------------------
        # Ignore bots and DMs
        # ---------------------------------------------------------

        if message.author.bot:
            return

        if message.guild is None:
            return

        # ---------------------------------------------------------
        # SERVER OWNER FULL BYPASS
        # ---------------------------------------------------------

        if self.is_server_owner(message):
            return

        guild_id = message.guild.id

        settings = self.settings[guild_id]

        # ---------------------------------------------------------
        # BADWORD WHITELIST
        #
        # IMPORTANT:
        # This does NOT return.
        #
        # It only tells the badword section to skip this member.
        # Link / spam / duplicate will continue working.
        # ---------------------------------------------------------

        badword_whitelisted = (
            message.author.id
            in self.badword_whitelist[guild_id]
        )

        # =========================================================
        # ANTI-LINK
        # =========================================================

        if settings["links"]:

            if self.link_pattern.search(
                message.content
            ):

                try:

                    await message.delete()

                except discord.NotFound:
                    pass

                except discord.Forbidden:

                    print(
                        "[AUTOMOD] Cannot delete link message."
                    )

                except Exception as e:

                    print(
                        f"[AUTOMOD] Link delete error: {e}"
                    )

                timed_out = await self.timeout_member(
                    message.author,
                    "HSL AutoMod: Unauthorized link"
                )

                if timed_out:

                    embed = self.security_embed(
                        "🔗 LINK BLOCKED",
                        (
                            "### 🛡️ Security Action\n\n"
                            f"👤 **Member:** "
                            f"{message.author.mention}\n\n"
                            "🔗 **Violation:** "
                            "Unauthorized link\n\n"
                            "🟢 **Action:** "
                            "10 Minute Timeout\n\n"
                            "🗑️ **Message:** Deleted"
                        ),
                        discord.Color.red()
                    )

                    embed.set_thumbnail(
                        url=message.author.display_avatar.url
                    )

                    await message.channel.send(
                        embed=embed,
                        delete_after=7
                    )

                return

        # =========================================================
        # ANTI-BADWORD
        #
        # WHITELIST ONLY APPLIES HERE
        # =========================================================

        if (
            settings["badwords"]
            and not badword_whitelisted
        ):

            content = message.content.lower().strip()

            found_word = None

            # -----------------------------------------------------
            # Check every badword
            # -----------------------------------------------------

            for word in self.bad_words:

                word = word.lower().strip()

                if not word:
                    continue

                # -------------------------------------------------
                # Multi-word phrases
                # -------------------------------------------------

                if " " in word:

                    if word in content:

                        found_word = word
                        break

                # -------------------------------------------------
                # Single words
                # -------------------------------------------------

                else:

                    pattern = (
                        r"(?<!\w)"
                        + re.escape(word)
                        + r"(?!\w)"
                    )

                    if re.search(
                        pattern,
                        content,
                        re.IGNORECASE
                    ):

                        found_word = word
                        break

            # -----------------------------------------------------
            # BADWORD FOUND
            # -----------------------------------------------------

            if found_word:

                print(
                    "[AUTOMOD] BADWORD DETECTED | "
                    f"Guild={guild_id} | "
                    f"User={message.author} | "
                    f"Word={found_word}"
                )

                # -------------------------------------------------
                # Delete
                # -------------------------------------------------

                try:

                    await message.delete()

                except discord.NotFound:
                    pass

                except discord.Forbidden:

                    print(
                        "[AUTOMOD] Missing permission "
                        "to delete badword message."
                    )

                except Exception as e:

                    print(
                        f"[AUTOMOD] Badword delete error: {e}"
                    )

                # -------------------------------------------------
                # Timeout
                # -------------------------------------------------

                timed_out = await self.timeout_member(
                    message.author,
                    "HSL AutoMod: Inappropriate language"
                )

                if timed_out:

                    embed = self.security_embed(
                        "🚨 LANGUAGE VIOLATION",
                        (
                            "### 🛡️ Security Action\n\n"
                            f"👤 **Member:** "
                            f"{message.author.mention}\n\n"
                            "⚠️ **Violation:** "
                            "Inappropriate language\n\n"
                            "🟢 **Action:** "
                            "10 Minute Timeout\n\n"
                            "🗑️ **Message:** Deleted"
                        ),
                        discord.Color.red()
                    )

                    embed.set_thumbnail(
                        url=message.author.display_avatar.url
                    )

                    await message.channel.send(
                        embed=embed,
                        delete_after=7
                    )

                else:

                    await message.channel.send(
                        (
                            f"⚠️ **AutoMod Alert:** "
                            f"{message.author.mention} ne "
                            "bad word use kiya, lekin bot ke "
                            "paas **Timeout** dene ki permission "
                            "/ role priority nahi hai!"
                        ),
                        delete_after=7
                    )

                return

        # =========================================================
        # ANTI-SPAM
        #
        # IMPORTANT:
        # BADWORD WHITELIST DOES NOT BYPASS THIS.
        # =========================================================

        if settings["spam"]:

            user_id = message.author.id

            now = time.monotonic()

            history = self.message_history[user_id]

            history.append(now)

            while (
                history
                and now - history[0]
                > self.time_window
            ):

                history.popleft()

            if len(history) >= self.max_messages:

                print(
                    "[AUTOMOD] SPAM DETECTED | "
                    f"Guild={guild_id} | "
                    f"User={message.author}"
                )

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
                        (
                            "### 🛡️ Security Action\n\n"
                            f"👤 **Member:** "
                            f"{message.author.mention}\n\n"
                            "📊 **Violation:** "
                            "Message spam\n\n"
                            "🟢 **Action:** "
                            "10 Minute Timeout"
                        ),
                        discord.Color.red()
                    )

                    embed.set_thumbnail(
                        url=message.author.display_avatar.url
                    )

                    await message.channel.send(
                        embed=embed,
                        delete_after=7
                    )

                history.clear()

                return

        # =========================================================
        # ANTI-DUPLICATE
        #
        # IMPORTANT:
        # BADWORD WHITELIST DOES NOT BYPASS THIS.
        # =========================================================

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

                self.duplicate_counts[user_id] += 1

                if (
                    self.duplicate_counts[user_id]
                    >= self.max_duplicates
                ):

                    print(
                        "[AUTOMOD] DUPLICATE DETECTED | "
                        f"Guild={guild_id} | "
                        f"User={message.author}"
                    )

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
                            (
                                "### 🛡️ Security Action\n\n"
                                f"👤 **Member:** "
                                f"{message.author.mention}\n\n"
                                "⚠️ **Violation:** "
                                "Repeated message\n\n"
                                "🟢 **Action:** "
                                "10 Minute Timeout"
                            ),
                            discord.Color.red()
                        )

                        embed.set_thumbnail(
                            url=message.author.display_avatar.url
                        )

                        await message.channel.send(
                            embed=embed,
                            delete_after=7
                        )

                    self.duplicate_counts[user_id] = 0

                    return

            else:

                self.duplicate_counts[user_id] = 0

            self.last_messages[user_id] = content

    # =============================================================
    # AUTOMOD STATUS
    # =============================================================

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
            name="🤍 Gali Whitelist",
            value=(
                f"**{len(self.badword_whitelist[interaction.guild.id])} "
                "members**"
            ),
            inline=True
        )

        embed.set_footer(
            text="HSL SECURITY • Protection System"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # =============================================================
    # WHITELIST GALI
    # =============================================================

    @app_commands.command(
        name="whitelistgali",
        description="Whitelist a member ONLY from Anti-Badword"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def whitelistgali(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):

        guild_id = interaction.guild.id

        self.badword_whitelist[guild_id].add(
            member.id
        )

        await interaction.response.send_message(
            (
                f"✅ {member.mention} ko "
                "**sirf Anti-Badword se whitelist** kar diya.\n\n"
                "🤬 Anti-Badword: **BYPASSED**\n"
                "🔗 Anti-Link: **ACTIVE**\n"
                "🚨 Anti-Spam: **ACTIVE**\n"
                "🔁 Anti-Duplicate: **ACTIVE**"
            ),
            ephemeral=True
        )

        print(
            "[AUTOMOD] Badword whitelist ADD | "
            f"Guild={guild_id} | "
            f"User={member.id}"
        )

    # =============================================================
    # UNWHITELIST GALI
    # =============================================================

    @app_commands.command(
        name="unwhitelistgali",
        description="Remove a member from Anti-Badword whitelist"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def unwhitelistgali(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):

        guild_id = interaction.guild.id

        self.badword_whitelist[guild_id].discard(
            member.id
        )

        await interaction.response.send_message(
            (
                f"✅ {member.mention} ko "
                "**Anti-Badword whitelist se remove** kar diya.\n\n"
                "🤬 Anti-Badword: **ACTIVE**"
            ),
            ephemeral=True
        )

        print(
            "[AUTOMOD] Badword whitelist REMOVE | "
            f"Guild={guild_id} | "
            f"User={member.id}"
        )

    # =============================================================
    # ERROR HANDLER
    # =============================================================

    @whitelistgali.error
    async def whitelistgali_error(
        self,
        interaction: discord.Interaction,
        error
    ):

        if isinstance(
            error,
            app_commands.errors.MissingPermissions
        ):

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    "❌ Sirf **Administrator** ye command use kar sakta hai.",
                    ephemeral=True
                )

            return

        print(
            f"[AUTOMOD] whitelistgali error: {error}"
        )

    @unwhitelistgali.error
    async def unwhitelistgali_error(
        self,
        interaction: discord.Interaction,
        error
    ):

        if isinstance(
            error,
            app_commands.errors.MissingPermissions
        ):

            if not interaction.response.is_done():

                await interaction.response.send_message(
                    "❌ Sirf **Administrator** ye command use kar sakta hai.",
                    ephemeral=True
                )

            return

        print(
            f"[AUTOMOD] unwhitelistgali error: {error}"
        )


# ================================================================
# SETUP
# ================================================================

async def setup(bot):

    await bot.add_cog(
        AutoMod(bot)
    )

    print("✅ AutoMod cog loaded")