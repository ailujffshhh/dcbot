import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import threading
from utils import extract_pdf_text, generate_formatted_pdf, split_text, clean_text, save_conversations, load_conversations, reset_conversation

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")

client_ai = OpenAI(base_url="https://router.huggingface.co/v1", api_key=HF_API_KEY)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=None, intents=intents)

app = FastAPI()

@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return JSONResponse({"status": "Bot is running!"})

GUILD_IDS = [1405134005359349760]

@bot.tree.command(name="chat", description="Ask Doc Ron a question")
async def chat(interaction: discord.Interaction, prompt: str):
    user_id = str(interaction.user.id)
    await interaction.response.send_message(f"{interaction.user.mention} asked: {prompt}\nDr. Ron is thinking...")
    
    conversations = load_conversations()
    if user_id not in conversations:
        conversations[user_id] = []
    
    conversations[user_id].append({"role": "user", "content": prompt})
    
    try:
        response = client_ai.chat.completions.create(
            model="openai/gpt-oss-120b:fireworks-ai",
            messages=[{"role": "system", "content": "Your name is Doc Ron. You are a helpful tutor."}] + conversations[user_id],
            temperature=0.7
        )
        answer = clean_text(response.choices[0].message.content)
        conversations[user_id].append({"role": "assistant", "content": answer})
        save_conversations(conversations)
        
        for chunk in split_text(answer):
            await interaction.followup.send(f"{interaction.user.mention} {chunk}")
    
    except Exception as e:
        error_str = str(e)
        if "402" in error_str or "exceeded your monthly" in error_str:
            reset_conversation(user_id)
            await interaction.followup.send(f"{interaction.user.mention}  Monthly limit reached. Starting a new conversation. Please try again.")
        else:
            await interaction.followup.send(f"{interaction.user.mention}  Error: {error_str}")

@bot.tree.command(name="review", description="Upload a PDF handout to convert it into a reviewer")
async def review(interaction: discord.Interaction, file: discord.Attachment):
    if not file.filename.lower().endswith(".pdf"):
        await interaction.response.send_message(" Please upload a valid PDF.", ephemeral=True)
        return
    await interaction.response.send_message(f" Processing your file **{file.filename}**...", ephemeral=True)
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
            temperature=0
        )
        reviewer_text = clean_text(response.choices[0].message.content)
        output_file = generate_formatted_pdf(reviewer_text, f"{file.filename}_REVIEWER.pdf")
        await interaction.followup.send(content=" Your reviewer is ready!", file=discord.File(output_file), ephemeral=True)
        os.remove(file_path)
        os.remove(output_file)
    except Exception as e:
        await interaction.followup.send(f" Error processing file: {str(e)}", ephemeral=True)

@bot.event
async def on_ready():
    for guild_id in GUILD_IDS:
        await bot.tree.sync(guild=discord.Object(id=guild_id))
    print(f"✅ Logged in as {bot.user}")

if __name__ == "__main__":
    import uvicorn
    threading.Thread(target=lambda: uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000))), daemon=True).start()
    bot.run(DISCORD_TOKEN)
