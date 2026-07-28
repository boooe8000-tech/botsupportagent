import discord
from discord.ui import Button, View
import os

# 1. ตั้งค่า Intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

CHANNEL_ID = int(os.getenv("CHANNEL_ID") or os.getenv("CATEGORY_ID") or "0")

# 🔘 สร้าง Class สำหรับปุ่มกด Confirm / Cancel
class TicketConfirmView(View):
    def __init__(self, user_message_content, user):
        super().__init__(timeout=300) # หมดเวลาใน 5 นาที
        self.user_message_content = user_message_content
        self.user = user

    # ปุ่ม ยืนยัน (สีเขียว)
    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_callback(self, interaction: discord.Interaction, button: Button):
        # ปิดปุ่มกดหลังจากคลิกแล้ว
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        target_channel = client.get_channel(CHANNEL_ID)
        if not target_channel:
            try:
                target_channel = await client.fetch_channel(CHANNEL_ID)
            except Exception as e:
                print(f"❌ Failed to fetch channel {CHANNEL_ID}: {e}")

        if target_channel:
            # ส่งตั๋วเข้าห้องสตาฟ
            await target_channel.send(
                f"📩 **[New Ticket from {self.user.display_name}]** (User ID: `{self.user.id}`):\n{self.user_message_content}"
            )
            await interaction.followup.send("✅ **Your ticket has been sent to the support team!**")
        else:
            await interaction.followup.send("❌ Error: Target support channel not found.")

    # ปุ่ม ยกเลิก (สีแดง)
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_callback(self, interaction: discord.Interaction, button: Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("❌ **Ticket creation cancelled.**")


@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')
    print(f'📌 Target Channel ID set to: {CHANNEL_ID}')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # 📩 1. เมื่อยูสเซอร์ DM หาบอท
    if isinstance(message.channel, discord.DMChannel):
        embed = discord.Embed(
            title="Are you sure you want to create a new support ticket?",
            description="Click **Create Ticket** to send your request to the support team or **Cancel** to abort.",
            color=discord.Color.blue()
        )
        
        # สร้าง View ที่มีปุ่มกด แล้วส่งไปพร้อม Embed
        view = TicketConfirmView(message.content, message.author)
        await message.channel.send(embed=embed, view=view)
        return

    # 🛠️ 2. คำสั่งสตาฟใน Channel สตาฟ
    if message.channel.id == CHANNEL_ID:
        
        # คำสั่ง !claim <User_ID>
        if message.content.startswith("!claim"):
            parts = message.content.split()
            if len(parts) < 2:
                await message.channel.send("⚠️ **Format:** `!claim <User_ID>`")
                return

            try:
                target_user_id = int(parts[1])
                target_user = client.get_user(target_user_id) or await client.fetch_user(target_user_id)
                
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
                    await message.channel.send(f"🟢 **{staff_name}** has claimed ticket for `{target_user.name}` (ID: `{target_user_id}`)")
                else:
                    await message.channel.send("❌ Could not find user.")
            except Exception as e:
                await message.channel.send(f"❌ Error: {e}")
            return

        # คำสั่ง r! <User_ID> <ข้อความ>
        if message.content.startswith("r!"):
            try:
                parts = message.content.split(" ", 2)
                if len(parts) < 3:
                    await message.channel.send("⚠️ **Format:** `r! <User_ID> <Message>`")
                    return
                    
                target_user_id = int(parts[1])
                reply_text = parts[2]
                
                target_user = client.get_user(target_user_id) or await client.fetch_user(target_user_id)

                if target_user:
                    await target_user.send(f"💬 **Support Response:** {reply_text}")
                    await message.add_reaction("✅")
                else:
                    await message.channel.send("❌ Could not find user.")
            except Exception as e:
                await message.channel.send(f"❌ Error: {e}")

client.run(os.getenv("DISCORD_TOKEN"))
