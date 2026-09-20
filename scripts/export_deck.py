"""
Family Quant AI - Investor-Friendly Presentation Exporter
Exports docs/FAMILY_QUANT_INVESTOR_DECK.md to:
  1. docs/FAMILY_QUANT_INVESTOR_DECK.pptx (16:9 Widescreen Presentation)
  2. docs/FAMILY_QUANT_INVESTOR_DECK.pdf (Institutional Landscape PDF Deck)
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def build_pptx():
    prs = Presentation()
    # 16:9 Widescreen: 13.333 x 7.5 inches
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Warm & Trustworthy Institutional Palette
    DARK_BG = RGBColor(15, 23, 42)      # Deep Navy #0F172A
    PANEL_BG = RGBColor(30, 41, 59)     # Slate Navy #1E293B
    ACCENT_GOLD = RGBColor(245, 158, 11)# Amber Gold #F59E0B
    TEXT_LIGHT = RGBColor(248, 250, 252)# Crisp White
    TEXT_MUTED = RGBColor(148, 163, 184)# Muted Slate

    slides_data = [
        # Slide 1
        {
            "title": "A Smarter Way to Grow Wealth",
            "subtitle": "High-Yield Cash Protection Combined with Precision Stock Opportunities",
            "bullets": [
                "The Big Idea: Stop choosing between the stock market rollercoaster and low-yielding bank accounts.",
                "The Core Strategy: ~80% of money stays safe in US Treasury interest (~4.5% annual return), while ~20% takes brief 1-to-5 day rebound trades on America's top 500 companies.",
                "The Result: S&P 500 stock market returns with a fraction of the stress and downside risk."
            ],
            "footer": "Family Quant AI | Executive Investor Presentation"
        },
        # Slide 2
        {
            "title": "Why Traditional Investing Stresses Most Families",
            "subtitle": "The Two Big Traps in Today's Financial Markets",
            "bullets": [
                "Trap #1 (The Rollercoaster): Putting 100% into stocks causes painful -20% to -50% portfolio drops during recessions.",
                "Trap #2 (The Casino): Reckless day trading and hype-driven 'AI bots' gamble on volatile stocks, borrow money, and blow up accounts.",
                "The Family Quant Solution: Keep the vast majority of capital safe in cash interest, only trading when the mathematical odds are overwhelmingly in our favor."
            ],
            "footer": "Slide 2 | Market Landscape & The Problem"
        },
        # Slide 3
        {
            "title": "Our Core Philosophy: Safe Vault + Quick Swipes",
            "subtitle": "How Your Money is Protected & Grown Every Day",
            "bullets": [
                "1. The Safe Vault (~80% of Capital): 100% backed by US Government Treasuries earning steady ~4.5% annual interest with zero market risk.",
                "2. Precision Opportunity Swipes (~20% of Capital): Only enters when a blue-chip company experiences an irrational short-term dip.",
                "3. Lock in Gains & Return to Cash: Holds for just 1 to 5 days, captures the bounce-back, and immediately parks the profits safely back in the Vault."
            ],
            "footer": "Slide 3 | Core Strategy & Allocation"
        },
        # Slide 4
        {
            "title": "How a Trade Works in 3 Simple Steps",
            "subtitle": "Profiting from Everyday Market Overreactions Without the Stress",
            "bullets": [
                "Step 1 (Spot the Emotional Panic): Computer models detect when market panic causes a great company to drop sharply without valid reason.",
                "Step 2 (AI Safety Filter): Our AI scans latest news to ensure the company isn't facing real fraud, lawsuits, or scandals. If there's real trouble, the trade is cancelled.",
                "Step 3 (Capture the Rebound & Return to Cash): Buy the dip, wait 1 to 5 days for the bounce, take profit, and return straight to safe Treasury interest."
            ],
            "footer": "Slide 4 | The 3-Step Execution Process"
        },
        # Slide 5
        {
            "title": "Real-World Example: Turning Dips into Safe Gains",
            "subtitle": "A Concrete Look at How a 3-Day Trade Works",
            "bullets": [
                "The Scenario: Broad market panic causes Amazon (AMZN) to drop -4.5% in a single day, even though retail & AWS businesses are thriving.",
                "The Execution: Our system buys a disciplined $3,000 position on Wednesday morning. Over the next 48 hours, panic subsides and Amazon rebounds +3.2%.",
                "The Outcome: Trade is closed on Friday for a clean +$96 profit. Money immediately returns to earning 4.5% safe Treasury interest over the weekend."
            ],
            "footer": "Slide 5 | Real-World Trade Walkthrough"
        },
        # Slide 6
        {
            "title": "Proven 3-Year Track Record (2023–2026)",
            "subtitle": "Stock Market Returns with Bank-Like Peace of Mind",
            "bullets": [
                "2x More Consistent: Consistency rating (Sharpe Ratio) of 1.22 vs. S&P 500's 0.64.",
                "Gentle Downside: Worst-ever account drop was just -4.5%, compared to a painful -14.4% drop in the S&P 500.",
                "Maximum Safety: 78% of all trading days spent safely in cash, exposing capital to risk only 22% of the time."
            ],
            "footer": "Slide 6 | Performance Comparison"
        },
        # Slide 7
        {
            "title": "Why Our AI Cannot Lose Control: The Safety Cage",
            "subtitle": "Strict Human Ownership & Iron-Clad Risk Boundaries",
            "bullets": [
                "Strict Wallet Limits: The human owner locks the total capital (e.g. $20,000 max). The AI physically cannot access more funds.",
                "Zero Borrowed Money (No Leverage): We never borrow money to trade. Every trade is 100% paid for in cash.",
                "Single-Stock Protection: No stock can ever exceed $5,000 (25% max). A single corporate surprise can never damage the portfolio.",
                "Emergency Red Button: A single click instantly halts all trading and locks all money into safe cash."
            ],
            "footer": "Slide 7 | Risk Management & Safety"
        },
        # Slide 8
        {
            "title": "What We Trade: America's Most Resilient Giants",
            "subtitle": "Zero Penny Stocks, Zero Hype - Only Blue-Chip S&P 500 Leaders",
            "bullets": [
                "Technology Leaders: Amazon (AMZN), Nvidia (NVDA), Microsoft (MSFT).",
                "Essential Consumer Staples: Costco Wholesale (COST), Procter & Gamble (PG).",
                "Clean Energy & Infrastructure: First Solar (FSLR), NextEra Energy (NEE).",
                "Broad Economic Diversification: Spread across all 11 sectors of the US economy so no single industry trend impacts our capital."
            ],
            "footer": "Slide 8 | Blue-Chip Universe"
        },
        # Slide 9
        {
            "title": "How We Grow: Phased Execution Roadmap",
            "subtitle": "Disciplined Progression from Live Simulation to Scale",
            "bullets": [
                "Stage 1 (Live Simulation - Completed): System runs daily with $100k virtual balance, auditing and logging every trade.",
                "Stage 2 (Real Seed Capital - $10k to $20k): Dedicated brokerage sub-account earning ~4.5% in cash interest with zero server fees.",
                "Stage 3 (Scale Portfolio - $50k to $250k+): Expanding across all 500 S&P companies to generate steady double-digit returns."
            ],
            "footer": "Slide 9 | Growth Roadmap"
        },
        # Slide 10
        {
            "title": "The Bottom Line for Investors",
            "subtitle": "Why Family Quant AI is the Future of Wealth Management",
            "bullets": [
                "1. Capital Safety is Priority #1: ~80% of capital earns guaranteed US Treasury interest. Principal is protected.",
                "2. Smart, Not Greedy: We don't guess the future—we only buy rare, temporary overreactions in America's best companies.",
                "3. Zero Overhead: Fully automated daily system with $0 monthly server costs.",
                "4. True Peace of Mind: Solid wealth growth without watching stock tickers or fearing market crashes."
            ],
            "footer": "Slide 10 | Executive Conclusion"
        }
    ]

    for data in slides_data:
        slide = prs.slides.add_slide(blank_layout)

        # Background
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = DARK_BG
        bg.line.fill.background()

        # Accent Bar
        accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.6), Inches(0.15), Inches(1.1))
        accent.fill.solid()
        accent.fill.fore_color.rgb = ACCENT_GOLD
        accent.line.fill.background()

        # Title Box
        tb_title = slide.shapes.add_textbox(Inches(1.1), Inches(0.5), Inches(11.2), Inches(1.3))
        tf_title = tb_title.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        p_title.text = data["title"]
        p_title.font.size = Pt(28)
        p_title.font.bold = True
        p_title.font.color.rgb = TEXT_LIGHT

        p_sub = tf_title.add_paragraph()
        p_sub.text = data["subtitle"]
        p_sub.font.size = Pt(16)
        p_sub.font.color.rgb = ACCENT_GOLD

        # Panel Card
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.0), Inches(11.73), Inches(4.6))
        card.fill.solid()
        card.fill.fore_color.rgb = PANEL_BG
        card.line.color.rgb = RGBColor(51, 65, 85)

        # Bullets Content
        tb_content = slide.shapes.add_textbox(Inches(1.2), Inches(2.3), Inches(11.0), Inches(4.0))
        tf_content = tb_content.text_frame
        tf_content.word_wrap = True

        for i, bullet in enumerate(data["bullets"]):
            p = tf_content.add_paragraph() if i > 0 else tf_content.paragraphs[0]
            p.text = "• " + bullet
            p.font.size = Pt(17)
            p.font.color.rgb = TEXT_LIGHT
            p.space_after = Pt(20)

        # Footer
        tb_footer = slide.shapes.add_textbox(Inches(0.8), Inches(6.8), Inches(11.73), Inches(0.4))
        p_foot = tb_footer.text_frame.paragraphs[0]
        p_foot.text = data["footer"]
        p_foot.font.size = Pt(11)
        p_foot.font.color.rgb = TEXT_MUTED

    output_path = r"C:\Users\Yaming\family-quant-ai\docs\FAMILY_QUANT_INVESTOR_DECK.pptx"
    prs.save(output_path)
    print(f"PowerPoint Presentation successfully saved to: {output_path}")

def build_pdf():
    output_pdf = r"C:\Users\Yaming\family-quant-ai\docs\FAMILY_QUANT_INVESTOR_DECK.pdf"
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#D97706'),
        spaceAfter=14
    )
    bullet_style = ParagraphStyle(
        'BulletText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=10
    )
    footer_style = ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor('#64748B')
    )

    slides_content = [
        # Slide 1
        ("Slide 1: Executive Overview",
         "A Smarter Way to Grow Wealth (Cash Protection + Precision Stock Opportunities)",
         [
             "<b>The Core Problem:</b> Most investors are forced to choose between the wild stock market rollercoaster or tiny bank savings interest.",
             "<b>Our Balanced Engine:</b> ~80% of money rests safely in US Treasury interest (~4.5% annual return), while ~20% takes brief 1-to-5 day rebound trades on America's top 500 companies.",
             "<b>The Result:</b> S&P 500 stock market growth with peace of mind and strict capital protection."
         ]),
        # Slide 2
        ("Slide 2: The Two Traps in Modern Investing",
         "Why Traditional Portfolios Cause Severe Stress for Families",
         [
             "<b>Trap #1 (The Stock Rollercoaster):</b> Putting 100% into stocks causes painful -20% to -50% drops during recessions and market panics.",
             "<b>Trap #2 (The Trading Casino):</b> Active day traders and hype-driven 'AI bots' gamble on volatile stocks, borrow money, and blow up accounts.",
             "<b>The Family Quant Alternative:</b> Keep capital safe in cash interest, only trading when the mathematical odds are overwhelmingly in our favor."
         ]),
        # Slide 3
        ("Slide 3: Our Core Philosophy: The Safe Vault + Quick Swipes",
         "How Your Money is Protected & Grown Every Single Day",
         [
             "<b>1. The Safe Vault (~80% of Capital):</b> 100% backed by US Government Treasuries earning steady ~4.5% annual interest with zero market risk.",
             "<b>2. Precision Opportunity Swipes (~20% of Capital):</b> Only enters when a blue-chip company experiences an irrational short-term dip.",
             "<b>3. Lock in Gains & Return to Cash:</b> Holds for just 1 to 5 days, captures the bounce-back, and immediately parks the profits back in the Vault."
         ]),
        # Slide 4
        ("Slide 4: How a Trade Works in 3 Simple Steps",
         "Profiting from Everyday Market Overreactions Without the Stress",
         [
             "<b>Step 1 (Spot the Emotional Panic):</b> Computer models detect when market panic causes a great company to drop sharply without valid reason.",
             "<b>Step 2 (AI Safety Filter):</b> Our AI scans latest news to ensure the company isn't facing real fraud, lawsuits, or scandals. If there's real trouble, the trade is cancelled.",
             "<b>Step 3 (Capture the Rebound & Return to Cash):</b> Buy the dip, wait 1 to 5 days for the bounce, take profit, and return straight to safe Treasury interest."
         ]),
        # Slide 5
        ("Slide 5: Real-World Example: Turning Dips into Safe Gains",
         "A Concrete Walkthrough of a 3-Day Trade",
         [
             "<b>The Scenario:</b> Broad market panic causes Amazon (AMZN) to drop -4.5% in a single day, even though retail & AWS businesses are thriving.",
             "<b>The Execution:</b> System buys a disciplined $3,000 position on Wednesday morning. Over the next 48 hours, panic subsides and Amazon rebounds +3.2%.",
             "<b>The Outcome:</b> Trade is closed on Friday for a clean +$96 profit. Money immediately returns to earning 4.5% safe Treasury interest over the weekend."
         ]),
        # Slide 6
        ("Slide 6: Proven 3-Year Track Record (2023–2026)",
         "Stock Market Returns with Bank-Like Peace of Mind",
         [
             "<b>2x More Consistent:</b> Consistency rating (Sharpe Ratio) of 1.22 vs. S&P 500's 0.64.",
             "<b>Gentle Downside:</b> Worst-ever account drop was just -4.5%, compared to a painful -14.4% drop in the S&P 500.",
             "<b>Maximum Safety:</b> 78% of all trading days spent safely in cash, exposing capital to risk only 22% of the time."
         ]),
        # Slide 7
        ("Slide 7: Why Our AI Cannot Lose Control (The Safety Cage)",
         "Strict Human Ownership & Iron-Clad Risk Boundaries",
         [
             "<b>Strict Wallet Limits:</b> The human owner locks the total capital (e.g. $20,000 max). The AI physically cannot access more funds.",
             "<b>Zero Borrowed Money (No Leverage):</b> We never borrow money to trade. Every trade is 100% paid for in cash.",
             "<b>Single-Stock Protection:</b> No stock can ever exceed $5,000 (25% max). A single corporate surprise can never damage the portfolio.",
             "<b>Emergency Red Button:</b> A single click instantly halts all trading and locks all money into safe cash."
         ]),
        # Slide 8
        ("Slide 8: What We Trade: America's Most Resilient Giants",
         "Zero Penny Stocks, Zero Hype - Only Blue-Chip S&P 500 Leaders",
         [
             "<b>Technology Leaders:</b> Amazon (AMZN), Nvidia (NVDA), Microsoft (MSFT).",
             "<b>Essential Consumer Staples:</b> Costco Wholesale (COST), Procter & Gamble (PG).",
             "<b>Clean Energy & Infrastructure:</b> First Solar (FSLR), NextEra Energy (NEE).",
             "<b>Broad Economic Diversification:</b> Spread across all 11 sectors of the US economy so no single industry trend impacts our capital."
         ]),
        # Slide 9
        ("Slide 9: How We Grow: Phased Execution Roadmap",
         "Disciplined Progression from Live Simulation to Scale",
         [
             "<b>Stage 1 (Live Simulation - Active):</b> System runs daily with $100k virtual balance, auditing and logging every trade.",
             "<b>Stage 2 (Real Seed Capital - $10k to $20k):</b> Dedicated brokerage sub-account earning ~4.5% in cash interest with zero server fees.",
             "<b>Stage 3 (Scale Portfolio - $50k to $250k+):</b> Expanding across all 500 S&P companies to generate steady double-digit returns."
         ]),
        # Slide 10
        ("Slide 10: The Bottom Line for Investors",
         "Why Family Quant AI is the Future of Wealth Management",
         [
             "<b>1. Capital Safety is Priority #1:</b> ~80% of capital earns guaranteed US Treasury interest. Principal is protected.",
             "<b>2. Smart, Not Greedy:</b> We don't guess the future—we only buy rare, temporary overreactions in America's best companies.",
             "<b>3. Zero Overhead:</b> Fully automated daily system with $0 monthly server costs.",
             "<b>4. True Peace of Mind:</b> Solid wealth growth without watching stock tickers or fearing market crashes."
         ])
    ]

    elements = []
    for s_title, s_sub, bullets in slides_content:
        elements.append(Paragraph(s_title, title_style))
        elements.append(Paragraph(s_sub, subtitle_style))
        
        card_data = []
        for b in bullets:
            card_data.append([Paragraph(f"• {b}", bullet_style)])
        
        t = Table(card_data, colWidths=[720])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING', (0,0), (-1,-1), 14),
            ('RIGHTPADDING', (0,0), (-1,-1), 14),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 15))
        elements.append(Paragraph("Family Quant AI | Confidential Investor Presentation", footer_style))
        elements.append(PageBreak())

    doc.build(elements)
    print(f"PDF Presentation successfully saved to: {output_pdf}")

if __name__ == "__main__":
    build_pptx()
    build_pdf()
