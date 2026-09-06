import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    # 16:9 widescreen
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_slide_layout = prs.slide_layouts[6] # completely blank

    # Color palette
    NAVY = RGBColor(11, 44, 91)
    ACCENT_BLUE = RGBColor(24, 119, 242)
    DARK_GRAY = RGBColor(33, 37, 41)
    LIGHT_BG = RGBColor(248, 249, 250)
    CARD_BORDER = RGBColor(220, 224, 230)
    WHITE = RGBColor(255, 255, 255)
    MUTED = RGBColor(108, 117, 125)
    GREEN = RGBColor(16, 149, 93)

    # -------------------------------------------------------------
    # SLIDE 1: Title
    # -------------------------------------------------------------
    s1 = prs.slides.add_slide(blank_slide_layout)
    
    # Header bar
    hbar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.4))
    hbar.fill.solid(); hbar.fill.fore_color.rgb = NAVY; hbar.line.fill.background()
    
    # Title box
    tb = s1.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.333), Inches(3.5))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = "SatQuery AI"
    p.font.size = Pt(48)
    p.font.bold = True
    p.font.color.rgb = NAVY
    p.alignment = PP_ALIGN.CENTER
    
    p2 = tf.add_paragraph()
    p2.text = "An Interactive Vision-Language Assistant for Multimodal Remote Sensing Image Analysis through Text Queries"
    p2.font.size = Pt(22)
    p2.font.color.rgb = ACCENT_BLUE
    p2.alignment = PP_ALIGN.CENTER
    p2.space_before = Pt(14)
    
    p3 = tf.add_paragraph()
    p3.text = "Smart India Hackathon (SIH 2026) | Problem Statement: SIH26167"
    p3.font.size = Pt(16)
    p3.font.bold = True
    p3.font.color.rgb = DARK_GRAY
    p3.alignment = PP_ALIGN.CENTER
    p3.space_before = Pt(24)

    # Footer
    fbar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(6.9), Inches(13.333), Inches(0.6))
    fbar.fill.solid(); fbar.fill.fore_color.rgb = ACCENT_BLUE; fbar.line.fill.background()
    ftxt = s1.shapes.add_textbox(Inches(1.0), Inches(6.95), Inches(11.333), Inches(0.5))
    ftxt.text_frame.text = "Ministry of Jal Shakti / ISRO & SAC Aligned Track  |  SatQuery AI Team"
    ftxt.text_frame.paragraphs[0].font.color.rgb = WHITE
    ftxt.text_frame.paragraphs[0].font.size = Pt(12)
    ftxt.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    # -------------------------------------------------------------
    # SLIDE 2: EXACT SIH TEMPLATE - PROPOSED SOLUTION
    # -------------------------------------------------------------
    s2 = prs.slides.add_slide(blank_slide_layout)
    
    # Top Oval (Team Name)
    oval = s2.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.6), Inches(0.4), Inches(2.2), Inches(1.1))
    oval.fill.solid(); oval.fill.fore_color.rgb = WHITE
    oval.line.color.rgb = RGBColor(128, 0, 128); oval.line.width = Pt(2.0)
    otf = oval.text_frame; otf.text = "Your Team\nName"
    otf.paragraphs[0].font.size = Pt(14); otf.paragraphs[0].font.bold = True
    otf.paragraphs[0].font.color.rgb = DARK_GRAY; otf.paragraphs[0].alignment = PP_ALIGN.CENTER
    otf.paragraphs[1].font.size = Pt(14); otf.paragraphs[1].font.bold = True
    otf.paragraphs[1].font.color.rgb = DARK_GRAY; otf.paragraphs[1].alignment = PP_ALIGN.CENTER

    # Top Center: IDEA TITLE
    itb = s2.shapes.add_textbox(Inches(3.2), Inches(0.5), Inches(6.8), Inches(0.9))
    itf = itb.text_frame; itf.word_wrap = True
    ip = itf.paragraphs[0]
    ip.text = "SatQuery AI: Interactive Multimodal RS Assistant"
    ip.font.size = Pt(24); ip.font.bold = True; ip.font.color.rgb = DARK_GRAY
    ip.alignment = PP_ALIGN.CENTER

    # Top Right: SIH 2026 Badge
    sih_box = s2.shapes.add_textbox(Inches(10.2), Inches(0.4), Inches(2.5), Inches(1.1))
    stf = sih_box.text_frame
    sp = stf.paragraphs[0]
    sp.text = "SMART INDIA\nHACKATHON 2026"
    sp.font.size = Pt(15); sp.font.bold = True; sp.font.color.rgb = NAVY
    sp.alignment = PP_ALIGN.RIGHT

    # Main Slide Title
    stitle_box = s2.shapes.add_textbox(Inches(0.6), Inches(1.6), Inches(12.133), Inches(0.7))
    stitle_f = stitle_box.text_frame
    stp = stitle_f.paragraphs[0]
    stp.text = "❖ Proposed Solution (Describe your Idea/Solution/Prototype)"
    stp.font.size = Pt(22); stp.font.bold = True; stp.font.color.rgb = ACCENT_BLUE

    # 3 Content Columns / Cards
    cards_data = [
        ("Detailed Explanation of Proposed Solution", [
            ("Agentic AI Orchestrator: ", "Translates natural-language queries into multi-specialist satellite analyses autonomously."),
            ("Native GeoTIFF Ingestion: ", "Directly processes optical/SAR, co-registered optical+SAR pairs, and bi-temporal pairs with full CRS & metadata preservation."),
            ("Specialist Engines: ", "Routes to fine-tuned RS-VLM (BigEarthNet.txt adapted), open-vocabulary grounder, radiometric change detector, and radar fusion pipeline.")
        ], Inches(0.6)),
        ("How It Addresses The Problem", [
            ("Democratizes GIS Analysis: ", "Non-technical users query complex satellite rasters in plain English without manual band math or GIS software skills."),
            ("Optical + SAR Synergy: ", "Combines optical spectral context (chlorophyll/turbidity) with SAR microwave backscatter for cloud-penetrating analysis."),
            ("Evidence-Grounded Answers: ", "Every answer is strictly paired with GIS bounding boxes, segmentation masks, honest confidence, and telemetry traces.")
        ], Inches(4.7)),
        ("Innovation & Uniqueness", [
            ("Agentic Intent Router: ", "Predictable semantic query parser verifies spatial overlap and modality constraints before firing tools."),
            ("Natural-Language Change VQA: ", "Translates raw radiometric difference matrices into directional, quantitative natural-language change summaries."),
            ("True Radiometric Ingestion: ", "Processes calibrated radar backscatter in dB and optical surface reflectance rather than treating scenes as 8-bit RGB.")
        ], Inches(8.8))
    ]

    for title, bullets, left_pos in cards_data:
        # Card background
        card = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left_pos, Inches(2.4), Inches(3.9), Inches(4.3))
        card.fill.solid(); card.fill.fore_color.rgb = LIGHT_BG
        card.line.color.rgb = CARD_BORDER; card.line.width = Pt(1.5)
        
        # Header inside card
        ch_box = s2.shapes.add_textbox(left_pos + Inches(0.15), Inches(2.5), Inches(3.6), Inches(0.7))
        ch_tf = ch_box.text_frame; ch_tf.word_wrap = True
        ch_p = ch_tf.paragraphs[0]
        ch_p.text = title
        ch_p.font.size = Pt(15); ch_p.font.bold = True; ch_p.font.color.rgb = NAVY
        
        # Bullet list inside card
        cb_box = s2.shapes.add_textbox(left_pos + Inches(0.15), Inches(3.2), Inches(3.6), Inches(3.4))
        cb_tf = cb_box.text_frame; cb_tf.word_wrap = True
        
        for idx, (lead, desc) in enumerate(bullets):
            p = cb_tf.paragraphs[0] if idx == 0 else cb_tf.add_paragraph()
            p.space_after = Pt(10)
            
            run1 = p.add_run()
            run1.text = "• " + lead
            run1.font.bold = True
            run1.font.size = Pt(12)
            run1.font.color.rgb = DARK_GRAY
            
            run2 = p.add_run()
            run2.text = desc
            run2.font.bold = False
            run2.font.size = Pt(11.5)
            run2.font.color.rgb = DARK_GRAY

    # Footer
    fbar2 = s2.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(6.9), Inches(13.333), Inches(0.6))
    fbar2.fill.solid(); fbar2.fill.fore_color.rgb = ACCENT_BLUE; fbar2.line.fill.background()
    
    ftxt2_l = s2.shapes.add_textbox(Inches(0.6), Inches(6.95), Inches(8.0), Inches(0.5))
    ftxt2_l.text_frame.text = "@SIH Idea submission- Template"
    ftxt2_l.text_frame.paragraphs[0].font.color.rgb = WHITE
    ftxt2_l.text_frame.paragraphs[0].font.size = Pt(12)
    
    ftxt2_r = s2.shapes.add_textbox(Inches(12.0), Inches(6.95), Inches(1.0), Inches(0.5))
    ftxt2_r.text_frame.text = "2"
    ftxt2_r.text_frame.paragraphs[0].font.color.rgb = WHITE
    ftxt2_r.text_frame.paragraphs[0].font.size = Pt(14)
    ftxt2_r.text_frame.paragraphs[0].font.bold = True

    # -------------------------------------------------------------
    # SLIDE 3 - 15 SUMMARY SLIDES
    # -------------------------------------------------------------
    remaining_slides = [
        ("Architecture & Workflow", "End-to-end flow from React GIS frontend, FastAPI gateway, RasterIngestor, AgentOrchestrator to 4 specialized inference engines and visual evidence generation."),
        ("Agentic Orchestration Deep Dive", "Explains the 10-step execution pipeline of AgentOrchestrator in app/agent/orchestrator.py: validation, modality extraction, intent parsing, model routing, and telemetry logging."),
        ("Multimodal Optical + SAR Fusion", "How SatQuery AI co-registers optical reflectance and SAR radar backscatter (dB) to classify water and built-up areas through clouds."),
        ("Bi-Temporal Change Understanding", "Automated radiometric differencing, adaptive thresholding, and natural-language change summary answering 'what changed and where'."),
        ("Model Adaptation on BigEarthNet.txt", "Details the 1.44 GB fine-tuned PyTorch checkpoint in checkpoints/bigearthnet_blip_vqa/best trained using training/train_bigearthnet.py."),
        ("ISRO / SAC Mission Compatibility", "Metadata and band normalization for Cartosat-2S optical and RISAT-1 radar sensors via app/utils/isro_adapter.py."),
        ("Trust & Verifiability Framework", "Honest confidence bounds, geospatial bounding boxes/masks, and immutable audit traces tracked by ExecutionTracker."),
        ("Exact SIH26167 Compliance Matrix", "16/16 requirements compliant including single-image VQA, bi-temporal change VQA, optical-SAR fusion, and GeoTIFF ingestion.")
    ]

    for title, desc in remaining_slides:
        s = prs.slides.add_slide(blank_slide_layout)
        # Header
        h = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(1.0))
        h.fill.solid(); h.fill.fore_color.rgb = NAVY; h.line.fill.background()
        ht = s.shapes.add_textbox(Inches(0.6), Inches(0.15), Inches(12.0), Inches(0.7))
        hp = ht.text_frame.paragraphs[0]
        hp.text = f"SatQuery AI — {title}"
        hp.font.size = Pt(24); hp.font.bold = True; hp.font.color.rgb = WHITE

        # Body card
        bcard = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(1.8), Inches(11.333), Inches(4.5))
        bcard.fill.solid(); bcard.fill.fore_color.rgb = LIGHT_BG
        bcard.line.color.rgb = CARD_BORDER
        bt = s.shapes.add_textbox(Inches(1.5), Inches(2.2), Inches(10.333), Inches(3.8))
        btf = bt.text_frame; btf.word_wrap = True
        bp = btf.paragraphs[0]
        bp.text = desc
        bp.font.size = Pt(18); bp.font.color.rgb = DARK_GRAY

        # Footer
        fb = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(6.9), Inches(13.333), Inches(0.6))
        fb.fill.solid(); fb.fill.fore_color.rgb = ACCENT_BLUE; fb.line.fill.background()

    out_path = r"d:\PROJECTS-PUPU\satquery-ai\SatQuery_AI_SIH26167_Presentation.pptx"
    prs.save(out_path)
    print(f"Presentation saved successfully to {out_path}")

if __name__ == "__main__":
    create_presentation()
