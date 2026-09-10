import asyncio
import discord
from discord.ext import commands


# ============================================================
# AFF-ARMY PROFESSIONAL TICKET SYSTEM
# ============================================================

TICKET_CATEGORY_NAME = "🎫 TICKETS"
STAFF_ROLE_NAME = "🎫 Ticket Staff"


# ============================================================
# HELPERS
# ============================================================

async def get_ticket_category(guild: discord.Guild):

    category = discord.utils.get(
        guild.categories,
        name=TICKET_CATEGORY_NAME
    )

    if category is None:

        category = await guild.create_category(
            TICKET_CATEGORY_NAME,
            reason="AFF-ARMY Ticket System"
        )

    return category


async def get_staff_role(guild: discord.Guild):

    role = discord.utils.get(
        guild.roles,
        name=STAFF_ROLE_NAME
    )

    if role is None:

        role = await guild.create_role(
            name=STAFF_ROLE_NAME,
            reason="AFF-ARMY Ticket Staff Role"
        )

    return role


def is_staff(member: discord.Member):

    if member.guild_permissions.administrator:
        return True

    if member.guild_permissions.manage_channels:
        return True

    if member.guild_permissions.manage_messages:
        return True

    return any(
        role.name == STAFF_ROLE_NAME
        for role in member.roles
    )


# ============================================================
# FF STATS SCREENSHOT UPLOAD VIEW
# ============================================================

class FFStatsScreenshotView(discord.ui.View):

    def __init__(self, bot):

        super().__init__(
            timeout=None
        )

        self.bot = bot

    # ========================================================
    # UPLOAD SCREENSHOT BUTTON
    # ========================================================

    @discord.ui.button(
        label="Upload Screenshot / Proof",
        emoji="📸",
        style=discord.ButtonStyle.primary,
        custom_id="hsl_ff_stats_screenshot"
    )
    async def upload_screenshot(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        channel = interaction.channel

        # ----------------------------------------------------
        # MAKE SURE THIS IS A TEXT CHANNEL
        # ----------------------------------------------------

        if not isinstance(channel, discord.TextChannel):

            await interaction.response.send_message(
                "❌ Screenshot upload is not available here.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # GET TICKET TOPIC
        # ----------------------------------------------------

        topic = channel.topic or ""

        owner_id = None

        if "Ticket Owner ID:" in topic:

            try:

                owner_id = int(
                    topic.split("Ticket Owner ID:")[1]
                    .split("|")[0]
                    .strip()
                )

            except Exception:

                owner_id = None

        # ----------------------------------------------------
        # ONLY TICKET OWNER
        # ----------------------------------------------------

        if owner_id != interaction.user.id:

            await interaction.response.send_message(
                "❌ Only the **ticket owner** can upload "
                "the Free Fire screenshot.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # CHECK BOT PERMISSIONS
        # ----------------------------------------------------

        bot_member = guild_me = interaction.guild.me

        if bot_member is not None:

            permissions = channel.permissions_for(bot_member)

            if not permissions.manage_messages:

                await interaction.response.send_message(
                    "❌ I cannot automatically delete your "
                    "screenshot because I don't have "
                    "**Manage Messages** permission in this ticket.",
                    ephemeral=True
                )

                return

            if not permissions.attach_files:

                await interaction.response.send_message(
                    "❌ I don't have **Attach Files** permission "
                    "in this ticket.",
                    ephemeral=True
                )

                return

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        await interaction.response.send_message(
            "📸 **SCREENSHOT UPLOAD READY**\n\n"
            "Please send your **Free Fire profile/stats "
            "screenshot** in this ticket now.\n\n"
            "✅ Supported formats: PNG, JPG, JPEG, WEBP\n"
            "⏱️ Upload window: **5 minutes**\n\n"
            "⚠️ Send the screenshot as an **attachment**.",
            ephemeral=True
        )

        # ----------------------------------------------------
        # WAIT FOR IMAGE
        # ----------------------------------------------------

        def check(message: discord.Message):

            # Same channel
            if message.channel.id != channel.id:
                return False

            # Same user
            if message.author.id != interaction.user.id:
                return False

            # Must contain attachment
            if not message.attachments:
                return False

            # Check supported image extension
            for attachment in message.attachments:

                filename = attachment.filename.lower()

                if filename.endswith(
                    (
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".webp"
                    )
                ):

                    return True

            return False

        # ----------------------------------------------------
        # WAIT
        # ----------------------------------------------------

        try:

            message = await self.bot.wait_for(
                "message",
                check=check,
                timeout=300
            )

        except asyncio.TimeoutError:

            await channel.send(
                f"⏱️ {interaction.user.mention}, "
                "the **screenshot upload window expired**.\n\n"
                "Click **📸 Upload Screenshot / Proof** "
                "again if you still need to upload it."
            )

            return

        # ----------------------------------------------------
        # FIND IMAGE
        # ----------------------------------------------------

        image_attachment = None

        for attachment in message.attachments:

            filename = attachment.filename.lower()

            if filename.endswith(
                (
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".webp"
                )
            ):

                image_attachment = attachment
                break

        if image_attachment is None:

            return

        # ====================================================
        # DOWNLOAD ORIGINAL IMAGE FIRST
        # ====================================================
        # IMPORTANT:
        # We do NOT rely on the user's Discord CDN URL.
        #
        # Bot downloads the attachment and uploads it again
        # in its own message.
        #
        # Then the original user message is deleted.
        # ====================================================

        image_filename = image_attachment.filename
        image_size = image_attachment.size

        try:

            bot_file = await image_attachment.to_file(
                filename=image_filename
            )

        except discord.HTTPException as e:

            print(
                f"[FF SCREENSHOT DOWNLOAD ERROR] {e}",
                flush=True
            )

            await channel.send(
                "❌ I received your screenshot, but I could "
                "not process the image. Please try again."
            )

            return

        except Exception as e:

            print(
                f"[FF SCREENSHOT FILE ERROR] {e}",
                flush=True
            )

            await channel.send(
                "❌ An error occurred while processing your "
                "screenshot. Please try again."
            )

            return

        # ====================================================
        # SCREENSHOT RECEIVED EMBED
        # ====================================================

        embed = discord.Embed(

            title="📸 SCREENSHOT RECEIVED",

            description=(
                f"✅ Screenshot successfully received from "
                f"{interaction.user.mention}\n\n"
                "🟢 **Status:** `RECEIVED`\n"
                "🛡️ **Staff can now review the screenshot.**"
            ),

            color=discord.Color.green()
        )

        embed.add_field(
            name="📁 FILE",
            value=f"`{image_filename}`",
            inline=True
        )

        embed.add_field(
            name="📦 SIZE",
            value=f"`{image_size / 1024:.1f} KB`",
            inline=True
        )

        # ----------------------------------------------------
        # SHOW IMAGE FROM BOT'S OWN ATTACHMENT
        # ----------------------------------------------------

        embed.set_image(
            url=f"attachment://{image_filename}"
        )

        embed.set_footer(
            text="AFF-ARMY • FF Player Profile Support"
        )

        # ====================================================
        # SEND BOT MESSAGE FIRST
        # ====================================================
        # This guarantees the screenshot is safely stored in
        # the bot's message before deleting the user's message.
        # ====================================================

        try:

            await channel.send(
                embed=embed,
                file=bot_file
            )

        except discord.Forbidden:

            await channel.send(
                "❌ I received the screenshot but Discord "
                "did not allow me to upload it.\n\n"
                "Please check the bot's **Attach Files** "
                "permission."
            )

            return

        except discord.HTTPException as e:

            print(
                f"[FF SCREENSHOT SEND ERROR] {e}",
                flush=True
            )

            await channel.send(
                "❌ I could not display the screenshot. "
                "Please try uploading it again."
            )

            return

        except Exception as e:

            print(
                f"[FF SCREENSHOT SEND ERROR] {e}",
                flush=True
            )

            return

        # ====================================================
        # DELETE USER'S ORIGINAL SCREENSHOT MESSAGE
        # ====================================================

        try:

            await message.delete(
                reason="AFF-ARMY screenshot upload processed"
            )

            print(
                f"[FF SCREENSHOT] Original screenshot "
                f"message deleted successfully | "
                f"User: {message.author} | "
                f"Channel: #{channel.name}",
                flush=True
            )

        except discord.Forbidden:

            print(
                "[FF SCREENSHOT] DELETE FAILED: "
                "Bot does not have Manage Messages permission.",
                flush=True
            )

            await channel.send(
                "⚠️ Screenshot was received successfully, "
                "but I could not delete the original upload.\n\n"
                "Please make sure the bot has "
                "**Manage Messages** permission."
            )

        except discord.NotFound:

            print(
                "[FF SCREENSHOT] Original message was already deleted.",
                flush=True
            )

        except discord.HTTPException as e:

            print(
                f"[FF SCREENSHOT DELETE HTTP ERROR] {e}",
                flush=True
            )

        except Exception as e:

            print(
                f"[FF SCREENSHOT DELETE ERROR] {e}",
                flush=True
            )


# ============================================================
# CREATE TICKET CHANNEL
# ============================================================

async def create_ticket_channel(
    interaction: discord.Interaction,
    ticket_type: str,
    ticket_title: str,
    ticket_description: str,
    ticket_fields=None
):

    guild = interaction.guild
    user = interaction.user

    # --------------------------------------------------------
    # EXISTING TICKET CHECK
    # --------------------------------------------------------

    for channel in guild.text_channels:

        if (
            channel.topic
            and f"Ticket Owner ID: {user.id}" in channel.topic
        ):

            await interaction.response.send_message(
                "❌ You already have an open ticket.\n"
                f"🎫 {channel.mention}",
                ephemeral=True
            )

            return

    # --------------------------------------------------------
    # CATEGORY + STAFF ROLE
    # --------------------------------------------------------

    category = await get_ticket_category(guild)
    staff_role = await get_staff_role(guild)

    # --------------------------------------------------------
    # PERMISSIONS
    # --------------------------------------------------------

    overwrites = {

        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        user:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            ),

        staff_role:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
                manage_messages=True
            ),

        guild.me:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
                manage_channels=True,
                manage_messages=True
            )
    }

    # --------------------------------------------------------
    # CHANNEL NAME
    # --------------------------------------------------------

    clean_name = ticket_type.lower()

    clean_name = clean_name.replace(
        " ",
        "-"
    )

    clean_name = clean_name.replace(
        "/",
        "-"
    )

    channel_name = f"{clean_name}-{user.id}"

    channel_name = channel_name[:95]

    # --------------------------------------------------------
    # CREATE CHANNEL
    # --------------------------------------------------------

    channel = await guild.create_text_channel(

        name=channel_name,

        category=category,

        overwrites=overwrites,

        topic=(
            f"Ticket Owner ID: {user.id} | "
            f"Ticket Type: {ticket_type}"
        ),

        reason=f"AFF ARMY Ticket opened by {user}"
    )

    # --------------------------------------------------------
    # MAIN TICKET EMBED
    # --------------------------------------------------------

    embed = discord.Embed(

        title=f"🎫 {ticket_title}",

        description=ticket_description,

        color=discord.Color.from_rgb(
            20,
            20,
            25
        )
    )

    embed.add_field(
        name="👤 PLAYER",
        value=user.mention,
        inline=True
    )

    embed.add_field(
        name="📂 CATEGORY",
        value=f"`{ticket_type}`",
        inline=True
    )

    embed.add_field(
        name="🟢 STATUS",
        value="`OPEN`",
        inline=True
    )

    # --------------------------------------------------------
    # CUSTOM FIELDS
    # --------------------------------------------------------

    if ticket_fields:

        for field_name, field_value in ticket_fields:

            embed.add_field(
                name=field_name,
                value=field_value,
                inline=False
            )

    # --------------------------------------------------------
    # SCREENSHOT INFO
    # --------------------------------------------------------

    if ticket_type == "FF Player Stats":

        embed.add_field(
            name="📸 SCREENSHOT / PROOF",
            value=(
                "Please click the **📸 Upload Screenshot / Proof** "
                "button below.\n\n"
                "After clicking it, send your latest "
                "**Free Fire profile/stats screenshot** "
                "as an attachment.\n\n"
                "🗑️ Your original upload will automatically "
                "be deleted after it is received."
            ),
            inline=False
        )

    else:

        embed.add_field(
            name="📸 SCREENSHOT / PROOF",
            value=(
                "You can upload screenshots/proof directly "
                "inside this private ticket."
            ),
            inline=False
        )

    embed.set_footer(
        text="AFF-ARMY • Professional Support System"
    )

    # --------------------------------------------------------
    # STAFF PANEL
    # --------------------------------------------------------

    staff_embed = discord.Embed(

        title="🛡️ STAFF CONTROL PANEL",

        description=(
            "**Staff members:**\n"
            "Use the buttons below to manage this ticket.\n\n"
            "🙋 **Claim** → Take responsibility for this ticket\n"
            "🔒 **Close** → Close the ticket\n"
            "🗑️ **Delete** → Delete after closing"
        ),

        color=discord.Color.dark_grey()
    )

    # --------------------------------------------------------
    # SEND MAIN TICKET
    # --------------------------------------------------------

    await channel.send(
        content=(
            f"{user.mention} <@&{staff_role.id}>"
        ),
        embed=embed,
        view=TicketControls()
    )

    # ========================================================
    # FF PLAYER STATS SCREENSHOT BUTTON
    # ========================================================

    if ticket_type == "FF Player Stats":

        screenshot_embed = discord.Embed(

            title="📸 FREE FIRE PROFILE SCREENSHOT",

            description=(
                "Please upload your **latest Free Fire "
                "profile/stats screenshot**.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📌 **STEP 1**\n"
                "Click **📸 Upload Screenshot / Proof**.\n\n"
                "📤 **STEP 2**\n"
                "Send your screenshot as an attachment "
                "in this ticket.\n\n"
                "🗑️ **STEP 3**\n"
                "Your original screenshot message will be "
                "automatically deleted.\n\n"
                "✅ **STEP 4**\n"
                "Bot will show **📸 SCREENSHOT RECEIVED** "
                "with your screenshot.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "✅ PNG / JPG / JPEG / WEBP supported.\n"
                "⏱️ You have **5 minutes** to upload."
            ),

            color=discord.Color.blue()
        )

        screenshot_embed.set_footer(
            text="AFF-ARMY • FF Player Profile Support"
        )

        await channel.send(
            embed=screenshot_embed,
            view=FFStatsScreenshotView(
                interaction.client
            )
        )

    # --------------------------------------------------------
    # STAFF EMBED
    # --------------------------------------------------------

    await channel.send(
        embed=staff_embed
    )

    # --------------------------------------------------------
    # CONFIRMATION
    # --------------------------------------------------------

    await interaction.response.send_message(
        f"✅ Your ticket has been created!\n"
        f"🎫 {channel.mention}",
        ephemeral=True
    )


# ============================================================
# FF PLAYER STATS MODAL
# ============================================================

class FFStatsModal(
    discord.ui.Modal,
    title="🎮 Free Fire Player Profile"
):

    ff_uid = discord.ui.TextInput(
        label="Free Fire UID",
        placeholder="Enter your Free Fire UID",
        required=True,
        max_length=30
    )

    kd = discord.ui.TextInput(
        label="KD / Kills",
        placeholder="Example: 3.45 KD",
        required=True,
        max_length=50
    )

    headshot = discord.ui.TextInput(
        label="Headshot Rate",
        placeholder="Example: 28.5%",
        required=True,
        max_length=50
    )

    rank = discord.ui.TextInput(
        label="Current Rank",
        placeholder="Example: Grandmaster / Heroic",
        required=True,
        max_length=100
    )

    requirement = discord.ui.TextInput(
        label="What do you need?",
        placeholder="Example: 1v4 / Profile Check / Tournament",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        fields = [

            (
                "🆔 FREE FIRE UID",
                f"`{self.ff_uid.value}`"
            ),

            (
                "📊 KD",
                f"`{self.kd.value}`"
            ),

            (
                "🎯 HEADSHOT RATE",
                f"`{self.headshot.value}`"
            ),

            (
                "🏆 CURRENT RANK",
                f"`{self.rank.value}`"
            ),

            (
                "📋 REQUEST",
                self.requirement.value
            )
        ]

        await create_ticket_channel(

            interaction=interaction,

            ticket_type="FF Player Stats",

            ticket_title="🎮 FREE FIRE PLAYER PROFILE",

            ticket_description=(
                "Welcome to **AFF ARMY Free Fire Support**.\n\n"
                "Your player information has been submitted "
                "to the staff team.\n\n"
                "📸 **Please upload your latest FF profile/"
                "stats screenshot below.**"
            ),

            ticket_fields=fields
        )


# ============================================================
# 1V4 MODAL
# ============================================================

class FF1v4Modal(
    discord.ui.Modal,
    title="🔥 1v4 Challenge Request"
):

    ff_uid = discord.ui.TextInput(
        label="Free Fire UID",
        placeholder="Enter your FF UID",
        required=True,
        max_length=30
    )

    player_name = discord.ui.TextInput(
        label="Player Name",
        placeholder="Your in-game name",
        required=True,
        max_length=100
    )

    kd = discord.ui.TextInput(
        label="KD / Headshot",
        placeholder="Example: 4.2 KD / 31% HS",
        required=True,
        max_length=100
    )

    challenge = discord.ui.TextInput(
        label="Challenge Details",
        placeholder="Explain what 1v4 challenge you want",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        fields = [

            (
                "🆔 FF UID",
                f"`{self.ff_uid.value}`"
            ),

            (
                "👤 PLAYER",
                self.player_name.value
            ),

            (
                "📊 KD / HS",
                self.kd.value
            ),

            (
                "🔥 CHALLENGE",
                self.challenge.value
            )
        ]

        await create_ticket_channel(

            interaction,

            "1v4 Challenge",

            "🔥 FREE FIRE 1v4 CHALLENGE",

            (
                "Welcome to the **AFF-ARMY 1v4 Challenge**.\n\n"
                "Staff will review your request and "
                "coordinate the challenge."
            ),

            fields
        )


# ============================================================
# 1V1 MODAL
# ============================================================

class FF1v1Modal(
    discord.ui.Modal,
    title="⚔️ 1v1 Challenge Request"
):

    ff_uid = discord.ui.TextInput(
        label="Free Fire UID",
        placeholder="Enter your FF UID",
        required=True,
        max_length=30
    )

    opponent = discord.ui.TextInput(
        label="Opponent UID / Name",
        placeholder="Opponent information",
        required=True,
        max_length=100
    )

    mode = discord.ui.TextInput(
        label="Mode",
        placeholder="Example: CS / BR / Custom",
        required=True,
        max_length=100
    )

    details = discord.ui.TextInput(
        label="Challenge Details",
        placeholder="Rules or other requirements",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        fields = [

            (
                "🆔 YOUR UID",
                f"`{self.ff_uid.value}`"
            ),

            (
                "⚔️ OPPONENT",
                self.opponent.value
            ),

            (
                "🎮 MODE",
                self.mode.value
            ),

            (
                "📋 DETAILS",
                self.details.value
            )
        ]

        await create_ticket_channel(

            interaction,

            "1v1 Challenge",

            "⚔️ FREE FIRE 1v1 CHALLENGE",

            (
                "Welcome to the **AFF ARMY 1v1 Challenge**.\n\n"
                "Staff will check the challenge details "
                "and assist you."
            ),

            fields
        )


# ============================================================
# TOURNAMENT MODAL
# ============================================================

class TournamentModal(
    discord.ui.Modal,
    title="🏆 Tournament Support"
):

    ff_uid = discord.ui.TextInput(
        label="Free Fire UID",
        placeholder="Enter your Free Fire UID",
        required=True,
        max_length=30
    )

    team = discord.ui.TextInput(
        label="Team / Squad Name",
        placeholder="Enter team name",
        required=True,
        max_length=100
    )

    players = discord.ui.TextInput(
        label="Number of Players",
        placeholder="Example: 4",
        required=True,
        max_length=20
    )

    details = discord.ui.TextInput(
        label="Tournament Requirement",
        placeholder="Explain what you need",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        fields = [

            (
                "🆔 FF UID",
                f"`{self.ff_uid.value}`"
            ),

            (
                "🏆 TEAM",
                self.team.value
            ),

            (
                "👥 PLAYERS",
                self.players.value
            ),

            (
                "📋 REQUIREMENT",
                self.details.value
            )
        ]

        await create_ticket_channel(

            interaction,

            "Tournament",

            "🏆 TOURNAMENT SUPPORT",

            (
                "Welcome to **AFF-ARMY Tournament Support**.\n\n"
                "Staff will assist you with your tournament request."
            ),

            fields
        )


# ============================================================
# OTHER SUPPORT MODAL
# ============================================================

class OtherSupportModal(
    discord.ui.Modal,
    title="🛠️ Other Support"
):

    subject = discord.ui.TextInput(
        label="Subject",
        placeholder="What do you need help with?",
        required=True,
        max_length=150
    )

    details = discord.ui.TextInput(
        label="Details",
        placeholder="Explain your issue in detail",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        fields = [

            (
                "📌 SUBJECT",
                self.subject.value
            ),

            (
                "📝 DETAILS",
                self.details.value
            )
        ]

        await create_ticket_channel(

            interaction,

            "Other Support",

            "🛠️ GENERAL SUPPORT",

            (
                "Welcome to **AFF-ARMY Support**.\n\n"
                "A staff member will review your request."
            ),

            fields
        )


# ============================================================
# TICKET DROPDOWN
# ============================================================

class TicketDropdown(
    discord.ui.Select
):

    def __init__(self):

        options = [

            discord.SelectOption(
                label="FF Player Profile / Stats",
                description="Submit your Free Fire profile & stats",
                emoji="🎮",
                value="stats"
            ),

            discord.SelectOption(
                label="1v1 Challenge",
                description="Request a Free Fire 1v1",
                emoji="⚔️",
                value="1v1"
            ),

            discord.SelectOption(
                label="1v4 Challenge",
                description="Request a Free Fire 1v4",
                emoji="🔥",
                value="1v4"
            ),

            discord.SelectOption(
                label="Tournament",
                description="Tournament / esports support",
                emoji="🏆",
                value="tournament"
            ),

            discord.SelectOption(
                label="Live Stream Support",
                description="Support related to a live stream",
                emoji="📺",
                value="live"
            ),

            discord.SelectOption(
                label="Other Support",
                description="Any other support request",
                emoji="🛠️",
                value="other"
            )
        ]

        super().__init__(

            placeholder="🎮 Select your support type...",

            min_values=1,

            max_values=1,

            options=options,

            custom_id="hsl_ticket_dropdown"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        value = self.values[0]

        # ----------------------------------------------------
        # FF STATS
        # ----------------------------------------------------

        if value == "stats":

            await interaction.response.send_modal(
                FFStatsModal()
            )

        # ----------------------------------------------------
        # 1V1
        # ----------------------------------------------------

        elif value == "1v1":

            await interaction.response.send_modal(
                FF1v1Modal()
            )

        # ----------------------------------------------------
        # 1V4
        # ----------------------------------------------------

        elif value == "1v4":

            await interaction.response.send_modal(
                FF1v4Modal()
            )

        # ----------------------------------------------------
        # TOURNAMENT
        # ----------------------------------------------------

        elif value == "tournament":

            await interaction.response.send_modal(
                TournamentModal()
            )

        # ----------------------------------------------------
        # LIVE STREAM
        # ----------------------------------------------------

        elif value == "live":

            await create_ticket_channel(

                interaction,

                "Live Stream",

                "📺 LIVE STREAM SUPPORT",

                (
                    "Welcome to **AFF-ARMY Live Stream Support**.\n\n"
                    "Please explain what happened during the "
                    "live stream and upload any relevant "
                    "screenshots/proof."
                )
            )

        # ----------------------------------------------------
        # OTHER
        # ----------------------------------------------------

        elif value == "other":

            await interaction.response.send_modal(
                OtherSupportModal()
            )


# ============================================================
# TICKET PANEL
# ============================================================

class TicketPanel(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            TicketDropdown()
        )


# ============================================================
# TICKET CONTROL BUTTONS
# ============================================================

class TicketControls(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    # ========================================================
    # CLAIM
    # ========================================================

    @discord.ui.button(
        label="Claim",
        emoji="🙋",
        style=discord.ButtonStyle.success,
        custom_id="hsl_claim_ticket"
    )
    async def claim_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ Only **Ticket Staff** can claim tickets.",
                ephemeral=True
            )

            return

        button.disabled = True

        embed = discord.Embed(

            title="🙋 TICKET CLAIMED",

            description=(
                f"This ticket has been claimed by "
                f"{interaction.user.mention}.\n\n"
                "🛡️ Staff is now handling this ticket."
            ),

            color=discord.Color.green()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

        await interaction.channel.send(
            f"🙋 {interaction.user.mention} has claimed this ticket."
        )

    # ========================================================
    # CLOSE
    # ========================================================

    @discord.ui.button(
        label="Close",
        emoji="🔒",
        style=discord.ButtonStyle.secondary,
        custom_id="hsl_close_ticket"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ Only **Ticket Staff** can close tickets.",
                ephemeral=True
            )

            return

        channel = interaction.channel

        # ----------------------------------------------------
        # GET OWNER
        # ----------------------------------------------------

        topic = channel.topic or ""

        owner_id = None

        if "Ticket Owner ID:" in topic:

            try:

                owner_id = int(
                    topic.split("Ticket Owner ID:")[1]
                    .split("|")[0]
                    .strip()
                )

            except Exception:

                owner_id = None

        # ----------------------------------------------------
        # REMOVE USER ACCESS
        # ----------------------------------------------------

        if owner_id:

            user = interaction.guild.get_member(
                owner_id
            )

            if user:

                await channel.set_permissions(

                    user,

                    view_channel=False,

                    send_messages=False,

                    attach_files=False
                )

        # ----------------------------------------------------
        # CLOSED STATUS
        # ----------------------------------------------------

        embed = discord.Embed(

            title="🔒 TICKET CLOSED",

            description=(
                "This ticket has been closed by "
                f"{interaction.user.mention}.\n\n"
                "🛡️ Staff can delete the ticket when finished."
            ),

            color=discord.Color.orange()
        )

        await interaction.response.send_message(
            embed=embed,
            view=ClosedTicketControls()
        )


# ============================================================
# CLOSED TICKET CONTROLS
# ============================================================

class ClosedTicketControls(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    # ========================================================
    # REOPEN
    # ========================================================

    @discord.ui.button(
        label="Reopen",
        emoji="🔓",
        style=discord.ButtonStyle.success,
        custom_id="hsl_reopen_ticket"
    )
    async def reopen_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ Only **Ticket Staff** can reopen tickets.",
                ephemeral=True
            )

            return

        channel = interaction.channel

        topic = channel.topic or ""

        owner_id = None

        if "Ticket Owner ID:" in topic:

            try:

                owner_id = int(
                    topic.split("Ticket Owner ID:")[1]
                    .split("|")[0]
                    .strip()
                )

            except Exception:

                pass

        # ----------------------------------------------------
        # RESTORE USER ACCESS
        # ----------------------------------------------------

        if owner_id:

            user = interaction.guild.get_member(
                owner_id
            )

            if user:

                await channel.set_permissions(

                    user,

                    view_channel=True,

                    send_messages=True,

                    read_message_history=True,

                    attach_files=True,

                    embed_links=True
                )

        # ----------------------------------------------------
        # REOPEN EMBED
        # ----------------------------------------------------

        embed = discord.Embed(

            title="🔓 TICKET REOPENED",

            description=(
                f"This ticket has been reopened by "
                f"{interaction.user.mention}."
            ),

            color=discord.Color.green()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=TicketControls()
        )

    # ========================================================
    # DELETE
    # ========================================================

    @discord.ui.button(
        label="Delete",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="hsl_delete_ticket"
    )
    async def delete_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ Only **Ticket Staff** can delete tickets.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🗑️ Deleting ticket...",
            ephemeral=True
        )

        await asyncio.sleep(1)

        await interaction.channel.delete(
            reason=f"Ticket deleted by {interaction.user}"
        )


# ============================================================
# TICKET COG
# ============================================================

class Ticket(
    commands.Cog
):

    def __init__(self, bot):

        self.bot = bot

    # ========================================================
    # TICKET PANEL COMMAND
    # ========================================================

    @commands.hybrid_command(
        name="ticketpanel",
        description="Create the AFF-ARMY professional ticket panel"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def ticketpanel(
        self,
        ctx
    ):

        embed = discord.Embed(

            title="🎫 AFF-ARMY SUPPORT CENTER",

            description=(

                "## ⚡ WELCOME TO AFF-ARMY\n\n"

                "Need help with **Free Fire, challenges, "
                "tournaments or other services?**\n\n"

                "Use the dropdown below and select the "
                "support category that matches your request.\n\n"

                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

                "🎮 **FF PLAYER PROFILE / STATS**\n"
                "Submit your UID, KD, Headshot Rate, Rank "
                "and profile screenshot.\n\n"

                "⚔️ **1v1 CHALLENGE**\n"
                "Request a custom 1v1 challenge.\n\n"

                "🔥 **1v4 CHALLENGE**\n"
                "Request a 1v4 challenge.\n\n"

                "🏆 **TOURNAMENT**\n"
                "Tournament and esports support.\n\n"

                "📺 **LIVE STREAM SUPPORT**\n"
                "Support for issues related to a live stream.\n\n"

                "🛠️ **OTHER SUPPORT**\n"
                "Anything else you need help with.\n\n"

                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

                "🔒 **PRIVATE TICKET**\n"
                "Your ticket is visible only to you and "
                "the AFF-ARMY staff team.\n\n"

                "📸 **PROOF / SCREENSHOTS**\n"
                "You can upload screenshots directly inside "
                "your private ticket."
            ),

            color=discord.Color.from_rgb(
                88,
                101,
                242
            )
        )

        embed.set_footer(
            text="AFF-ARMY • Professional Gaming Support"
        )

        await ctx.send(
            embed=embed,
            view=TicketPanel()
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        Ticket(bot)
    )

    # --------------------------------------------------------
    # PERSISTENT VIEWS
    # --------------------------------------------------------

    bot.add_view(
        TicketPanel()
    )

    bot.add_view(
        TicketControls()
    )

    bot.add_view(
        ClosedTicketControls()
    )

    bot.add_view(
        FFStatsScreenshotView(bot)
    )

