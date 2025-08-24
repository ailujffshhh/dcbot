import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import threading
from utils import extract_pdf_text, generate_formatted_pdf

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")

# OpenAI client (HuggingFace proxy)
client_ai = OpenAI(base_url="https://router.huggingface.co/v1", api_key=HF_API_KEY)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=None, intents=intents)

# FastAPI app
app = FastAPI()

@app.get("/")
@app.head("/")
async def root():
    return JSONResponse({"status": "Bot is running!"})

# Guild where slash commands will sync
GUILD_IDS = [1405134005359349760]

# ---------------- MENTION CHAT ----------------
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return  # ignore other bots

    # Check if bot is mentioned
    if bot.user.mentioned_in(message):
        user_mention = message.author.mention
        prompt = message.content.replace(f"<@{bot.user.id}>", "").strip()

        if not prompt:
            await message.reply(" Hi! Mention me with a question like: `@Dr. Ron what is photosynthesis?`")
            return

        thinking_msg = await message.reply(" Doc Ron is thinking...")

        try:
            response = client_ai.chat.completions.create(
                model="openai/gpt-oss-120b:fireworks-ai",
                messages=[
                    {"role": "system", "content": "Your name is Doc Ron. You are a helpful tutor. Respond in casual Filipino style. Limit your responses with 1 sentence only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            answer = response.choices[0].message.content

            await thinking_msg.edit(content=f"{user_mention} asked: {prompt}\n\n{user_mention} {answer}")

        except Exception as e:
            if "402" in str(e):
                await thinking_msg.edit(content=f"{user_mention} ❌ You’ve hit the **monthly credit limit**. Please try again later.")
            else:
                await thinking_msg.edit(content=f"{user_mention} ❌ Error: {str(e)}")

# ---------------- REVIEW COMMAND ----------------
@bot.tree.command(name="review", description="Upload a PDF handout to convert it into a reviewer")
async def review(interaction: discord.Interaction, file: discord.Attachment):
    if not file.filename.lower().endswith(".pdf"):
        await interaction.response.send_message("⚠️ Please upload a valid **PDF file**.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)

    try:
        file_path = f"./{file.filename}"
        await file.save(file_path)

        pdf_text = extract_pdf_text(file_path)
        response = client_ai.chat.completions.create(
            model="openai/gpt-oss-120b:fireworks-ai",
            messages=[
                {"role": "system", "content": "Your name is Doc Ron. You create concise reviewers."},
                {"role": "user", "content": f"Convert the following handout into bullet points:\n\n{pdf_text}"}
            ],
            temperature=0,
            max_tokens=800
        )
        reviewer_text = response.choices[0].message.content
        output_file = generate_formatted_pdf(reviewer_text, f"{file.filename}_REVIEWER.pdf")

        await interaction.followup.send(
            content="📝 Your reviewer is ready! Download it below:",
            file=discord.File(output_file),
            ephemeral=True
        )

        os.remove(file_path)
        os.remove(output_file)

    except Exception as e:
        if "402" in str(e):
            await interaction.followup.send("❌ You’ve hit the **monthly credit limit**. Please try again later.", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Error processing file: {str(e)}", ephemeral=True)

# ---------------- READY EVENT ----------------
@bot.event
async def on_ready():
    for guild_id in GUILD_IDS:
        try:
            await bot.tree.sync(guild=discord.Object(id=guild_id))
            print(f"✅ Synced commands to guild {guild_id}")
        except Exception as e:
            print(f"⚠️ Failed to sync commands: {e}")
    print(f"✅ Logged in as {bot.user}")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    import uvicorn
    threading.Thread(
        target=lambda: uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000))),
        daemon=True
    ).start()
    bot.run(DISCORD_TOKEN)
