import discord
from discord.ui import Button, View
import os
from datetime import datetime

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
# 1. Category ID สำหรับสร้างห้อง Ticket ใหม่
CATEGORY_ID = int(os.getenv("CATEGORY_ID") or os.getenv("CHANNEL_ID") or "0")

# 2. Role ID ของทีมงาน/สตาฟ ที่ต้องการให้เห็นห้อง Ticket
# (สามารถนำ Role ID จาก Discord มาใส่แทนเลข 0 หรือรับจาก Environment Variable)
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID") or "1530871675879559229")

# 3. สีเขียวเข้ม EVA Air (HEX: #006039)
EVA_GREEN = discord.Color.from_rgb(0, 96, 57)

# ==========================================
# 🤖 BOT SETUP
# ==========================================
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

# บันทึกสถานะตั๋วที่เปิดอยู่ {user_id: channel_id}
active_tickets = {}

# ==========================================
# 🎨 EMBED CREATOR (EVA AIR STYLE)
# ==========================================
def create_eva_embed(author: discord.User, title: str, message: discord.Message):
    description = message.content if message.content else ""
    
    # จัดการไฟล์แนบและรูปภาพ
    attachments_text = ""
    first_image_url = None

    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                if not first_image_url:
                    first_image_url = attachment.url
            attachments_text += f"📎 [{attachment.filename}]({attachment.url})\n"

    if attachments_text:
        description += f"\n\n**Attachments:**\n{attachments_text}"

    embed = discord.Embed(
        title=title,
        description=description,
        color=EVA_GREEN
    )
    
    # แสดงพรีวิวรูปภาพ (ถ้ามี)
    if first_image_url:
        embed.set_image(url=first_image_url)

    # ส่วน Author (ชื่อ และ รูปโปรไฟล์ผู้ส่ง)
    avatar_url = author.display_avatar.url if author.display_avatar else author.default_avatar.url
    embed.set_author(name=author.display_name, icon_url=avatar_url)
    
    # ส่วน Footer ด้านล่าง
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    embed.set_footer(text=f"EVA Airways Corporation | {author.id} • {now_str}")
    return embed


# ==========================================
# 🔘 UI COMPONENTS
# ==========================================
class TicketConfirmView(View):
    def __init__(self, initial_message: discord.Message, user: discord.User):
        super().__init__(timeout=None)
        self.initial_message = initial_message
        self.user = user

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)

        # ปิดปุ่มกดหลังจากยืนยัน
        for child in self.children:
            child.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception as e:
            print(f"Failed to edit view: {e}")

        # ดึง Category
        category = client.get_channel(CATEGORY_ID)
        if not category or not isinstance(category, discord.CategoryChannel):
            try:
                category = await client.fetch_channel(CATEGORY_ID)
            except Exception as e:
                print(f"❌ Failed to fetch category {CATEGORY_ID}: {e}")

        if category and isinstance(category, discord.CategoryChannel):
            guild = category.guild

            # 🛠️ ตั้งค่า OVERWRITES (สิทธิ์เข้าถึงห้อง)
            overwrites = {
                # ซ่อนห้องจากสมาชิกทั่วไป (@everyone)
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                # อนุญาตให้บอทมองเห็นและตอบกลับ
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            # เพิ่มสิทธิ์ให้ Role ทีมงาน/สตาฟ (ถ้าระบุ STAFF_ROLE_ID ไว้)
            if STAFF_ROLE_ID != 0:
                staff_role = guild.get_role(STAFF_ROLE_ID)
                if staff_role:
                    overwrites[staff_role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        attach_files=True,
                        embed_links=True
                    )

            try:
                # สร้างห้อง Ticket
                channel_name = f"ticket-{self.user.name}".lower().replace(" ", "-")
                ticket_channel = await guild.create_text_channel(
                    name=channel_name,
                    category=category,
                    overwrites=overwrites
                )

                active_tickets[self.user.id] = ticket_channel.id

                # ส่ง Embed ข้อความแรกลงในห้อง Ticket
                embed = create_eva_embed(
                    author=self.user,
                    title="Message Received",
                    message=self.initial_message
                )
                await ticket_channel.send(embed=embed)

                await interaction.followup.send("✅ **Your ticket channel has been created! Our support team will assist you shortly.**")

            except Exception as e:
                print(f"❌ Error creating channel: {e}")
                await interaction.followup.send(f"❌ Failed to create ticket channel: {e}")
        else:
            await interaction.followup.send("❌ Error: Invalid Category ID. Please check Railway Variables.")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        for child in self.children:
            child.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception as e:
            print(f"Failed to edit view: {e}")
            
        await interaction.followup.send("❌ **Ticket creation cancelled.**")


# ==========================================
# 🚀 EVENT HANDLERS
# ==========================================
@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')
    print(f'📌 Target Category ID: {CATEGORY_ID}')
    if STAFF_ROLE_ID != 0:
        print(f'🛡️ Target Staff Role ID: {STAFF_ROLE_ID}')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # 📩 1. เมื่อผู้ใช้ส่ง DM หาบอท
    if isinstance(message.channel, discord.DMChannel):
        
        # ถ้าเปิด Ticket ไว้อยู่แล้ว ให้ส่ง Embed เข้าห้อง Ticket ของสตาฟ
        if message.author.id in active_tickets:
            ticket_channel_id = active_tickets[message.author.id]
            ticket_channel = client.get_channel(ticket_channel_id) or await client.fetch_channel(ticket_channel_id)
            
            if ticket_channel:
                embed = create_eva_embed(
                    author=message.author,
                    title="Message Received",
                    message=message
                )
                await ticket_channel.send(embed=embed)
                await message.add_reaction("✅")
            else:
                await message.channel.send("❌ Active ticket channel not found.")
            return

        # ถ้ายังไม่ได้เปิด Ticket -> ถามยืนยันเพื่อสร้างห้อง
        embed = discord.Embed(
            title="Are you sure you want to create a new support ticket?",
            description="Click **Create Ticket** to send your request to the support team or **Cancel** to abort.",
            color=EVA_GREEN
        )
        view = TicketConfirmView(message, message.author)
        await message.channel.send(embed=embed, view=view)
        return

    # 🛠️ 2. เมื่อสตาฟพิมพ์ตอบกลับจากในห้อง Discord Ticket
    for uid, ch_id in list(active_tickets.items()):
        if message.channel.id == ch_id:
            
            # คำสั่ง !close เพื่อลบห้อง
            if message.content.startswith("!close"):
                target_user = client.get_user(uid) or await client.fetch_user(uid)
                if target_user:
                    try:
                        await target_user.send("🔒 **Your support ticket has been closed. Thank you!**")
                    except Exception as e:
                        print(f"Error sending DM: {e}")
                
                del active_tickets[uid]
                await message.channel.send("🔒 Closing and deleting channel in 5 seconds...")
                import asyncio
                await asyncio.sleep(5)
                await message.channel.delete()
                return

            # คำสั่ง !claim (สตาฟรับเรื่อง)
            if message.content.startswith("!claim"):
                target_user = client.get_user(uid) or await client.fetch_user(uid)
                if target_user:
                    staff_name = message.author.display_name
                    claim_embed = discord.Embed(
                        title="Support Agent Connected",
                        description=(
                            f"Greetings and salutations, **{staff_name}** with the support agent. "
                            f"Please provide your inquiry to ensure a fast and efficient assistance process.\n\n"
                            f"Thank you!"
                        ),
                        color=discord.Color.from_rgb(209, 17, 36)
                    )
                    claim_embed.set_author(name="Support Agent Connected")
                    await target_user.send(embed=claim_embed)
                    await message.add_reaction("✅")
                    await message.channel.send(f"🟢 **{staff_name}** has claimed this ticket.")
                return

            # ข้อความทั่วไปจากสตาฟ -> ส่ง Embed หาผู้ใช้ใน DM
            target_user = client.get_user(uid) or await client.fetch_user(uid)
            if target_user:
                embed = create_eva_embed(
                    author=message.author,
                    title="Support Response",
                    message=message
                )
                await target_user.send(embed=embed)
                await message.add_reaction("✅")
            break

client.run(os.getenv("DISCORD_TOKEN"))
