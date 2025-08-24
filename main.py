import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from openai import OpenAI
from utils import clean_text, split_text

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
client = OpenAI(api_key=OPENAI_API_KEY)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")


@bot.tree.command(name="chat", description="Talk to Dr. Ron")
async def chat(interaction: discord.Interaction, prompt: str):
    user_mention = interaction.user.mention

    # Send initial response immediately
    await interaction.response.send_message(f"{user_mention} asked: {prompt}\n🤔 Dr. Ron is thinking...")

    try:
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        reply = response.choices[0].message.content

    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        reply = error_msg

    reply = clean_text(reply)

    # Split long replies into Discord-safe chunks
    chunks = split_text(reply)

    # Followup with actual reply
    for chunk in chunks:
        await interaction.followup.send(chunk)


bot.run(DISCORD_TOKEN)
