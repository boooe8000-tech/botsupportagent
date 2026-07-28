import discord
import os

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True
intents.reactions = True

client = discord.Client(intents=intents)

CHANNEL_ID = int(os.getenv("CHANNEL_ID") or os.getenv("CATEGORY_ID") or "0")

# พจนานุกรมสำหรับเก็บข้อความชั่วคราวรอการยืนยัน {message_id: content}
pending_tickets = {}

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # 📩 1. เมื่อมีคน DM หาบอท
    if isinstance(message.channel, discord.DMChannel):
        try:
            await message.add_reaction("✅")
        except Exception as e:
            print(f"Error adding reaction: {e}")

        pending_tickets[message.id] = message.content

        embed = discord.Embed(
            title="Are you sure you want to create a new support ticket?",
            description="React to ✅ to send a ticket to the support team.",
            color=discord.Color.blue()
        )
        await message.channel.send(embed=embed)
        return

    # 🛠️ โซนคำสั่งสำหรับสตาฟใน Channel
    if message.channel.id == CHANNEL_ID:
        
        # 📌 2. คำสั่ง !claim <User_ID> (ส่ง Embed รับเรื่องให้ยูสเซอร์)
        if message.content.startswith("!claim"):
            parts = message.content.split()
            if len(parts) < 2:
                await message.channel.send("⚠️ **Format:** `!claim <User_ID>`")
                return

            try:
                target_user_id = int(parts[1])
                target_user = await client.fetch_user(target_user_id)
                
                if target_user:
                    # ดึงชื่อสตาฟที่พิมพ์คำสั่ง
                    staff_name = message.author.display_name
                    
                    # สร้าง Embed แบบในภาพ (สีแดง #D11124)
                    claim_embed = discord.Embed(
                        title="Support Agent Connected",
                        description=(
                            f"Greetings and salutations, **{staff_name}** with the support agent. "
                            f"Please provide your inquiry to ensure a fast and efficient assistance process.\n\n"
                            f"Thank you!"
                        ),
                        color=discord.Color.from_rgb(209, 17, 36)
                    )
                    
                    # ใส่โลโก้ข้างบนภาพ Embed (ถ้ามีลิงก์รูปให้ใส่ใน url)
                    claim_embed.set_author(
                        name="Support Agent Connected"
                    )

                    await target_user.send(embed=claim_embed)
                    await message.add_reaction("✅")
                    await message.channel.send(f"🟢 **{staff_name}** has claimed ticket for `{target_user.name}` (ID: `{target_user_id}`)")
                else:
                    await message.channel.send("❌ Could not find user.")
            except ValueError:
                await message.channel.send("❌ Invalid User ID.")
            except Exception as e:
                await message.channel.send(f"❌ Error sending claim message: {e}")
            return

        # 📤 3. คำสั่ง r! <User_ID> <ข้อความ> (ส่งข้อความตอบกลับธรรมดา)
        if message.content.startswith("r!"):
            try:
                parts = message.content.split(" ", 2)
                if len(parts) < 3:
                    await message.channel.send("⚠️ **Format:** `r! <User_ID> <Message>`")
                    return
                    
                target_user_id = int(parts[1])
                reply_text = parts[2]
                
                target_user = await client.fetch_user(target_user_id)
                if target_user:
                    await target_user.send(f"💬 **Support Response:** {reply_text}")
                    await message.add_reaction("✅")
                else:
                    await message.channel.send("❌ Could not find user.")
            except Exception as e:
                await message.channel.send(f"❌ Error: {e}")

@client.event
async def on_raw_reaction_add(payload):
    if payload.user_id == client.user.id:
        return

    if str(payload.emoji) == "✅" and payload.message_id in pending_tickets:
        user_message_content = pending_tickets.pop(payload.message_id)
        
        target_channel = client.get_channel(CHANNEL_ID)
        if target_channel:
            user = await client.fetch_user(payload.user_id)
            
            await target_channel.send(
                f"📩 **[New Ticket from {user.display_name}]** (User ID: `{user.id}`):\n{user_message_content}"
            )
            
            try:
                dm_channel = await user.create_dm()
                await dm_channel.send("✅ **Your ticket has been sent to the support team!**")
            except Exception as e:
                print(f"Error sending confirmation DM: {e}")

client.run(os.getenv("DISCORD_TOKEN"))
