from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle, Polygon
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import datetime

# ── Brand Colors ────────────────────────────────────────────────────────────
NAVY        = colors.HexColor("#1B2A4A")
BLUE        = colors.HexColor("#2563EB")
LIGHT_BLUE  = colors.HexColor("#DBEAFE")
TEAL        = colors.HexColor("#0EA5E9")
GREEN       = colors.HexColor("#16A34A")
LIGHT_GREEN = colors.HexColor("#DCFCE7")
ORANGE      = colors.HexColor("#EA580C")
LIGHT_ORANGE= colors.HexColor("#FFF7ED")
GRAY_DARK   = colors.HexColor("#1F2937")
GRAY_MID    = colors.HexColor("#6B7280")
GRAY_LIGHT  = colors.HexColor("#F3F4F6")
GRAY_LINE   = colors.HexColor("#E5E7EB")
WHITE       = colors.white
YELLOW      = colors.HexColor("#FEF9C3")
PURPLE      = colors.HexColor("#7C3AED")

OUTPUT_FILE = "AUTO_AI_BRD.pdf"
PAGE_W, PAGE_H = letter


# ── Custom Header/Footer Canvas ─────────────────────────────────────────────
class BRDCanvas:
    def __init__(self, filename, **kwargs):
        self.filename = filename

    @staticmethod
    def on_page(canvas_obj, doc):
        canvas_obj.saveState()
        w, h = letter

        # Top bar
        canvas_obj.setFillColor(NAVY)
        canvas_obj.rect(0, h - 0.55 * inch, w, 0.55 * inch, fill=1, stroke=0)

        # Accent stripe
        canvas_obj.setFillColor(BLUE)
        canvas_obj.rect(0, h - 0.65 * inch, w, 0.1 * inch, fill=1, stroke=0)

        # Header text
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont("Helvetica-Bold", 9)
        canvas_obj.drawString(0.5 * inch, h - 0.38 * inch, "AUTO AI — Car Discovery & Outreach Agent")
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawRightString(w - 0.5 * inch, h - 0.38 * inch, "Business Requirements Document v1.0")

        # Bottom bar
        canvas_obj.setFillColor(NAVY)
        canvas_obj.rect(0, 0, w, 0.45 * inch, fill=1, stroke=0)
        canvas_obj.setFillColor(BLUE)
        canvas_obj.rect(0, 0.45 * inch, w, 0.06 * inch, fill=1, stroke=0)

        # Footer text
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.drawString(0.5 * inch, 0.17 * inch, "Confidential — AUTO AI Project  |  Neeraj Nagpal")
        canvas_obj.drawRightString(w - 0.5 * inch, 0.17 * inch, f"Page {doc.page}")

        canvas_obj.restoreState()


# ── Styles ───────────────────────────────────────────────────────────────────
def make_styles():
    s = {}

    s["cover_title"] = ParagraphStyle("cover_title",
        fontName="Helvetica-Bold", fontSize=36, textColor=WHITE,
        leading=44, alignment=TA_CENTER, spaceAfter=8)

    s["cover_sub"] = ParagraphStyle("cover_sub",
        fontName="Helvetica", fontSize=15, textColor=LIGHT_BLUE,
        leading=20, alignment=TA_CENTER, spaceAfter=4)

    s["cover_meta"] = ParagraphStyle("cover_meta",
        fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#93C5FD"),
        leading=16, alignment=TA_CENTER)

    s["section_num"] = ParagraphStyle("section_num",
        fontName="Helvetica-Bold", fontSize=9, textColor=BLUE,
        leading=12, spaceBefore=18, spaceAfter=2)

    s["section_title"] = ParagraphStyle("section_title",
        fontName="Helvetica-Bold", fontSize=16, textColor=NAVY,
        leading=20, spaceBefore=2, spaceAfter=6,
        borderPadding=(0, 0, 4, 0))

    s["subsection"] = ParagraphStyle("subsection",
        fontName="Helvetica-Bold", fontSize=11, textColor=BLUE,
        leading=15, spaceBefore=10, spaceAfter=4)

    s["body"] = ParagraphStyle("body",
        fontName="Helvetica", fontSize=9.5, textColor=GRAY_DARK,
        leading=15, spaceAfter=4)

    s["body_small"] = ParagraphStyle("body_small",
        fontName="Helvetica", fontSize=8.5, textColor=GRAY_DARK,
        leading=13, spaceAfter=2)

    s["bullet"] = ParagraphStyle("bullet",
        fontName="Helvetica", fontSize=9.5, textColor=GRAY_DARK,
        leading=15, leftIndent=16, spaceAfter=3,
        bulletIndent=4, bulletFontName="Helvetica", bulletFontSize=9.5)

    s["code"] = ParagraphStyle("code",
        fontName="Courier", fontSize=8, textColor=NAVY,
        leading=12, leftIndent=12, backColor=GRAY_LIGHT,
        borderColor=GRAY_LINE, borderWidth=0.5, borderPadding=6,
        spaceAfter=6)

    s["callout"] = ParagraphStyle("callout",
        fontName="Helvetica", fontSize=9, textColor=GRAY_DARK,
        leading=13, leftIndent=12, backColor=LIGHT_BLUE,
        borderColor=BLUE, borderWidth=1, borderPadding=8,
        spaceAfter=8)

    s["toc_title"] = ParagraphStyle("toc_title",
        fontName="Helvetica-Bold", fontSize=13, textColor=NAVY,
        leading=18, spaceBefore=4, spaceAfter=10)

    s["toc_item"] = ParagraphStyle("toc_item",
        fontName="Helvetica", fontSize=9.5, textColor=GRAY_DARK,
        leading=16, leftIndent=8)

    s["tag_green"] = ParagraphStyle("tag_green",
        fontName="Helvetica-Bold", fontSize=8, textColor=GREEN,
        leading=11)

    s["tag_orange"] = ParagraphStyle("tag_orange",
        fontName="Helvetica-Bold", fontSize=8, textColor=ORANGE,
        leading=11)

    return s


# ── Helper: Section Header ───────────────────────────────────────────────────
def section_header(num, title, styles):
    return KeepTogether([
        Spacer(1, 0.15 * inch),
        HRFlowable(width="100%", thickness=0.5, color=GRAY_LINE),
        Spacer(1, 0.06 * inch),
        Paragraph(f"SECTION {num}", styles["section_num"]),
        Paragraph(title, styles["section_title"]),
        Spacer(1, 0.04 * inch),
    ])


def bullet(text, styles):
    return Paragraph(f"• &nbsp; {text}", styles["bullet"])


def sub(title, styles):
    return Paragraph(title, styles["subsection"])


def body(text, styles):
    return Paragraph(text, styles["body"])


# ── Colored Table Helper ─────────────────────────────────────────────────────
def styled_table(data, col_widths, header_bg=NAVY, header_fg=WHITE,
                 alt_bg=GRAY_LIGHT, stripe_bg=WHITE):
    style = TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  header_bg),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  header_fg),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  8.5),
        ("BOTTOMPADDING", (0, 0), (-1, 0),  7),
        ("TOPPADDING",    (0, 0), (-1, 0),  7),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8.5),
        ("TOPPADDING",    (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.4, GRAY_LINE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ])
    t = Table(data, colWidths=col_widths)
    t.setStyle(style)
    return t


# ── Cover Page ───────────────────────────────────────────────────────────────
def cover_page(styles):
    elements = []

    # Big colored cover block via table trick
    cover_data = [[
        Paragraph("🚗", ParagraphStyle("em", fontName="Helvetica-Bold",
                  fontSize=52, textColor=WHITE, alignment=TA_CENTER, leading=60)),
    ]]
    cover_table = Table(cover_data, colWidths=[6.5 * inch])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 28),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 20),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
        ("ROUNDEDCORNERS", [8]),
    ]))
    elements.append(Spacer(1, 0.6 * inch))
    elements.append(cover_table)

    title_data = [[Paragraph("AUTO AI", ParagraphStyle("ct",
        fontName="Helvetica-Bold", fontSize=42, textColor=NAVY,
        alignment=TA_CENTER, leading=50))]]
    title_t = Table(title_data, colWidths=[6.5 * inch])
    title_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LIGHT_BLUE),
        ("TOPPADDING",    (0,0),(-1,-1), 14),
        ("BOTTOMPADDING", (0,0),(-1,-1), 14),
    ]))
    elements.append(title_t)

    sub_data = [[Paragraph("Car Discovery &amp; Outreach Agent", ParagraphStyle("cs",
        fontName="Helvetica", fontSize=16, textColor=GRAY_MID,
        alignment=TA_CENTER, leading=22))]]
    sub_t = Table(sub_data, colWidths=[6.5 * inch])
    sub_t.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
    ]))
    elements.append(sub_t)

    elements.append(Spacer(1, 0.3 * inch))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=BLUE))
    elements.append(Spacer(1, 0.2 * inch))

    meta = [
        ["Document Type", "Business Requirements Document (BRD)"],
        ["Version",        "1.0"],
        ["Date",           "April 19, 2026"],
        ["Author",         "Neeraj Nagpal"],
        ["Status",         "Active Development"],
        ["Classification", "Confidential"],
    ]
    meta_table = Table(meta, colWidths=[2.2 * inch, 4.3 * inch])
    meta_table.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",      (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR",     (0, 0), (0, -1), BLUE),
        ("TEXTCOLOR",     (1, 0), (1, -1), GRAY_DARK),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [WHITE, GRAY_LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.4, GRAY_LINE),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Powered by bar
    powered = [["Powered By: LangChain  ·  OpenAI GPT-4o-mini  ·  Marketcheck  ·  Twilio  ·  SendGrid  ·  Streamlit"]]
    powered_t = Table(powered, colWidths=[6.5 * inch])
    powered_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), NAVY),
        ("TEXTCOLOR",     (0,0),(-1,-1), colors.HexColor("#93C5FD")),
        ("FONTNAME",      (0,0),(-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0),(-1,-1), 8.5),
        ("ALIGNMENT",     (0,0),(-1,-1), "CENTER"),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
    ]))
    elements.append(powered_t)
    elements.append(PageBreak())
    return elements


# ── Table of Contents ────────────────────────────────────────────────────────
def toc(styles):
    elements = []
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph("Table of Contents", styles["toc_title"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=BLUE))
    elements.append(Spacer(1, 0.1 * inch))

    sections = [
        ("1",  "Executive Summary"),
        ("2",  "Business Objectives"),
        ("3",  "Scope"),
        ("4",  "Functional Requirements"),
        ("5",  "Non-Functional Requirements"),
        ("6",  "System Architecture"),
        ("7",  "Technology Stack"),
        ("8",  "Data Models"),
        ("9",  "External API Summary"),
        ("10", "Environment Configuration"),
        ("11", "Agent Pipeline Flow"),
        ("12", "Known Limitations"),
        ("13", "Future Enhancements"),
        ("14", "Setup & Run Instructions"),
        ("15", "PR / FAQ — Press Release & Frequently Asked Questions"),
        ("16", "Product Strategy"),
        ("17", "Design Architecture Diagram"),
        ("18", "Detailed Workflow"),
        ("19", "Agent Deep Dive"),
    ]
    toc_data = [["#", "Section Title"]] + [[n, t] for n, t in sections]
    toc_table = Table(toc_data, colWidths=[0.5 * inch, 6.0 * inch])
    toc_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 9.5),
        ("TEXTCOLOR",     (0, 1), (-1, -1), GRAY_DARK),
        ("TEXTCOLOR",     (0, 1), (0, -1), BLUE),
        ("FONTNAME",      (0, 1), (0, -1), "Helvetica-Bold"),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.4, GRAY_LINE),
    ]))
    elements.append(toc_table)
    elements.append(PageBreak())
    return elements


# ── Visual Diagram Helpers ───────────────────────────────────────────────────
def _box(d, x, y, w, h, fill, label, sublabel="", text_color=None):
    tc = text_color or colors.white
    d.add(Rect(x, y, w, h, fillColor=fill, strokeColor=colors.white,
               strokeWidth=1.2, rx=4, ry=4))
    d.add(String(x + w/2, y + h/2 + (5 if sublabel else 0), label,
                 fontName="Helvetica-Bold", fontSize=7.5,
                 fillColor=tc, textAnchor="middle"))
    if sublabel:
        d.add(String(x + w/2, y + h/2 - 7, sublabel,
                     fontName="Helvetica", fontSize=6,
                     fillColor=tc, textAnchor="middle"))


def _arrow(d, x1, y1, x2, y2, color=None):
    c = color or colors.HexColor("#94A3B8")
    d.add(Line(x1, y1, x2, y2, strokeColor=c, strokeWidth=1.2))
    # arrowhead
    dx, dy = x2 - x1, y2 - y1
    import math
    length = math.sqrt(dx*dx + dy*dy) or 1
    ux, uy = dx/length, dy/length
    px, py = -uy, ux
    size = 5
    d.add(Polygon([x2, y2,
                   x2 - ux*size + px*3, y2 - uy*size + py*3,
                   x2 - ux*size - px*3, y2 - uy*size - py*3],
                  fillColor=c, strokeColor=c, strokeWidth=0))


def _legend_box(color, label):
    d = Drawing(100, 22)
    d.add(Rect(2, 4, 14, 14, fillColor=color, strokeColor=color, rx=2, ry=2))
    d.add(String(20, 9, label, fontName="Helvetica", fontSize=7.5,
                 fillColor=colors.HexColor("#1F2937"), textAnchor="start"))
    return d


def _arch_diagram():
    W, H = 6.5 * inch, 4.2 * inch
    d = Drawing(W, H)

    # Background
    d.add(Rect(0, 0, W, H, fillColor=colors.HexColor("#F8FAFC"),
               strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=1))

    bw, bh = 88, 36   # box width/height
    col1 = 10
    col2 = 130
    col3 = 270
    col4 = 390
    col5 = 295

    # Row positions (y from bottom)
    row_user   = H - 55
    row_front  = H - 110
    row_orch   = H - 170
    row_agents = H - 240
    row_models = H - 300
    row_apis   = H - 355
    row_del    = H - 300

    # ── User
    _box(d, W/2 - 44, row_user, 88, 32, NAVY, "👤 User", "Browser", WHITE)

    # Arrow user → frontend
    _arrow(d, W/2, row_user, W/2, row_front + 36)

    # ── Frontend
    _box(d, W/2 - 70, row_front, 140, 36, BLUE, "Streamlit Frontend", "app.py", WHITE)

    # Arrow frontend → orchestrator
    _arrow(d, W/2, row_front, W/2, row_orch + 36)

    # ── Orchestrator
    _box(d, W/2 - 80, row_orch, 160, 36, TEAL, "Orchestrator", "agents/orchestrator.py", WHITE)

    # ── Agents row
    agent_y = row_agents
    agent_configs = [
        (60,  GREEN,  "Search Agent",   "search_agent.py"),
        (230, PURPLE, "Ranking Agent",  "ranking_agent.py"),
        (400, ORANGE, "Outreach Agent", "outreach_agent.py"),
    ]
    orch_cx = W/2
    for ax, acolor, alabel, afile in agent_configs:
        _box(d, ax, agent_y, 105, 36, acolor, alabel, afile, WHITE)
        acx = ax + 52.5
        _arrow(d, orch_cx, row_orch, acx, agent_y + 36)

    # ── Data Models
    _box(d, W/2 - 55, row_models, 110, 32, PURPLE, "Data Models", "models.py (Pydantic)", WHITE)

    # ── External APIs
    api_configs = [
        (15,  NAVY,  "Marketcheck",  "Inventory API"),
        (135, NAVY,  "OpenAI",       "GPT-4o-mini"),
        (255, NAVY,  "SendGrid",     "Email API"),
        (375, NAVY,  "Twilio",       "SMS API"),
    ]
    for ax, acolor, alabel, asub in api_configs:
        _box(d, ax, row_apis, 100, 32, acolor, alabel, asub, WHITE)
        # Arrow from search agent to Marketcheck and OpenAI
        if alabel == "Marketcheck":
            _arrow(d, 112, agent_y, ax + 50, row_apis + 32)
        elif alabel == "OpenAI":
            _arrow(d, 112, agent_y, ax + 50, row_apis + 32)
        elif alabel == "SendGrid":
            _arrow(d, 452, agent_y, ax + 50, row_apis + 32)
        elif alabel == "Twilio":
            _arrow(d, 452, agent_y, ax + 50, row_apis + 32)

    # ── Labels for sections
    label_style = {"fontName": "Helvetica", "fontSize": 6.5,
                   "fillColor": colors.HexColor("#94A3B8"), "textAnchor": "start"}
    d.add(String(10, H - 18, "PRESENTATION LAYER", **label_style))
    d.add(String(10, row_front - 16, "AGENT PIPELINE", **label_style))
    d.add(String(10, row_apis - 16, "EXTERNAL SERVICES", **label_style))

    return d


def _workflow_diagram():
    W, H = 6.5 * inch, 2.8 * inch
    d = Drawing(W, H)
    d.add(Rect(0, 0, W, H, fillColor=colors.HexColor("#F8FAFC"),
               strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=1))

    steps = [
        (BLUE,   "1\nInput"),
        (TEAL,   "2\nOrchestrate"),
        (GREEN,  "3\nNormalize"),
        (GREEN,  "4\nSearch"),
        (PURPLE, "5\nRank"),
        (ORANGE, "6\nGenerate"),
        (NAVY,   "7\nDeliver"),
        (BLUE,   "8\nDisplay"),
    ]
    n = len(steps)
    pad = 14
    bw = (W - pad * 2 - (n - 1) * 8) / n
    bh = 60
    cy = H / 2

    for i, (color, label) in enumerate(steps):
        x = pad + i * (bw + 8)
        y = cy - bh / 2
        parts = label.split("\n")
        d.add(Rect(x, y, bw, bh, fillColor=color, strokeColor=WHITE,
                   strokeWidth=1, rx=4, ry=4))
        d.add(String(x + bw/2, y + bh/2 + 6, parts[0],
                     fontName="Helvetica-Bold", fontSize=11,
                     fillColor=WHITE, textAnchor="middle"))
        d.add(String(x + bw/2, y + bh/2 - 8, parts[1],
                     fontName="Helvetica", fontSize=7,
                     fillColor=WHITE, textAnchor="middle"))
        if i < n - 1:
            nx = x + bw + 8
            _arrow(d, x + bw, cy, nx, cy, color=colors.HexColor("#94A3B8"))

    return d


# ── Build PDF ────────────────────────────────────────────────────────────────
def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_FILE,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.75 * inch,
        title="AUTO AI — Business Requirements Document",
        author="Neeraj Nagpal",
        subject="BRD v1.0",
    )

    styles = make_styles()
    elems = []

    # ── Cover ──────────────────────────────────────────────────────────────
    elems += cover_page(styles)

    # ── TOC ────────────────────────────────────────────────────────────────
    elems += toc(styles)

    # ── Section 1: Executive Summary ───────────────────────────────────────
    elems.append(section_header("1", "Executive Summary", styles))
    elems.append(body(
        "AUTO AI is an AI-powered car discovery and outreach platform built to automate the "
        "end-to-end process of finding, ranking, and communicating personalized used car listings "
        "to buyers. The system leverages a multi-agent pipeline — combining real-time marketplace "
        "inventory data, AI-based scoring, and automated email/SMS delivery — to eliminate the "
        "manual effort of browsing multiple car listing sites.", styles))
    elems.append(Spacer(1, 0.08 * inch))

    highlight = Table([[Paragraph(
        "AUTO AI reduces the car buying research process from hours to seconds by combining "
        "real-time dealer inventory data with AI-driven personalization and automated outreach.",
        ParagraphStyle("hl", fontName="Helvetica-Bold", fontSize=9.5, textColor=NAVY, leading=15)
    )]], colWidths=[6.5 * inch])
    highlight.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LIGHT_BLUE),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("RIGHTPADDING",  (0,0),(-1,-1), 14),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LINEAFTER",     (0,0),(0,-1),  3, BLUE),
    ]))
    elems.append(highlight)

    # ── Section 2: Business Objectives ────────────────────────────────────
    elems.append(section_header("2", "Business Objectives", styles))
    objectives = [
        ["#", "Objective", "Priority"],
        ["1", "Automate used car discovery based on buyer preferences", "High"],
        ["2", "Surface real, live inventory from dealer websites via Marketcheck API", "High"],
        ["3", "Rank listings by relevance using a multi-factor scoring algorithm", "High"],
        ["4", "Deliver personalized results to buyers via Email and/or SMS", "Medium"],
        ["5", "Provide graceful fallback to AI-simulated listings when live data is unavailable", "Low"],
    ]
    t = Table(objectives, colWidths=[0.4*inch, 4.6*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), NAVY),
        ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 8.5),
        ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,1),(-1,-1), 8.5),
        ("TEXTCOLOR",     (0,1),(0,-1), BLUE),
        ("FONTNAME",      (0,1),(0,-1), "Helvetica-Bold"),
        ("BACKGROUND",    (2,1),(2,3), LIGHT_GREEN),
        ("TEXTCOLOR",     (2,1),(2,3), GREEN),
        ("FONTNAME",      (2,1),(2,-1), "Helvetica-Bold"),
        ("BACKGROUND",    (2,4),(2,4), LIGHT_BLUE),
        ("TEXTCOLOR",     (2,4),(2,4), BLUE),
        ("BACKGROUND",    (2,5),(2,5), YELLOW),
        ("TEXTCOLOR",     (2,5),(2,5), ORANGE),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GRAY_LIGHT]),
        ("GRID",          (0,0),(-1,-1), 0.4, GRAY_LINE),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    elems.append(t)

    # ── Section 3: Scope ───────────────────────────────────────────────────
    elems.append(section_header("3", "Scope", styles))
    elems.append(sub("In Scope", styles))
    for item in [
        "Web-based user interface for entering car preferences (Streamlit)",
        "Real-time car inventory search via Marketcheck API",
        "AI-powered make/model name normalization (handles user misspellings)",
        "Multi-factor listing ranking engine (price, mileage, color match)",
        "Automated email delivery via SendGrid with GPT-generated content",
        "Automated SMS delivery via Twilio with GPT-generated content",
        "Graceful fallback to GPT-simulated listings if live API is unavailable",
    ]:
        elems.append(bullet(item, styles))

    elems.append(Spacer(1, 0.08 * inch))
    elems.append(sub("Out of Scope", styles))
    for item in [
        "User account management / authentication / login",
        "Payment or financing integration",
        "Vehicle history reports (Carfax, AutoCheck)",
        "Direct dealer contact or lead form submission",
        "Mobile native app (iOS / Android)",
        "AutoTrader and CarGurus direct API (no public API available)",
    ]:
        elems.append(bullet(item, styles))

    # ── Section 4: Functional Requirements ────────────────────────────────
    elems.append(section_header("4", "Functional Requirements", styles))
    elems.append(sub("4.1  User Input — Search Preferences", styles))

    input_data = [
        ["Field", "Type", "Required", "Notes"],
        ["Make",           "Text",     "Yes", "Auto-corrected via GPT (handles misspellings)"],
        ["Model",          "Text",     "Yes", "Auto-corrected via GPT"],
        ["Min Price ($)",  "Number",   "Yes", "USD — must be less than Max Price"],
        ["Max Price ($)",  "Number",   "Yes", "USD"],
        ["Exterior Color", "Dropdown", "No",  "Any, White, Black, Silver, Gray, Red, Blue, Green, Other"],
        ["Interior Color", "Dropdown", "No",  "Any, Black, Beige, Gray, Brown, White, Red, Other"],
        ["Max Mileage",    "Number",   "No",  "Odometer cap in miles"],
        ["Location",       "Text",     "Yes", "ZIP code or City, State format"],
        ["Search Radius",  "Slider",   "Yes", "10 – 200 miles"],
        ["Email Delivery", "Checkbox", "No",  "Requires valid email address"],
        ["SMS Delivery",   "Checkbox", "No",  "Requires valid phone number (+1 format)"],
    ]
    elems.append(styled_table(input_data,
        [1.5*inch, 1.0*inch, 0.9*inch, 3.1*inch]))
    elems.append(Spacer(1, 0.1 * inch))

    elems.append(sub("4.2  Search Agent", styles))
    for item in [
        "Accepts user preferences as structured Pydantic model (CarPreferences)",
        "Normalizes make/model spelling using GPT-4o-mini before API call",
        "Queries Marketcheck API (GET /v2/search/car/active) with full filter set",
        "Parses response: title, price, mileage, year, colors, dealer, location, URL, source domain",
        "Falls back to GPT-simulated listings if Marketcheck key is absent or API fails",
        "Surfaces a warning banner in the UI when fallback mode is triggered",
    ]:
        elems.append(bullet(item, styles))

    elems.append(Spacer(1, 0.08 * inch))
    elems.append(sub("4.3  Ranking Agent — Scoring Formula", styles))
    scoring_data = [
        ["Factor",              "Max Points", "Scoring Logic"],
        ["Price Proximity",     "40 pts",     "Closer to midpoint of budget range = higher score"],
        ["Mileage",             "30 pts",     "Lower mileage relative to max = higher score"],
        ["Exterior Color Match","15 pts",     "Substring match between preference and listing"],
        ["Interior Color Match","15 pts",     "Substring match between preference and listing"],
        ["TOTAL",               "100 pts",    "Top 5 listings returned, sorted descending"],
    ]
    t = Table(scoring_data, colWidths=[2.0*inch, 1.1*inch, 3.4*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), BLUE),
        ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("BACKGROUND",    (0,-1),(-1,-1), NAVY),
        ("TEXTCOLOR",     (0,-1),(-1,-1), WHITE),
        ("FONTNAME",      (0,-1),(-1,-1), "Helvetica-Bold"),
        ("FONTNAME",      (0,1),(-1,-2), "Helvetica"),
        ("FONTSIZE",      (0,0),(-1,-1), 8.5),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-2), [WHITE, GRAY_LIGHT]),
        ("GRID",          (0,0),(-1,-1), 0.4, GRAY_LINE),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 0.08 * inch))

    elems.append(sub("4.4  Outreach Agent", styles))
    outreach_data = [
        ["Channel", "Generator",       "Delivery Service", "Content"],
        ["Email",   "GPT-4o-mini",     "SendGrid API",     "Personalized HTML email with listing cards, prices, links"],
        ["SMS",     "GPT-4o-mini",     "Twilio API",       "Concise summary ≤300 chars — top 3 cars with price & mileage"],
    ]
    elems.append(styled_table(outreach_data,
        [0.8*inch, 1.2*inch, 1.5*inch, 3.0*inch]))

    # ── Section 5: Non-Functional Requirements ─────────────────────────────
    elems.append(section_header("5", "Non-Functional Requirements", styles))
    nfr_data = [
        ["Category",      "Requirement"],
        ["Performance",   "Marketcheck API call must complete within 15 seconds"],
        ["Availability",  "Runs locally via Streamlit; no uptime SLA currently"],
        ["Security",      "API keys stored in .env file — never committed to version control"],
        ["Scalability",   "Stateless pipeline; each search is fully independent"],
        ["Resilience",    "Full GPT fallback if Marketcheck API fails or returns 0 results"],
        ["Compatibility", "Python 3.9+ on macOS / Linux"],
    ]
    elems.append(styled_table(nfr_data, [1.6*inch, 4.9*inch]))

    # ── Section 6: System Architecture ────────────────────────────────────
    elems.append(section_header("6", "System Architecture", styles))

    arch_rows = [
        ["LAYER", "COMPONENT", "TECHNOLOGY", "ROLE"],
        ["Frontend",    "app.py",               "Streamlit",          "User interface — preferences sidebar & results grid"],
        ["Orchestration","orchestrator.py",      "Python",             "Coordinates Search → Rank → Outreach pipeline"],
        ["Agent",       "search_agent.py",       "LangChain + Requests","Make/model normalization, Marketcheck query, GPT fallback"],
        ["Agent",       "ranking_agent.py",      "Python",             "Multi-factor scoring and top-5 selection"],
        ["Agent",       "outreach_agent.py",     "LangChain + APIs",   "Email/SMS content generation and delivery"],
        ["Data Models", "models.py",             "Pydantic v2",        "CarPreferences and CarListing schema validation"],
        ["Config",      "config.py",             "python-dotenv",      "Environment variable management"],
        ["External API","Marketcheck",           "REST API v2",        "Real-time used car inventory from dealer websites"],
        ["External API","OpenAI GPT-4o-mini",    "OpenAI SDK",         "Normalization, email, SMS generation, fallback listings"],
        ["External API","SendGrid",              "SendGrid SDK",       "Transactional HTML email delivery"],
        ["External API","Twilio",               "Twilio SDK",         "SMS message delivery"],
    ]
    t = Table(arch_rows, colWidths=[1.0*inch, 1.5*inch, 1.4*inch, 2.6*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), NAVY),
        ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 8),
        ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,1),(-1,-1), 8),
        ("TEXTCOLOR",     (0,1),(0,1), BLUE),   # Frontend
        ("TEXTCOLOR",     (0,2),(0,2), PURPLE),  # Orchestration
        ("TEXTCOLOR",     (0,3),(0,5), GREEN),   # Agents
        ("TEXTCOLOR",     (0,6),(0,7), GRAY_MID),# Config
        ("TEXTCOLOR",     (0,8),(0,-1), ORANGE), # External
        ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GRAY_LIGHT]),
        ("GRID",          (0,0),(-1,-1), 0.4, GRAY_LINE),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 0.1*inch))

    # Pipeline flow diagram (text-based)
    elems.append(sub("Pipeline Flow", styles))
    pipeline_steps = [
        ("1", BLUE,   "User Input",      "Enter preferences → click Find Cars"),
        ("2", TEAL,   "Search Agent",    "Normalize make/model → Query Marketcheck → Parse listings"),
        ("3", GREEN,  "Ranking Agent",   "Score by price + mileage + color → Return top 5"),
        ("4", PURPLE, "Outreach Agent",  "Generate email/SMS via GPT → Deliver via SendGrid/Twilio"),
        ("5", NAVY,   "Display Results", "Show listing cards with source badge, score, and live links"),
    ]
    for num, color, title, desc in pipeline_steps:
        row = Table([[
            Paragraph(num, ParagraphStyle("pn", fontName="Helvetica-Bold",
                fontSize=12, textColor=WHITE, alignment=TA_CENTER, leading=16)),
            Paragraph(f"<b>{title}</b><br/><font size='8' color='#6B7280'>{desc}</font>",
                ParagraphStyle("pd", fontName="Helvetica", fontSize=9,
                    textColor=GRAY_DARK, leading=14))
        ]], colWidths=[0.35*inch, 6.15*inch])
        row.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(0,0), color),
            ("TOPPADDING",    (0,0),(-1,-1), 7),
            ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ("LEFTPADDING",   (0,0),(-1,-1), 10),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("LINEBELOW",     (0,0),(-1,-1), 0.5, GRAY_LINE),
        ]))
        elems.append(row)

    # ── Section 7: Technology Stack ────────────────────────────────────────
    elems.append(section_header("7", "Technology Stack", styles))
    tech_data = [
        ["Layer",          "Technology",        "Version",  "Purpose"],
        ["Frontend",       "Streamlit",         "≥1.32.0",  "Web UI"],
        ["Agent Framework","LangChain",         "≥0.2.0",   "LLM chain orchestration"],
        ["LLM",            "OpenAI GPT-4o-mini","Latest",   "Normalization, content generation, fallback"],
        ["LLM Client",     "langchain-openai",  "≥0.1.0",   "OpenAI API integration"],
        ["Data Validation","Pydantic",          "≥2.0.0",   "CarPreferences & CarListing models"],
        ["Car Inventory",  "Marketcheck API",   "v2",        "Real-time used car listings"],
        ["Email Delivery", "SendGrid",          "≥6.10.0",  "Transactional email"],
        ["SMS Delivery",   "Twilio",            "≥9.0.0",   "SMS messaging"],
        ["HTTP Client",    "Requests",          "≥2.31.0",  "Marketcheck API calls"],
        ["Config",         "python-dotenv",     "≥1.0.0",   "Environment variable management"],
        ["Language",       "Python",            "3.9+",     "Runtime"],
    ]
    elems.append(styled_table(tech_data,
        [1.4*inch, 1.6*inch, 0.9*inch, 2.6*inch]))

    # ── Section 8: Data Models ─────────────────────────────────────────────
    elems.append(section_header("8", "Data Models", styles))
    elems.append(sub("CarPreferences", styles))
    prefs_data = [
        ["Field",           "Type",   "Required", "Description"],
        ["make",            "str",    "Yes",      "Vehicle make (e.g. Porsche) — auto-corrected"],
        ["model",           "str",    "Yes",      "Vehicle model (e.g. 911) — auto-corrected"],
        ["price_min",       "int",    "Yes",      "Minimum budget in USD"],
        ["price_max",       "int",    "Yes",      "Maximum budget in USD"],
        ["exterior_color",  "str?",   "No",       "Preferred exterior color"],
        ["interior_color",  "str?",   "No",       "Preferred interior color"],
        ["max_mileage",     "int?",   "No",       "Maximum odometer reading in miles"],
        ["location",        "str",    "Yes",      "ZIP code or City, State"],
        ["radius_miles",    "int",    "Yes",      "Search radius in miles"],
        ["delivery_email",  "bool",   "Default T","Send results via email"],
        ["delivery_sms",    "bool",   "Default F","Send results via SMS"],
        ["user_email",      "str?",   "No",       "Recipient email address"],
        ["user_phone",      "str?",   "No",       "Recipient phone number"],
    ]
    elems.append(styled_table(prefs_data,
        [1.4*inch, 0.7*inch, 0.9*inch, 3.5*inch]))
    elems.append(Spacer(1, 0.1*inch))

    elems.append(sub("CarListing", styles))
    listing_data = [
        ["Field",           "Type",   "Description"],
        ["title",           "str",    "Listing headline (e.g. 2019 Porsche 911 Turbo S)"],
        ["price",           "int",    "Listed price in USD"],
        ["mileage",         "int",    "Odometer reading in miles"],
        ["year",            "int",    "Model year"],
        ["exterior_color",  "str?",   "Exterior color"],
        ["interior_color",  "str?",   "Interior color"],
        ["dealer_name",     "str?",   "Selling dealer name"],
        ["location",        "str?",   "Dealer city and state"],
        ["listing_url",     "str?",   "Direct link to the listing page"],
        ["match_score",     "float?", "Computed relevance score (0–100)"],
        ["source",          "str?",   "Origin domain (e.g. dealer website)"],
    ]
    elems.append(styled_table(listing_data,
        [1.4*inch, 0.7*inch, 4.4*inch]))

    # ── Section 9: External API Summary ───────────────────────────────────
    elems.append(section_header("9", "External API Summary", styles))
    api_data = [
        ["API",           "Status",  "Base URL",                         "Auth Method",          "Primary Use"],
        ["Marketcheck",   "Active",  "api.marketcheck.com/v2",           "api_key param",        "Car inventory search"],
        ["OpenAI",        "Active",  "api.openai.com/v1",                "Bearer token",         "LLM — normalize, generate, fallback"],
        ["SendGrid",      "Active",  "api.sendgrid.com/v3",              "API key header",       "Email delivery"],
        ["Twilio",        "Active",  "api.twilio.com",                   "AccountSID + Token",   "SMS delivery"],
        ["AutoDev",       "Reserved","api.auto.dev",                     "Bearer token",         "Future VIN enrichment"],
        ["AutoTrader",    "N/A",     "No public API",                    "Enterprise only",      "Not integrated"],
        ["CarGurus",      "N/A",     "No inventory search endpoint",     "Contact required",     "Not integrated"],
        ["Cars.com",      "N/A",     "Internal API only",                "Not available",        "Not integrated"],
    ]
    t = Table(api_data, colWidths=[1.0*inch, 0.7*inch, 1.7*inch, 1.3*inch, 1.8*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), NAVY),
        ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 7.5),
        ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,1),(-1,-1), 7.5),
        ("BACKGROUND",    (1,1),(1,4), LIGHT_GREEN),
        ("TEXTCOLOR",     (1,1),(1,4), GREEN),
        ("FONTNAME",      (1,1),(1,4), "Helvetica-Bold"),
        ("BACKGROUND",    (1,5),(1,5), LIGHT_BLUE),
        ("TEXTCOLOR",     (1,5),(1,5), BLUE),
        ("FONTNAME",      (1,5),(1,5), "Helvetica-Bold"),
        ("BACKGROUND",    (1,6),(1,-1), LIGHT_ORANGE),
        ("TEXTCOLOR",     (1,6),(1,-1), ORANGE),
        ("FONTNAME",      (1,6),(1,-1), "Helvetica-Bold"),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GRAY_LIGHT]),
        ("GRID",          (0,0),(-1,-1), 0.4, GRAY_LINE),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    elems.append(t)

    # ── Section 10: Environment Configuration ─────────────────────────────
    elems.append(section_header("10", "Environment Configuration", styles))
    env_data = [
        ["Variable",              "Required",    "Description"],
        ["OPENAI_API_KEY",        "Yes",         "OpenAI API key for GPT-4o-mini"],
        ["MARKETCHECK_API_KEY",   "Recommended", "Marketcheck key — enables real listings"],
        ["AUTODEV_API_KEY",       "No",          "AutoDev key — reserved for future VIN enrichment"],
        ["TWILIO_ACCOUNT_SID",    "If SMS",      "Twilio account SID"],
        ["TWILIO_AUTH_TOKEN",     "If SMS",      "Twilio auth token"],
        ["TWILIO_PHONE_NUMBER",   "If SMS",      "Twilio outbound phone number"],
        ["SENDGRID_API_KEY",      "If Email",    "SendGrid API key"],
        ["SENDGRID_FROM_EMAIL",   "If Email",    "Verified SendGrid sender email"],
    ]
    t = Table(env_data, colWidths=[2.2*inch, 1.2*inch, 3.1*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), NAVY),
        ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 8.5),
        ("FONTNAME",      (0,1),(-1,-1), "Courier"),
        ("FONTSIZE",      (0,1),(-1,-1), 8),
        ("TEXTCOLOR",     (0,1),(0,-1), NAVY),
        ("BACKGROUND",    (1,1),(1,1), LIGHT_GREEN),
        ("TEXTCOLOR",     (1,1),(1,1), GREEN),
        ("FONTNAME",      (1,1),(1,1), "Helvetica-Bold"),
        ("BACKGROUND",    (1,2),(1,2), LIGHT_BLUE),
        ("TEXTCOLOR",     (1,2),(1,2), BLUE),
        ("FONTNAME",      (1,2),(1,2), "Helvetica-Bold"),
        ("FONTNAME",      (1,3),(-1,-1), "Helvetica"),
        ("FONTSIZE",      (1,1),(-1,-1), 8.5),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GRAY_LIGHT]),
        ("GRID",          (0,0),(-1,-1), 0.4, GRAY_LINE),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    elems.append(t)

    # ── Section 11: Agent Pipeline Flow ───────────────────────────────────
    elems.append(section_header("11", "Agent Pipeline Flow", styles))
    flow_data = [
        ["Step", "Agent / Component",  "Input",                   "Output",                     "Fallback"],
        ["1",    "Input Validation",   "User form data",          "CarPreferences model",        "Validation error shown"],
        ["2",    "Search Agent",       "CarPreferences",          "List of CarListing objects",  "GPT-simulated listings"],
        ["3",    "Ranking Agent",      "List[CarListing]",        "Top 5 scored listings",       "None needed"],
        ["4",    "Outreach Agent",     "Top 5 + user contacts",   "Email/SMS delivery result",   "Error shown in UI"],
        ["5",    "Display",            "Ranked listings + status","Result cards + badges",        "Warning banner"],
    ]
    elems.append(styled_table(flow_data,
        [0.4*inch, 1.3*inch, 1.4*inch, 1.8*inch, 1.6*inch]))

    # ── Section 12: Known Limitations ─────────────────────────────────────
    elems.append(section_header("12", "Known Limitations", styles))
    lim_data = [
        ["Limitation",                    "Detail"],
        ["AutoTrader / CarGurus data",    "Not available — both block third-party scraping; no public APIs exist"],
        ["Marketcheck price filter",      "API may return listings slightly outside price range; ranking agent re-prioritizes"],
        ["Free tier API limits",          "Marketcheck free tier has monthly call volume limits"],
        ["Location input",                "Works best with ZIP code; city/state parsing may be less precise"],
        ["No persistent storage",         "Search results are not saved between sessions"],
        ["Python 3.9 compatibility",      "str | None union syntax not supported — uses Optional[] instead"],
    ]
    t = Table(lim_data, colWidths=[2.2*inch, 4.3*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), ORANGE),
        ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 8.5),
        ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,1),(-1,-1), 8.5),
        ("FONTNAME",      (0,1),(0,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",     (0,1),(0,-1), ORANGE),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_ORANGE]),
        ("GRID",          (0,0),(-1,-1), 0.4, GRAY_LINE),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    elems.append(t)

    # ── Section 13: Future Enhancements ───────────────────────────────────
    elems.append(section_header("13", "Future Enhancements", styles))
    future_data = [
        ["Priority", "Enhancement",                                           "Benefit"],
        ["High",     "VIN-based vehicle history enrichment via AutoDev API",  "Reliability data per listing"],
        ["High",     "Save search history and results to SQLite database",    "Persistent user sessions"],
        ["Medium",   "Display photo thumbnails from Marketcheck media links", "Richer listing cards"],
        ["Medium",   "User accounts with saved preferences and price alerts", "Repeat engagement"],
        ["Medium",   "Price trend analysis vs. market value",                 "Buyer negotiation insight"],
        ["Low",      "Deploy to cloud (Streamlit Cloud / AWS / GCP)",         "Public accessibility"],
        ["Low",      "Mobile-responsive UI improvements",                     "Better mobile experience"],
        ["Low",      "Support for new/CPO inventory",                         "Broader inventory coverage"],
    ]
    t = Table(future_data, colWidths=[0.8*inch, 3.4*inch, 2.3*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), NAVY),
        ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 8.5),
        ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,1),(-1,-1), 8.5),
        ("BACKGROUND",    (0,1),(0,2), LIGHT_GREEN),
        ("TEXTCOLOR",     (0,1),(0,2), GREEN),
        ("FONTNAME",      (0,1),(0,2), "Helvetica-Bold"),
        ("BACKGROUND",    (0,3),(0,5), LIGHT_BLUE),
        ("TEXTCOLOR",     (0,3),(0,5), BLUE),
        ("FONTNAME",      (0,3),(0,5), "Helvetica-Bold"),
        ("BACKGROUND",    (0,6),(0,-1), YELLOW),
        ("TEXTCOLOR",     (0,6),(0,-1), ORANGE),
        ("FONTNAME",      (0,6),(0,-1), "Helvetica-Bold"),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GRAY_LIGHT]),
        ("GRID",          (0,0),(-1,-1), 0.4, GRAY_LINE),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    elems.append(t)

    # ── Section 14: Setup & Run Instructions ──────────────────────────────
    elems.append(section_header("14", "Setup & Run Instructions", styles))
    elems.append(sub("Prerequisites", styles))
    for item in ["Python 3.9+", "OpenAI API key (required)", "Marketcheck API key (recommended for real listings)"]:
        elems.append(bullet(item, styles))

    elems.append(Spacer(1, 0.08*inch))
    elems.append(sub("Installation", styles))
    code_lines = [
        "git clone <repo-url>",
        "cd AUTO_AI",
        "python3 -m venv venv",
        "source venv/bin/activate",
        "pip install -r requirements.txt",
        "cp .env.example .env",
        "# Edit .env and add your API keys",
    ]
    code_block = Table([[Paragraph(
        "<br/>".join(f'<font color="#2563EB">{l}</font>' if l.startswith("#") else l
                     for l in code_lines),
        ParagraphStyle("code2", fontName="Courier", fontSize=8.5,
            textColor=NAVY, leading=14, backColor=GRAY_LIGHT)
    )]], colWidths=[6.5*inch])
    code_block.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), GRAY_LIGHT),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("LINEAFTER",     (0,0),(0,-1),  3, BLUE),
        ("BOX",           (0,0),(-1,-1), 0.5, GRAY_LINE),
    ]))
    elems.append(code_block)
    elems.append(Spacer(1, 0.08*inch))

    elems.append(sub("Running the App", styles))
    run_block = Table([[Paragraph(
        "streamlit run app.py<br/>"
        '<font color="#6B7280"># Opens automatically at http://localhost:8501</font>',
        ParagraphStyle("run", fontName="Courier", fontSize=9,
            textColor=NAVY, leading=15))
    ]], colWidths=[6.5*inch])
    run_block.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LIGHT_BLUE),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("LINEAFTER",     (0,0),(0,-1),  3, BLUE),
        ("BOX",           (0,0),(-1,-1), 0.5, BLUE),
    ]))
    elems.append(run_block)

    # ── Section 15: PR / FAQ ───────────────────────────────────────────────
    elems.append(PageBreak())
    elems.append(section_header("15", "PR / FAQ — Press Release & Frequently Asked Questions", styles))

    elems.append(sub("Press Release", styles))
    pr_header = Table([[Paragraph(
        "FOR IMMEDIATE RELEASE",
        ParagraphStyle("pr_tag", fontName="Helvetica-Bold", fontSize=8,
            textColor=ORANGE, leading=12, alignment=TA_LEFT))
    ]], colWidths=[6.5*inch])
    pr_header.setStyle(TableStyle([
        ("TOPPADDING", (0,0),(-1,-1), 4), ("BOTTOMPADDING", (0,0),(-1,-1), 4)]))
    elems.append(pr_header)
    elems.append(Spacer(1, 0.06*inch))

    pr_title = Table([[Paragraph(
        "AUTO AI Eliminates the Pain of Car Shopping — AI Agent Finds, Ranks, and Delivers Your Perfect Car in Seconds",
        ParagraphStyle("prt", fontName="Helvetica-Bold", fontSize=13,
            textColor=NAVY, leading=18, alignment=TA_LEFT))
    ]], colWidths=[6.5*inch])
    pr_title.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LIGHT_BLUE),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LINEAFTER",     (0,0),(0,-1), 4, BLUE),
    ]))
    elems.append(pr_title)
    elems.append(Spacer(1, 0.1*inch))

    pr_paras = [
        ("Anaheim, CA — April 19, 2026 —",
         "Today, AUTO AI launches an intelligent car discovery platform that automates the "
         "entire used car search process from start to finish. Powered by LangChain, OpenAI GPT-4o-mini, "
         "and the Marketcheck inventory API, AUTO AI finds real dealer listings, scores them against "
         "your exact preferences, and delivers personalized results directly to your inbox or phone — "
         "all in under 30 seconds."),
        ("The Problem:",
         "Buying a used car today means spending hours on AutoTrader, CarGurus, and dealer websites — "
         "manually filtering, comparing, and still not knowing if you found the best deal. The process "
         "is fragmented, time-consuming, and frustrating."),
        ("The Solution:",
         "AUTO AI acts as your personal car-buying agent. Enter your make, model, budget, color, "
         "mileage tolerance, and location. The AI pipeline takes over — searching real inventory, "
         "ranking every listing with a transparent 100-point score, and sending you a curated shortlist "
         "via email or SMS. Every 'View Listing' link goes directly to the dealer's page."),
        ("Built for:",
         "Car buyers who value their time, automotive dealerships building buyer engagement tools, "
         "and developers exploring multi-agent AI pipelines for real-world applications."),
    ]
    for label, text in pr_paras:
        elems.append(body(f"<b>{label}</b> {text}", styles))
        elems.append(Spacer(1, 0.06*inch))

    elems.append(Spacer(1, 0.1*inch))
    elems.append(sub("Frequently Asked Questions (FAQ)", styles))

    faqs = [
        ("Q: Is the car data real or simulated?",
         "A: When a Marketcheck API key is configured, all listings are real and sourced directly "
         "from dealer websites. Without a key, the system falls back to GPT-simulated listings "
         "clearly marked with an 'AI Simulated' orange badge."),
        ("Q: Why don't I see AutoTrader or CarGurus listings?",
         "A: Neither platform offers a public API. AutoTrader requires an enterprise partnership "
         "(typically $1,000+/month). CarGurus has no inventory search endpoint. Marketcheck is the "
         "best publicly available aggregator that covers real dealer inventory."),
        ("Q: How accurate is the match score?",
         "A: The score is transparent and rule-based: 40pts for price fit, 30pts for mileage, "
         "15pts each for exterior and interior color. It is not an ML model — it is deterministic "
         "and fully auditable."),
        ("Q: Can I use this without Twilio or SendGrid?",
         "A: Yes. Both are optional. If you don't configure them, results are still displayed in "
         "the browser UI. Email and SMS are only sent when the keys are present and the user "
         "opts in."),
        ("Q: What happens if the Marketcheck API fails?",
         "A: The system automatically falls back to GPT-simulated listings and shows a yellow "
         "warning banner in the UI explaining the fallback. No error is thrown to the user."),
        ("Q: Can the app handle misspelled car makes?",
         "A: Yes. A GPT-4o-mini normalization step corrects make/model spelling before "
         "hitting the Marketcheck API — so 'porche 911' becomes 'Porsche 911' automatically."),
        ("Q: Is my data stored anywhere?",
         "A: No. The application is stateless. No search history, preferences, or results are "
         "persisted between sessions. All data exists only in memory during a single session."),
    ]
    for q, a in faqs:
        q_block = Table([[Paragraph(q, ParagraphStyle("fq",
            fontName="Helvetica-Bold", fontSize=9, textColor=NAVY, leading=13))
        ]], colWidths=[6.5*inch])
        q_block.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), LIGHT_BLUE),
            ("LEFTPADDING",   (0,0),(-1,-1), 10),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LINEAFTER",     (0,0),(0,-1), 3, BLUE),
        ]))
        a_block = Table([[Paragraph(a, ParagraphStyle("fa",
            fontName="Helvetica", fontSize=9, textColor=GRAY_DARK, leading=13))
        ]], colWidths=[6.5*inch])
        a_block.setStyle(TableStyle([
            ("LEFTPADDING",   (0,0),(-1,-1), 10),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LINEAFTER",     (0,0),(0,-1), 3, GRAY_LINE),
        ]))
        elems.append(q_block)
        elems.append(a_block)
        elems.append(Spacer(1, 0.06*inch))

    # ── Section 16: Product Strategy ──────────────────────────────────────
    elems.append(PageBreak())
    elems.append(section_header("16", "Product Strategy", styles))

    elems.append(sub("Vision", styles))
    vision_block = Table([[Paragraph(
        "To become the go-to AI-powered car discovery layer — making personalized, "
        "real-time inventory search available to any buyer, dealer, or platform through "
        "a simple, intelligent agent pipeline.",
        ParagraphStyle("vis", fontName="Helvetica-Bold", fontSize=10,
            textColor=NAVY, leading=16, alignment=TA_CENTER))
    ]], colWidths=[6.5*inch])
    vision_block.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), NAVY),
        ("TEXTCOLOR",     (0,0),(-1,-1), WHITE),
        ("TOPPADDING",    (0,0),(-1,-1), 14),
        ("BOTTOMPADDING", (0,0),(-1,-1), 14),
        ("LEFTPADDING",   (0,0),(-1,-1), 20),
        ("RIGHTPADDING",  (0,0),(-1,-1), 20),
    ]))
    elems.append(vision_block)
    elems.append(Spacer(1, 0.1*inch))

    elems.append(sub("Strategic Pillars", styles))
    pillars = [
        ("Real Data First",     BLUE,   "Connect to live dealer inventory via Marketcheck. "
                                         "AI simulation is a fallback, never the default goal."),
        ("Transparency",        GREEN,  "Every match score is explainable — buyers see exactly "
                                         "why a car ranked #1 vs #5."),
        ("Zero Friction UX",    TEAL,   "One form, one click. The agent pipeline handles all "
                                         "complexity invisibly behind the scenes."),
        ("Omnichannel Delivery",PURPLE, "Results reach buyers where they are — browser, email, "
                                         "or SMS — without requiring an account or login."),
        ("Extensible by Design",ORANGE, "New data sources (VIN history, photos, pricing trends) "
                                         "can plug in as additional agents without rearchitecting."),
    ]
    for title, color, desc in pillars:
        row = Table([[
            Paragraph(title, ParagraphStyle("pt", fontName="Helvetica-Bold",
                fontSize=9, textColor=WHITE, leading=13, alignment=TA_CENTER)),
            Paragraph(desc, ParagraphStyle("pd2", fontName="Helvetica",
                fontSize=9, textColor=GRAY_DARK, leading=13))
        ]], colWidths=[1.4*inch, 5.1*inch])
        row.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(0,0), color),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("LEFTPADDING",   (0,0),(-1,-1), 10),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("LINEBELOW",     (0,0),(-1,-1), 0.5, GRAY_LINE),
        ]))
        elems.append(row)
    elems.append(Spacer(1, 0.1*inch))

    elems.append(sub("Competitive Positioning", styles))
    comp_data = [
        ["Capability",              "AUTO AI", "AutoTrader", "CarGurus", "Manual Search"],
        ["Real inventory data",     "Yes",     "Yes",        "Yes",      "Yes"],
        ["Public API access",       "Yes",     "No",         "No",       "N/A"],
        ["AI-based ranking",        "Yes",     "No",         "Partial",  "No"],
        ["Automated email/SMS",     "Yes",     "No",         "No",       "No"],
        ["Make/model autocorrect",  "Yes",     "No",         "No",       "No"],
        ["Free to use",             "Yes",     "No",         "No",       "Yes"],
        ["Customizable pipeline",   "Yes",     "No",         "No",       "No"],
    ]
    t = Table(comp_data, colWidths=[2.2*inch, 1.0*inch, 1.1*inch, 1.1*inch, 1.1*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), NAVY),
        ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 8.5),
        ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,1),(-1,-1), 8.5),
        ("BACKGROUND",    (1,1),(1,-1), LIGHT_GREEN),
        ("TEXTCOLOR",     (1,1),(1,-1), GREEN),
        ("FONTNAME",      (1,1),(1,-1), "Helvetica-Bold"),
        ("ALIGN",         (1,0),(-1,-1), "CENTER"),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GRAY_LIGHT]),
        ("GRID",          (0,0),(-1,-1), 0.4, GRAY_LINE),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 0.1*inch))

    elems.append(sub("Go-to-Market Phases", styles))
    gtm_data = [
        ["Phase", "Name",          "Focus",                                          "Target"],
        ["1",     "MVP (Now)",     "Local Streamlit app, Marketcheck integration",   "Developer / personal use"],
        ["2",     "Beta",          "Cloud deploy, user accounts, saved searches",    "Early adopters / dealerships"],
        ["3",     "Growth",        "Photo thumbnails, VIN history, price alerts",    "Consumer car buyers"],
        ["4",     "Scale",         "White-label API for dealers, CRM integrations",  "Enterprise / dealer networks"],
    ]
    t = Table(gtm_data, colWidths=[0.5*inch, 1.2*inch, 3.0*inch, 1.8*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), BLUE),
        ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 8.5),
        ("BACKGROUND",    (0,1),(0,1), LIGHT_GREEN),
        ("TEXTCOLOR",     (0,1),(0,1), GREEN),
        ("FONTNAME",      (0,1),(0,1), "Helvetica-Bold"),
        ("BACKGROUND",    (0,2),(0,2), LIGHT_BLUE),
        ("TEXTCOLOR",     (0,2),(0,2), BLUE),
        ("BACKGROUND",    (0,3),(0,3), YELLOW),
        ("TEXTCOLOR",     (0,3),(0,3), ORANGE),
        ("BACKGROUND",    (0,4),(0,4), LIGHT_ORANGE),
        ("TEXTCOLOR",     (0,4),(0,4), ORANGE),
        ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,1),(-1,-1), 8.5),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("ALIGN",         (0,0),(0,-1), "CENTER"),
        ("GRID",          (0,0),(-1,-1), 0.4, GRAY_LINE),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    elems.append(t)

    # ── Section 17: Design Architecture Diagram ────────────────────────────
    elems.append(PageBreak())
    elems.append(section_header("17", "Design Architecture Diagram", styles))
    elems.append(body(
        "The diagram below shows the full system architecture of AUTO AI, from user interaction "
        "through the agent pipeline to external APIs and delivery channels.", styles))
    elems.append(Spacer(1, 0.1*inch))
    elems.append(_arch_diagram())
    elems.append(Spacer(1, 0.15*inch))

    legend_data = [[
        _legend_box(BLUE,   "Frontend / UI"),
        _legend_box(GREEN,  "Agent Layer"),
        _legend_box(TEAL,   "Orchestrator"),
        _legend_box(PURPLE, "Data Models"),
        _legend_box(ORANGE, "External APIs"),
        _legend_box(NAVY,   "Delivery"),
    ]]
    legend_t = Table(legend_data, colWidths=[1.08*inch]*6)
    legend_t.setStyle(TableStyle([
        ("ALIGN",  (0,0),(-1,-1), "CENTER"),
        ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2),
    ]))
    elems.append(legend_t)

    # ── Section 18: Detailed Workflow ──────────────────────────────────────
    elems.append(PageBreak())
    elems.append(section_header("18", "Detailed Workflow", styles))
    elems.append(body(
        "The workflow below traces the full lifecycle of a single car search request through "
        "the AUTO AI system — from user input to delivered results.", styles))
    elems.append(Spacer(1, 0.1*inch))
    elems.append(_workflow_diagram())
    elems.append(Spacer(1, 0.12*inch))

    elems.append(sub("Step-by-Step Breakdown", styles))
    workflow_steps = [
        ("Step 1", BLUE,   "User Input & Validation",
         "User fills the Streamlit sidebar with make, model, budget, mileage, color, location, "
         "radius, and delivery preferences. The app validates all required fields and checks "
         "that price_min < price_max before proceeding."),
        ("Step 2", TEAL,   "Orchestrator Kicks Off Pipeline",
         "run_pipeline() is called with a validated CarPreferences Pydantic model. The orchestrator "
         "calls each agent in sequence: Search → Rank → Outreach, passing results between agents "
         "and collecting a final results dictionary."),
        ("Step 3", GREEN,  "Search Agent — Normalize",
         "GPT-4o-mini receives the raw make/model strings and returns the corrected official names "
         "as a JSON object. Example: 'porche' → 'Porsche'. This prevents zero-result API calls "
         "caused by typos."),
        ("Step 4", GREEN,  "Search Agent — Query Marketcheck",
         "The agent calls GET /v2/search/car/active with all filters: make, model, price range, "
         "mileage cap, exterior color, ZIP/city, and radius. Up to 10 results are returned sorted "
         "by price ascending. Each listing is parsed into a CarListing Pydantic object."),
        ("Step 5", GREEN,  "Search Agent — Fallback",
         "If MARKETCHECK_API_KEY is not set, or if the API returns 0 results, or if an exception "
         "is raised, the agent falls back to GPT-4o-mini to simulate 5 realistic listings. "
         "A warning flag is set and passed through the pipeline."),
        ("Step 6", PURPLE, "Ranking Agent — Score & Sort",
         "Each CarListing is scored on 4 factors (price 40pts, mileage 30pts, ext color 15pts, "
         "int color 15pts). Listings are sorted descending by score. The top 5 are returned."),
        ("Step 7", ORANGE, "Outreach Agent — Generate Content",
         "If email is enabled: GPT-4o-mini writes a personalized HTML email body with listing "
         "cards, prices, mileage, colors, dealer info, and 'View Listing' links. "
         "If SMS is enabled: GPT writes a ≤300-character summary of the top 3 listings."),
        ("Step 8", NAVY,   "Outreach Agent — Deliver",
         "SendGrid sends the HTML email to the user's address. Twilio sends the SMS to the user's "
         "phone number. Both return a success/failure dict that is surfaced in the UI."),
        ("Step 9", BLUE,   "Display Results",
         "The Streamlit UI renders 5 listing cards in a 3-column grid. Each card shows: title, "
         "price, year, mileage, colors, dealer, location, match score, source badge (green = real "
         "data, orange = AI simulated), and a clickable 'View Listing →' link."),
    ]
    for step, color, title, desc in workflow_steps:
        row = Table([[
            Paragraph(step, ParagraphStyle("ws", fontName="Helvetica-Bold",
                fontSize=8, textColor=WHITE, leading=11, alignment=TA_CENTER)),
            Paragraph(f"<b>{title}</b><br/><font size='8'>{desc}</font>",
                ParagraphStyle("wd", fontName="Helvetica", fontSize=9,
                    textColor=GRAY_DARK, leading=13))
        ]], colWidths=[0.65*inch, 5.85*inch])
        row.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(0,0), color),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("LINEBELOW",     (0,0),(-1,-1), 0.5, GRAY_LINE),
        ]))
        elems.append(row)

    # ── Section 19: Agent Deep Dive ────────────────────────────────────────
    elems.append(PageBreak())
    elems.append(section_header("19", "Agent Deep Dive", styles))
    elems.append(body(
        "AUTO AI is built on a three-agent architecture coordinated by a central orchestrator. "
        "Each agent has a single, well-defined responsibility and communicates via typed Pydantic "
        "models.", styles))
    elems.append(Spacer(1, 0.1*inch))

    agents = [
        {
            "name": "Search Agent",
            "file": "agents/search_agent.py",
            "color": GREEN,
            "light": LIGHT_GREEN,
            "role": "Discover real car listings from live inventory APIs and normalize user input.",
            "input": "CarPreferences (make, model, price range, mileage, colors, location, radius)",
            "output": "list[CarListing] + optional warning string",
            "tools": ["OpenAI GPT-4o-mini (normalization)", "Marketcheck REST API v2", "GPT-4o-mini (fallback simulation)"],
            "steps": [
                "Call GPT-4o-mini to correct make/model spelling",
                "Parse location string into ZIP or city/state params",
                "Call Marketcheck GET /v2/search/car/active with all filters",
                "Parse JSON response into CarListing objects with source domain",
                "If 0 results or exception → call GPT fallback and set warning flag",
            ],
            "fallback": "GPT-4o-mini generates 5 simulated listings marked 'AI Simulated'",
        },
        {
            "name": "Ranking Agent",
            "file": "agents/ranking_agent.py",
            "color": PURPLE,
            "light": colors.HexColor("#EDE9FE"),
            "role": "Score and prioritize listings by relevance to buyer preferences.",
            "input": "CarPreferences + list[CarListing]",
            "output": "list[CarListing] — top 5, sorted by match_score descending",
            "tools": ["Pure Python — no external API or LLM calls"],
            "steps": [
                "Price proximity: score up to 40pts based on distance from budget midpoint",
                "Mileage: score up to 30pts — lower mileage relative to cap = higher score",
                "Exterior color: +15pts flat if preference substring matches listing color",
                "Interior color: +15pts flat if preference substring matches listing color",
                "Sort all listings descending by total score, return top 5",
            ],
            "fallback": "No fallback needed — pure deterministic algorithm",
        },
        {
            "name": "Outreach Agent",
            "file": "agents/outreach_agent.py",
            "color": ORANGE,
            "light": LIGHT_ORANGE,
            "role": "Generate personalized content and deliver results via email and SMS.",
            "input": "CarPreferences + top 5 CarListings",
            "output": "dict with email/SMS success status and generated content",
            "tools": ["OpenAI GPT-4o-mini (email + SMS writing)", "SendGrid API (email)", "Twilio API (SMS)"],
            "steps": [
                "If email enabled: GPT writes personalized HTML email body with listing cards",
                "Send HTML email via SendGrid to user's address with subject line",
                "If SMS enabled: GPT writes ≤300 char SMS summary of top 3 listings",
                "Send SMS via Twilio from configured phone number to user's number",
                "Return success/failure dict for each channel back to orchestrator",
            ],
            "fallback": "Delivery failure is caught and shown as error in UI — pipeline continues",
        },
    ]

    for agent in agents:
        elems.append(KeepTogether([
            Table([[
                Paragraph(agent["name"], ParagraphStyle("an", fontName="Helvetica-Bold",
                    fontSize=13, textColor=WHITE, leading=17)),
                Paragraph(agent["file"], ParagraphStyle("af", fontName="Courier",
                    fontSize=8, textColor=colors.HexColor("#93C5FD"), leading=12,
                    alignment=TA_RIGHT)),
            ]], colWidths=[3.5*inch, 3.0*inch]),
        ]))
        # Agent header bar
        hdr = Table([[
            Paragraph(agent["name"], ParagraphStyle("an2", fontName="Helvetica-Bold",
                fontSize=12, textColor=WHITE, leading=16)),
            Paragraph(agent["file"], ParagraphStyle("af2", fontName="Courier",
                fontSize=8, textColor=colors.HexColor("#CBD5E1"), leading=12,
                alignment=TA_RIGHT)),
        ]], colWidths=[3.5*inch, 3.0*inch])
        hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), agent["color"]),
            ("TOPPADDING",    (0,0),(-1,-1), 10),
            ("BOTTOMPADDING", (0,0),(-1,-1), 10),
            ("LEFTPADDING",   (0,0),(-1,-1), 12),
            ("RIGHTPADDING",  (0,0),(-1,-1), 12),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ]))
        elems.append(hdr)

        # Role
        role_row = Table([[
            Paragraph("<b>Role:</b>", ParagraphStyle("rl", fontName="Helvetica-Bold",
                fontSize=8.5, textColor=agent["color"], leading=13)),
            Paragraph(agent["role"], ParagraphStyle("rv", fontName="Helvetica",
                fontSize=8.5, textColor=GRAY_DARK, leading=13)),
        ]], colWidths=[0.6*inch, 5.9*inch])
        role_row.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), agent["light"]),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 12),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ]))
        elems.append(role_row)

        # I/O/Tools/Steps table
        detail_data = [
            ["Input",    agent["input"]],
            ["Output",   agent["output"]],
            ["Tools",    "\n".join(f"  • {t}" for t in agent["tools"])],
            ["Steps",    "\n".join(f"  {i+1}. {s}" for i, s in enumerate(agent["steps"]))],
            ["Fallback", agent["fallback"]],
        ]
        for label, val in detail_data:
            r = Table([[
                Paragraph(label, ParagraphStyle("dl", fontName="Helvetica-Bold",
                    fontSize=8, textColor=WHITE, leading=12, alignment=TA_CENTER)),
                Paragraph(val.replace("\n", "<br/>"), ParagraphStyle("dv",
                    fontName="Helvetica", fontSize=8.5, textColor=GRAY_DARK, leading=13)),
            ]], colWidths=[0.75*inch, 5.75*inch])
            r.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(0,0), agent["color"]),
                ("TOPPADDING",    (0,0),(-1,-1), 6),
                ("BOTTOMPADDING", (0,0),(-1,-1), 6),
                ("LEFTPADDING",   (0,0),(-1,-1), 10),
                ("VALIGN",        (0,0),(-1,-1), "TOP"),
                ("LINEBELOW",     (0,0),(-1,-1), 0.4, GRAY_LINE),
            ]))
            elems.append(r)

        elems.append(Spacer(1, 0.18*inch))

    # ── Build ──────────────────────────────────────────────────────────────
    doc.build(elems, onFirstPage=BRDCanvas.on_page, onLaterPages=BRDCanvas.on_page)
    print(f"✅  PDF created: {OUTPUT_FILE}")


if __name__ == "__main__":
    build_pdf()
