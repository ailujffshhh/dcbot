import os
import threading
import discord
from discord.ext import commands
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from openai import OpenAI

from utils import extract_pdf_text, generate_formatted_pdf
from game import setup_game, handle_game_message
from chatbot import handle_chatbot_message

# ----- Env -----
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")

# ----- OpenAI (HuggingFace router) -----
client_ai = OpenAI(base_url="https://router.huggingface.co/v1", api_key=HF_API_KEY)

# ----- Discord Bot -----
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ----- FastAPI (health check) -----
app = FastAPI()
@app.get("/")
@app.head("/")
async def root():
    return JSONResponse({"status": "Bot is running!"})

# Optional: limit slash command sync to a guild for faster updates
GUILD_IDS = [1405134005359349760]

# Dedup message IDs
processed_messages = set()

# ========== MESSAGE ROUTER ==========
@bot.event
async def on_message(message: discord.Message):
    global processed_messages
    if message.author.bot:
        return

    # prevent duplicates
    if message.id in processed_messages:
        return
    processed_messages.add(message.id)
    if len(processed_messages) > 1000:
        processed_messages = set(list(processed_messages)[-500:])

    # 1) Let the game own its channel(s)
    handled = await handle_game_message(message, bot)
    if handled:
        return

    # 2) Chatbot mention handler
    handled = await handle_chatbot_message(message, bot, client_ai)
    if handled:
        return

    # 3) Finally, allow commands
    await bot.process_commands(message)

# ========== /review SLASH COMMAND ==========
@bot.tree.command(name="review", description="Upload a PDF handout to convert it into a reviewer")
async def review(interaction: discord.Interaction, file: discord.Attachment):
    if not file.filename.lower().endswith(".pdf"):
        await interaction.response.send_message("⚠️ Please upload a valid PDF file.", ephemeral=True)
        return

    await interaction.response.send_message(
        f"📄 Processing your file **{file.filename}** into a reviewer...",
        ephemeral=True
    )

    try:
        # Save locally
        file_path = f"./{file.filename}"
        await file.save(file_path)

        # Extract text
        pdf_text = extract_pdf_text(file_path)
        if not pdf_text:
            await interaction.followup.send("⚠️ Could not extract any text from the PDF.", ephemeral=True)
            return

        # Generate reviewer
        response = client_ai.chat.completions.create(
            model="openai/gpt-oss-120b:fireworks-ai",
            messages=[
                {
                    "role": "system",
                    "content": "You create concise bullet-point reviewers from study handouts. "
                               "No reasoning or extra commentary. Do not use dashes '-'."
                },
                {"role": "user", "content": f"Convert this handout into a bullet-point reviewer:\n\n{pdf_text}"}
            ],
            temperature=0
        )

        reviewer_text = response.choices[0].message.content
        output_file = generate_formatted_pdf(reviewer_text, f"{file.filename} (REVIEWER).pdf")

        await interaction.followup.send(
            content="📝 Your reviewer is ready! Download it below:",
            file=discord.File(output_file),
            ephemeral=True
        )

        os.remove(file_path)
        os.remove(output_file)

    except Exception as e:
        await interaction.followup.send(f"❌ Error processing file: {str(e)}", ephemeral=True)

# ========== READY ==========
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    # Fast guild sync (optional)
    for guild_id in GUILD_IDS:
        try:
            guild = discord.Object(id=guild_id)
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            print(f"✅ Synced commands to guild {guild_id}")
        except Exception as e:
            print(f"⚠️ Failed to sync commands to guild {guild_id}: {e}")

# ========== MAIN ==========
if __name__ == "__main__":
    import uvicorn

    def run_fastapi():
        uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

    threading.Thread(target=run_fastapi, daemon=True).start()

    setup_game(bot)  # start tasks/listeners owned by the game
    bot.run(DISCORD_TOKEN)
