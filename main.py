import os
import re
import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI
import PyPDF2
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import threading

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is not set!")
print("✅ Discord token loaded correctly.")

client_ai = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_API_KEY,
)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=None, intents=intents)

app = FastAPI()

@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return JSONResponse({"status": "Bot is running!"})

def extract_pdf_text(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + " "
    return text.strip()

def markdown_to_pdf(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'`(.*?)`', r'<font face="Courier">\1</font>', text)
    text = re.sub(r'^\s*---\s*$', '<hr/>', text, flags=re.MULTILINE)
    return text

def generate_formatted_pdf(text, output_file="reviewer.pdf"):
    doc = SimpleDocTemplate(output_file, pagesize=letter)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=20,
        alignment=1,
        textColor=colors.HexColor("#2E4053")
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=12,
        leading=16,
        textColor=colors.black
    )
    elements = [Paragraph("Study Reviewer", title_style), Spacer(1, 12)]
    formatted_text = markdown_to_pdf(text)
    sections = formatted_text.split('<hr/>')
    for i, sec in enumerate(sections):
        for paragraph in sec.strip().split("\n"):
            paragraph = paragraph.strip()
            if paragraph:
                elements.append(Paragraph(paragraph, body_style))
                elements.append(Spacer(1, 4))
        if i < len(sections) - 1:
            elements.append(HRFlowable(width="100%", thickness=1, color=colors.black))
            elements.append(Spacer(1, 8))
    doc.build(elements)
    return output_file

GUILD_IDS = [1405134005359349760]

for guild_id in GUILD_IDS:
    guild = discord.Object(id=guild_id)

    @bot.tree.command(
        name="chat",
        description="Ask Doc Ron a question, get a response, and be a member of SBAPN Gang.",
        guild=guild
    )
    async def chat(interaction: discord.Interaction, prompt: str):
        await interaction.response.send_message(f"💬 {interaction.user} asked: {prompt}\nDr. Ron is thinking...")
        try:
            response = client_ai.chat.completions.create(
                model="openai/gpt-oss-120b:fireworks-ai",
                messages=[
                    {"role": "system", "content": "Your name is Doc Ron. You are a helpful tutor who answers questions clearly and concisely."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            answer = response.choices[0].message.content
            await interaction.followup.send(answer)
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating response: {str(e)}")

    @bot.tree.command(
        name="review",
        description="Upload a PDF handout to convert it into a reviewer",
        guild=guild
    )
    async def review(interaction: discord.Interaction, file: discord.Attachment):
        if not file.filename.lower().endswith(".pdf"):
            await interaction.response.send_message(
                "⚠️ Please upload a valid **PDF file**.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"📄 Processing your file **{file.filename}** into a reviewer, please wait...",
            ephemeral=True
        )
        try:
            file_path = f"./{file.filename}"
            await file.save(file_path)
            pdf_text = extract_pdf_text(file_path)
            if not pdf_text:
                await interaction.followup.send(
                    "⚠️ Could not extract any text from the PDF.", ephemeral=True
                )
                return
            response = client_ai.chat.completions.create(
                model="openai/gpt-oss-120b:fireworks-ai",
                messages=[
                    {"role": "system", "content": "Your name is Doc Ron, You are a helpful tutor that creates concise and easy-to-read reviewers from study handouts. Do NOT include reasoning or extra commentary. Avoid using '-'."},
                    {"role": "user", "content": f"Convert the following handout into a bullet-point reviewer:\n\n{pdf_text}"}
                ],
                temperature=0
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
            await interaction.followup.send(
                f"❌ Error processing file: {str(e)}", ephemeral=True
            )

@bot.event
async def on_ready():
    for guild_id in GUILD_IDS:
        guild = discord.Object(id=guild_id)
        await bot.tree.sync(guild=guild)
    print(f"✅ Logged in as {bot.user}. Commands synced for guilds: {GUILD_IDS}")

if __name__ == "__main__":
    def start_webserver():
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
    web_thread = threading.Thread(target=start_webserver, daemon=True)
    web_thread.start()
    bot.run(DISCORD_TOKEN)
