import re
import os
import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
import PyPDF2

CONVERSATION_FILE = "conversations.json"

def clean_text(text: str) -> str:
    return re.sub(r"[\x00-\x1F\x7F]", "", text)

def split_text(text: str, max_len: int = 2000):
    text = clean_text(text)
    return [text[i:i+max_len] for i in range(0, len(text), max_len)]

def extract_pdf_text(file_path: str) -> str:
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + " "
    return text.strip()

def generate_formatted_pdf(text: str, output_file="reviewer.pdf"):
    doc = SimpleDocTemplate(output_file, pagesize=letter)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=18, spaceAfter=20, alignment=1, textColor=colors.HexColor("#2E4053"))
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=12, leading=16, textColor=colors.black)

    elements = [Paragraph("Study Reviewer", title_style), Spacer(1, 12)]
    sections = text.split("\n---\n")
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

def save_conversations(conversations: dict):
    with open(CONVERSATION_FILE, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)

def load_conversations() -> dict:
    if os.path.exists(CONVERSATION_FILE):
        with open(CONVERSATION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}
