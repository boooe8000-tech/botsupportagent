import os
import asyncio
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.dm_messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

CATEGORY_ID = int(os.getenv("CATEGORY_ID", "0"))
TOKEN = os.getenv("DISCORD_TOKEN")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # User DMs the bot
    if isinstance(message.channel, discord.DMChannel):
        guild = bot.guilds[0]
        category = guild.get_channel(CATEGORY_ID)

        if not category:
            print("Error: Category ID not found or invalid.")
            return

        channel_name = f"ticket-{message.author.name}".lower().replace(" ", "-")
        channel = discord.utils.get(category.channels, name=channel_name)

        if not channel:
            channel = await category.create_text_channel(name=channel_name)
            embed = discord.Embed(
                title="New Modmail Ticket",
                description=f"User: {message.author.mention}\nUser ID: `{message.author.id}`",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)

        await channel.send(f"**{message.author.name}**: {message.content}")
        await message.channel.send("Your message has been sent to the support team.")

    # Staff replies in ticket channel
    elif message.channel.category_id == CATEGORY_ID:
        if message.content.startswith("!"):
            await bot.process_commands(message)
            return

        username = message.channel.name.replace("ticket-", "")
        member = discord.utils.find(lambda m: m.name.lower().replace(" ", "-") == username, message.guild.members)

        if member:
            await member.send(f"**Support Staff**: {message.content}")
            await message.channel.send("Message delivered to user.")
        else:
            await message.channel.send("Could not find the user to send DM.")

    await bot.process_commands(message)

@bot.command()
async def close(ctx):
    if ctx.channel.category_id == CATEGORY_ID:
        await ctx.send("Closing ticket in 5 seconds...")
        await asyncio.sleep(5)
        await ctx.channel.delete()

if __name__ == "__main__":
    bot.run(TOKEN)