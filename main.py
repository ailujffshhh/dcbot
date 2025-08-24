import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import threading
from utils import extract_pdf_text, generate_formatted_pdf
import asyncio
from game import setup_game

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")

# OpenAI client (HuggingFace proxy)
client_ai = OpenAI(base_url="https://router.huggingface.co/v1", api_key=HF_API_KEY)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)  # Added a prefix

# FastAPI app
app = FastAPI()

@app.get("/")
@app.head("/")
async def root():
    return JSONResponse({"status": "Bot is running!"})

# Guild where slash commands will sync
GUILD_IDS = [1405134005359349760]

# Track processed messages to prevent duplicates
processed_messages = set()

# ---------------- MENTION CHAT ----------------
@bot.event
async def on_message(message: discord.Message):
    # Declare global before using the variable
    global processed_messages
    
    # Prevent processing the same message twice
    if message.id in processed_messages:
        return
    processed_messages.add(message.id)
    
    # Clean up old message IDs to prevent memory issues
    if len(processed_messages) > 1000:
        # Keep only the most recent 500 messages
        processed_messages = set(list(processed_messages)[-500:])
    
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
            )

            # Safely extract the content
            if response.choices and response.choices[0].message.content:
                answer = response.choices[0].message.content
                await thinking_msg.edit(content=f"{user_mention} {answer}")
            else:
                await thinking_msg.edit(content=f"{user_mention} ❌ No response from model.")

        except Exception as e:
            if "402" in str(e):
                await thinking_msg.edit(content=f"{user_mention} ❌ You've hit the monthly credit limit. Please try again later.")
            else:
                await thinking_msg.edit(content=f"{user_mention} ❌ Error: {str(e)}")
        
        # Return here to prevent processing commands for mentions
        return
    
    # Only process commands for messages that aren't mentions
    await bot.process_commands(message)

# ---------------- REVIEW COMMAND ----------------
@bot.tree.command(name="review", description="Upload a PDF handout to convert it into a reviewer")
async def review(interaction: discord.Interaction, file: discord.Attachment):
    if not file.filename.lower().endswith(".pdf"):
        await interaction.response.send_message(
            "⚠️ Please upload a valid **PDF file**.", ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"📄 Processing your file **{file.filename}** into a reviewer, stay still motherfucker...",
        ephemeral=True
    )

    try:
        # Save PDF locally
        file_path = f"./{file.filename}"
        await file.save(file_path)

        # Extract text
        pdf_text = extract_pdf_text(file_path)
        if not pdf_text:
            await interaction.followup.send(
                "⚠️ Could not extract any text from the PDF.", ephemeral=True
            )
            return

        # Generate reviewer using AI (non-thinking mode)
        response = client_ai.chat.completions.create(
            model="openai/gpt-oss-120b:fireworks-ai",
            messages=[
                {"role": "system", "content": "You are a helpful tutor that creates concise and easy-to-read reviewers from study handouts. Do NOT include reasoning or extra commentary. PLease prevent using '-' or dash because ReportLab doesn't recognize the tag. If you are adding like one-direction make it one direction (just space)."},
                {"role": "user", "content": f"Convert the following handout into a bullet-point reviewer:\n\n{pdf_text}. Do not add - or dash to your words"}
            ],
            temperature=0
        )
        print(response.choices[0].message.content)
        reviewer_text = response.choices[0].message.content

        # Generate formatted PDF
        output_file = generate_formatted_pdf(reviewer_text, "**{file.name}** (REVIEWER).pdf")

        # Send PDF to user
        await interaction.followup.send(
            content="📝 Your reviewer is ready! Download it below:",
            file=discord.File(output_file),
            ephemeral=True
        )

        # Cleanup
        os.remove(file_path)
        os.remove(output_file)

    except Exception as e:
        await interaction.followup.send(
            f"❌ Error processing file: {str(e)}", ephemeral=True
        )

# ---------------- READY EVENT ----------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    
    # Sync commands to all guilds
    for guild_id in GUILD_IDS:
        try:
            guild = discord.Object(id=guild_id)
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            print(f"✅ Synced commands to guild {guild_id}")
        except Exception as e:
            print(f"⚠️ Failed to sync commands to guild {guild_id}: {e}")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    import uvicorn
    
    # Run FastAPI in a separate thread
    def run_fastapi():
        uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
    
    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()

    setup_game(bot)
    # Run the Discord bot
    bot.run(DISCORD_TOKEN)
