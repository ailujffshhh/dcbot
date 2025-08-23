import os
import re
import discord
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI
import PyPDF2
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors


load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")


client_ai = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_API_KEY,
)


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=None, intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")


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


def split_reviewer_text(text):
    lines = []
    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if paragraph:
            sentences = [s.strip() for s in paragraph.split(". ") if s.strip()]
            lines.extend(sentences)
    return lines


def generate_formatted_pdf(text, output_file="reviewer.pdf"):
    doc = SimpleDocTemplate(output_file, pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=20,
        alignment=1,  # center
        textColor=colors.HexColor("#2E4053")
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=12,
        leading=16,
        textColor=colors.black
    )

    elements = []
    elements.append(Paragraph("Study Reviewer", title_style))
    elements.append(Spacer(1, 12))

 
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


# /review command
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

# Run bot
bot.run(DISCORD_TOKEN)
