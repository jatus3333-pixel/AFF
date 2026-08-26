import asyncio
import re
import time
from collections import defaultdict, deque
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# HSL-CORP AUTO MOD
# ============================================================

class AutoMod(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # ====================================================
        # MEMORY
        # ====================================================

        self.message_history = defaultdict(
            lambda: deque(maxlen=20)
        )

        self.last_messages = {}

        self.duplicate_counts = defaultdict(int)

        # ====================================================
        # SETTINGS
        # ====================================================

        self.settings = defaultdict(
            lambda: {
                "links": True,
                "spam": True,
                "duplicates": True,
                "badwords": True
            }
        )

        # ====================================================
        # LINK REGEX
        # ====================================================

        self.link_pattern = re.compile(
            r"(https?://\S+|www\.\S+|discord\.gg/\S+|discord\.com/invite/\S+)",
            re.IGNORECASE
        )

        # ====================================================
        # BAD WORDS
        # ====================================================

        self.bad_words = {
            "mc",
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
            "bc",
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

        # ====================================================
        # LIMITS
        # ====================================================

        self.max_messages = 5
        self.time_window = 5

        self.max_duplicates = 3

        self.automod_timeout_minutes = 10

        print("🛡️ HSL-CORP AutoMod initialized")


    # ========================================================
    # GET SECURITY COG
    # ========================================================

    def get_security_cog(self):
        """
        Security cog ko safely find karta hai.

        IMPORTANT:
        AutoMod aur Security dono alag Cogs hain.
        Gali whitelist Security cog mein stored hai.
        """

        try:
            security = self.bot.get_cog("Security")

            if security:
                return security

        except Exception as e:
            print(
                "[AUTOMOD] Security cog lookup error:",
                repr(e)
            )

        return None


    # ========================================================
    # GALI WHITELIST CHECK
    # ========================================================

    def is_gali_whitelisted(self, message):
        """
        IMPORTANT FIX:

        Agar user Security cog ke
        /whitelistgali @user
        se whitelisted hai,

        toh ONLY badword filter bypass hoga.

        Anti-Link
        Anti-Spam
        Anti-Duplicate

        normally work karenge.
        """

        if not message.guild:
            return False

        security = self.get_security_cog()

        if security is None:
            return False

        try:
            return security.gali_whitelisted(
                message.guild.id,
                message.author.id
            )

        except Exception as e:

            print(
                "[AUTOMOD] Gali whitelist check error:",
                repr(e)
            )

            return False


    # ========================================================
    # SECURITY OWNER CHECK
    # ========================================================

    def is_security_owner(self, message):
        """
        Same owner logic as Security cog.

        Ye sirf compatibility ke liye hai.
        Gali whitelist ka actual check
        Security.gali_whitelisted() se hota hai.
        """

        if not message.guild:
            return False

        # Server owner
        if message.guild.owner_id == message.author.id:
            return True

        security = self.get_security_cog()

        if security:

            try:

                if security.has_owner_role(
                    message.author
                ):
                    return True

            except Exception:
                pass

            try:

                # Bot owner IDs handled by Security
                if message.author.id in security.BOT_OWNER_IDS:
                    return True

            except Exception:
                pass

            try:

                # Security cog's bot owner check
                result = security.is_bot_owner(
                    message.author
                )

                if asyncio.iscoroutine(result):
                    # Cannot await here because this function is sync.
                    # Actual async owner check happens separately.
                    pass

            except Exception:
                pass

        return False


    # ========================================================
    # ASYNC OWNER BYPASS
    # ========================================================

    async def is_owner_or_manager(self, message):

        if not message.guild:
            return False

        # Server owner
        if message.guild.owner_id == message.author.id:
            return True

        security = self.get_security_cog()

        if security:

            try:

                if await security.is_bot_owner(
                    message.author
                ):
                    return True

            except Exception:
                pass

            try:

                if security.has_owner_role(
                    message.author
                ):
                    return True

            except Exception:
                pass

        return False


    # ========================================================
    # TIMEOUT
    # ========================================================

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
                f"[AUTOMOD] ❌ Cannot timeout "
                f"{member} - permission/role hierarchy."
            )

            return False

        except discord.HTTPException as e:

            print(
                "[AUTOMOD] Timeout HTTP error:",
                repr(e)
            )

            return False

        except Exception as e:

            print(
                "[AUTOMOD] Timeout error:",
                repr(e)
            )

            return False


    # ========================================================
    # SECURITY EMBED
    # ========================================================

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


    # ========================================================
    # LOAD SETTINGS
    # ========================================================

    @commands.Cog.listener()
    async def on_ready(self):

        for guild in self.bot.guilds:

            try:

                row = None

                if hasattr(
                    self.bot,
                    "db"
                ):

                    try:
                        row = self.bot.db.get_guild(
                            guild.id
                        )
                    except Exception:
                        row = None

                if row:

                    self.settings[
                        guild.id
                    ]["links"] = bool(
                        row.get(
                            "automod_links",
                            True
                        )
                    )

                    self.settings[
                        guild.id
                    ]["spam"] = bool(
                        row.get(
                            "automod_spam",
                            True
                        )
                    )

                    self.settings[
                        guild.id
                    ]["duplicates"] = bool(
                        row.get(
                            "automod_duplicates",
                            True
                        )
                    )

                    self.settings[
                        guild.id
                    ]["badwords"] = bool(
                        row.get(
                            "automod_badwords",
                            True
                        )
                    )

            except Exception as e:

                print(
                    f"[AUTOMOD] Database load error: {e}"
                )

        print(
            "💾 AutoMod settings loaded"
        )


    # ========================================================
    # BADWORD DETECTION
    # ========================================================

    def find_badword(
        self,
        content
    ):

        if not content:
            return None

        content = content.lower()

        for word in self.bad_words:

            word = word.strip().lower()

            if not word:
                continue

            # ----------------------------------------------
            # PHRASE
            # ----------------------------------------------

            if " " in word:

                if word in content:
                    return word

                continue

            # ----------------------------------------------
            # SINGLE WORD
            # ----------------------------------------------

            pattern = (
                r"(?<!\w)"
                +
                re.escape(word)
                +
                r"(?!\w)"
            )

            try:

                if re.search(
                    pattern,
                    content,
                    flags=re.IGNORECASE
                ):

                    return word

            except Exception:

                if word in content:
                    return word

        return None


    # ========================================================
    # MESSAGE SECURITY
    # ========================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message
    ):

        # ====================================================
        # IGNORE BOT
        # ====================================================

        if message.author.bot:
            return

        # ====================================================
        # IGNORE DM
        # ====================================================

        if message.guild is None:
            return

        settings = self.settings[
            message.guild.id
        ]

        content = (
            message.content or ""
        ).strip()

        lower_content = content.lower()


        # ====================================================
        # OWNER BYPASS
        # ====================================================
        #
        # IMPORTANT:
        # Owner bypass only applies to the normal
        # AutoMod owner behavior.
        #
        # Gali whitelist is checked separately.
        #

        if await self.is_owner_or_manager(
            message
        ):

            return


        # ====================================================
        # ANTI-LINK
        # ====================================================

        if settings.get(
            "links",
            True
        ):

            if self.link_pattern.search(
                content
            ):

                # ------------------------------------------
                # DELETE
                # ------------------------------------------

                try:

                    await message.delete()

                except discord.Forbidden:

                    print(
                        "[AUTOMOD] ❌ Cannot delete link."
                    )

                except Exception as e:

                    print(
                        "[AUTOMOD] Link delete error:",
                        repr(e)
                    )

                # ------------------------------------------
                # TIMEOUT
                # ------------------------------------------

                timed_out = await self.timeout_member(
                    message.author,
                    "HSL AutoMod: Unauthorized link"
                )

                # ------------------------------------------
                # WARNING
                # ------------------------------------------

                if timed_out:

                    try:

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

                    except Exception as e:

                        print(
                            "[AUTOMOD] Link warning error:",
                            repr(e)
                        )

                return


        # ====================================================
        # ANTI-BADWORD
        # ====================================================

        if settings.get(
            "badwords",
            True
        ):

            # =================================================
            # ⭐ CRITICAL FIX ⭐
            #
            # Check Security cog whitelist BEFORE
            # scanning bad words.
            #
            # /whitelistgali @User
            #
            # means this user's bad words are allowed.
            #
            # NOTHING ELSE IS BYPASSED.
            # =================================================

            gali_whitelisted = (
                self.is_gali_whitelisted(
                    message
                )
            )

            if gali_whitelisted:

                print(
                    "[AUTOMOD] ✅ GALI WHITELIST BYPASS:",
                    f"{message.author} ({message.author.id})"
                )

                # IMPORTANT:
                # Do NOT return from on_message.
                #
                # We only skip BADWORD detection.
                #
                # Anti-Spam and Anti-Duplicate
                # continue below.

            else:

                found_word = self.find_badword(
                    content
                )

                if found_word:

                    print(
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    )

                    print(
                        "[AUTOMOD] 🚨 BADWORD DETECTED"
                    )

                    print(
                        f"[AUTOMOD] User: "
                        f"{message.author} "
                        f"({message.author.id})"
                    )

                    print(
                        f"[AUTOMOD] Word: "
                        f"{found_word}"
                    )

                    # --------------------------------------
                    # DELETE MESSAGE
                    # --------------------------------------

                    try:

                        await message.delete()

                    except discord.Forbidden:

                        print(
                            "[AUTOMOD] ❌ Cannot delete badword message."
                        )

                    except Exception as e:

                        print(
                            "[AUTOMOD] Delete error:",
                            repr(e)
                        )

                    # --------------------------------------
                    # TIMEOUT
                    # --------------------------------------

                    timed_out = await self.timeout_member(
                        message.author,
                        "HSL AutoMod: Inappropriate language"
                    )

                    # --------------------------------------
                    # WARNING
                    # --------------------------------------

                    if timed_out:

                        try:

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

                        except Exception as e:

                            print(
                                "[AUTOMOD] Badword warning error:",
                                repr(e)
                            )

                    else:

                        try:

                            await message.channel.send(

                                (
                                    "⚠️ **AutoMod Alert:** "
                                    f"{message.author.mention} "
                                    "ne bad word use kiya, "
                                    "lekin bot ke paas "
                                    "**Timeout** dene ki permission / "
                                    "role priority nahi hai!"
                                ),

                                delete_after=7
                            )

                        except Exception:
                            pass

                    print(
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    )

                    return


        # ====================================================
        # ANTI-SPAM
        # ====================================================

        if settings.get(
            "spam",
            True
        ):

            user_id = message.author.id

            now = time.monotonic()

            history = self.message_history[
                user_id
            ]

            history.append(
                now
            )

            while (
                history
                and
                now - history[0] > self.time_window
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

                    try:

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

                    except Exception:
                        pass

                history.clear()

                return


        # ====================================================
        # ANTI-DUPLICATE
        # ====================================================

        if settings.get(
            "duplicates",
            True
        ):

            user_id = message.author.id

            normalized_content = (
                message.content
                .strip()
                .lower()
            )

            if (
                normalized_content
                and
                self.last_messages.get(
                    user_id
                ) == normalized_content
            ):

                self.duplicate_counts[
                    user_id
                ] += 1

                if (
                    self.duplicate_counts[
                        user_id
                    ]
                    >=
                    self.max_duplicates
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

                        try:

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
            ] = normalized_content


    # ========================================================
    # AUTOMOD STATUS
    # ========================================================

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

        if not interaction.guild:

            return await interaction.response.send_message(
                "❌ Server only command.",
                ephemeral=True
            )

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

        # Check Security whitelist count

        whitelist_count = 0

        security = self.get_security_cog()

        if security:

            try:

                security_settings = (
                    security.get_settings(
                        interaction.guild.id
                    )
                )

                whitelist_count = len(
                    security_settings.get(
                        "whitelist_gali",
                        []
                    )
                )

            except Exception:
                whitelist_count = 0

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
            value=status(
                settings["links"]
            ),
            inline=True
        )

        embed.add_field(
            name="🚨 Anti-Spam",
            value=status(
                settings["spam"]
            ),
            inline=True
        )

        embed.add_field(
            name="🔁 Anti-Duplicate",
            value=status(
                settings["duplicates"]
            ),
            inline=True
        )

        embed.add_field(
            name="🤬 Anti-Badword",
            value=status(
                settings["badwords"]
            ),
            inline=True
        )

        embed.add_field(
            name="🤬 Gali Whitelist",
            value=f"🟢 **{whitelist_count} MEMBERS**",
            inline=True
        )

        embed.add_field(
            name="🔇 Auto Timeout",
            value="🟢 **10 MINUTES**",
            inline=True
        )

        embed.set_footer(
            text="HSL SECURITY • Protection System"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


    # ========================================================
    # COMMAND ERROR
    # ========================================================

    @automod_status.error
    async def automod_status_error(
        self,
        interaction,
        error
    ):

        if isinstance(
            error,
            app_commands.errors.MissingPermissions
        ):

            if interaction.response.is_done():

                await interaction.followup.send(
                    "❌ Administrator permission required.",
                    ephemeral=True
                )

            else:

                await interaction.response.send_message(
                    "❌ Administrator permission required.",
                    ephemeral=True
                )

            return

        print(
            "[AUTOMOD] STATUS ERROR:",
            repr(error)
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        AutoMod(bot)
    )

    print(
        "🛡️ automod.py successfully loaded"
    )