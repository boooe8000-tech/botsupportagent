import discord
from discord.ui import Button, View
import os

# 1. ตั้งค่า Intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

# ดึง Category ID จาก Railway
CATEGORY_ID = int(os.getenv("CATEGORY_ID") or os.getenv("CHANNEL_ID") or "0")

# เก็บข้อมูลตั๋วที่เปิดอยู่ {user_id: channel_id}
active_tickets = {}

# 🔘 Class สำหรับปุ่มกด Confirm / Cancel
class TicketConfirmView(View):
    def __init__(self, user_message_content, user):
        super().__init__(timeout=None)
        self.user_message_content = user_message_content
        self.user = user

    # ปุ่ม Create Ticket (สีเขียว)
    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)

        # ปิดปุ่มกด
        for child in self.children:
            child.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception as e:
            print(f"Failed to edit view: {e}")

        # ดึง Category ตาม ID ที่ตั้งไว้
        category = client.get_channel(CATEGORY_ID)
        if not category or not isinstance(category, discord.CategoryChannel):
            try:
                category = await client.fetch_channel(CATEGORY_ID)
            except Exception as e:
                print(f"❌ Failed to fetch category {CATEGORY_ID}: {e}")

        if category and isinstance(category, discord.CategoryChannel):
            guild = category.guild

            # 🛠️ ตั้งค่าสิทธิ์ของห้อง Ticket ใหม่
            # - ให้สตาฟมองเห็น ( Customer Service Team / Admin )
            # - ซ่อนห้องจากคนทั่วไป (@everyone)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            try:
                # ➕ สร้าง Text Channel ใหม่ใต้มวดหมู่ (Category)
                channel_name = f"ticket-{self.user.name}".lower().replace(" ", "-")
                ticket_channel = await guild.create_text_channel(
                    name=channel_name,
                    category=category,
                    overwrites=overwrites
                )

                # บันทึกสถานะว่าเปิดตั๋วอยู่ในห้องไหน
                active_tickets[self.user.id] = ticket_channel.id

                # ส่งข้อความแรกเข้าห้องตั๋วที่เพิ่งสร้าง
                embed = discord.Embed(
                    title=f"Ticket: {self.user.display_name}",
                    description=f"**User ID:** `{self.user.id}`\n\n**Inquiry:**\n{self.user_message_content}",
                    color=discord.Color.blue()
                )
                await ticket_channel.send(content=f"📩 **New Ticket Created!**", embed=embed)

                # แจ้งกลับหายูสเซอร์ใน DM
                await interaction.followup.send("✅ **Your ticket channel has been created! Our support team will assist you shortly.**")

            except Exception as e:
                print(f"❌ Error creating channel: {e}")
                await interaction.followup.send(f"❌ Failed to create ticket channel: {e}")
        else:
            await interaction.followup.send("❌ Error: Invalid Category ID. Please check Railway Variables.")

    # ปุ่ม Cancel (สีแดง)
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


@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')
    print(f'📌 Target Category ID set to: {CATEGORY_ID}')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # 📩 1. เมื่อยูสเซอร์ส่ง DM หาบอท
    if isinstance(message.channel, discord.DMChannel):
        
        # ถ้าเปิด Ticket ไว้อยู่แล้ว ให้ส่งข้อความเข้าไปในห้อง Ticket ของเขา
        if message.author.id in active_tickets:
            ticket_channel_id = active_tickets[message.author.id]
            ticket_channel = client.get_channel(ticket_channel_id) or await client.fetch_channel(ticket_channel_id)
            
            if ticket_channel:
                await ticket_channel.send(f"💬 **[{message.author.display_name}]**: {message.content}")
                await message.add_reaction("✅")
            else:
                await message.channel.send("❌ Active ticket channel not found.")
            return

        # ถ้ายังไม่ได้เปิด Ticket -> ส่ง Embed พร้อมปุ่ม Create Ticket
        embed = discord.Embed(
            title="Are you sure you want to create a new support ticket?",
            description="Click **Create Ticket** to send your request to the support team or **Cancel** to abort.",
            color=discord.Color.blue()
        )
        view = TicketConfirmView(message.content, message.author)
        await message.channel.send(embed=embed, view=view)
        return

    # 🛠️ 2. เมื่อสตาฟพิมพ์ตอบกลับจากในห้อง Discord
    # ถ้าข้อความส่งมาจากห้อง Ticket ที่สร้างขึ้น
    for uid, ch_id in list(active_tickets.items()):
        if message.channel.id == ch_id:
            
            # คำสั่ง !close เพื่อปิดและลบห้อง
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

            # คำสั่ง !claim (ส่ง Embed สีแดงหาผู้ใช้)
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

            # พิมพ์ข้อความธรรมดาในห้อง Ticket -> บอทจะส่ง DM ไปหายูสเซอร์คนนั้นให้อัตโนมัติ!
            target_user = client.get_user(uid) or await client.fetch_user(uid)
            if target_user:
                await target_user.send(f"💬 **Support Response:** {message.content}")
                await message.add_reaction("✅")
            break

client.run(os.getenv("DISCORD_TOKEN"))
