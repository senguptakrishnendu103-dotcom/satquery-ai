import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def build_slide3_architecture(prs, s3):
    blank_layout = prs.slide_layouts[6]

    # Theme Colors
    NAVY = RGBColor(11, 44, 91)
    DARK_BLUE = RGBColor(15, 60, 130)
    PRIMARY_BLUE = RGBColor(24, 119, 242)
    PURPLE = RGBColor(105, 45, 175)
    GREEN = RGBColor(20, 125, 60)
    ORANGE = RGBColor(215, 95, 20)
    DARK_GRAY = RGBColor(33, 37, 41)
    LIGHT_GRAY = RGBColor(100, 110, 120)
    LIGHT_BG = RGBColor(248, 250, 253)
    CARD_BORDER = RGBColor(215, 225, 238)
    WHITE = RGBColor(255, 255, 255)

    # 1. TOP HEADER
    # Team Name Oval (Top Left)
    oval = s3.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.5), Inches(0.25), Inches(1.8), Inches(0.85))
    oval.fill.solid(); oval.fill.fore_color.rgb = WHITE
    oval.line.color.rgb = RGBColor(128, 0, 128); oval.line.width = Pt(1.5)
    otf = oval.text_frame; otf.text = "Your Team\nName"
    otf.paragraphs[0].font.size = Pt(12); otf.paragraphs[0].font.bold = True; otf.paragraphs[0].font.color.rgb = DARK_GRAY; otf.paragraphs[0].alignment = PP_ALIGN.CENTER
    otf.paragraphs[1].font.size = Pt(12); otf.paragraphs[1].font.bold = True; otf.paragraphs[1].font.color.rgb = DARK_GRAY; otf.paragraphs[1].alignment = PP_ALIGN.CENTER

    # Title: TECHNICAL APPROACH
    tb_title = s3.shapes.add_textbox(Inches(2.5), Inches(0.25), Inches(7.8), Inches(0.45))
    p_t = tb_title.text_frame.paragraphs[0]
    p_t.text = "TECHNICAL APPROACH"
    p_t.font.size = Pt(26); p_t.font.bold = True; p_t.font.color.rgb = DARK_GRAY; p_t.alignment = PP_ALIGN.CENTER

    # Top Right SIH Logo / Badge
    sih_box = s3.shapes.add_textbox(Inches(10.6), Inches(0.20), Inches(2.2), Inches(0.70))
    sp = sih_box.text_frame.paragraphs[0]
    sp.text = "SMART INDIA\nHACKATHON 2026"
    sp.font.size = Pt(13); sp.font.bold = True; sp.font.color.rgb = NAVY; sp.alignment = PP_ALIGN.RIGHT

    # Subtitle Underline Banner
    sub_box = s3.shapes.add_textbox(Inches(0.5), Inches(1.10), Inches(12.333), Inches(0.40))
    sp_sub = sub_box.text_frame.paragraphs[0].add_run()
    sp_sub.text = "❖ Technical Approach (Technologies Used & Methodology Flow)"
    sp_sub.font.size = Pt(18); sp_sub.font.bold = True; sp_sub.font.underline = True; sp_sub.font.color.rgb = PRIMARY_BLUE

    # -------------------------------------------------------------
    # LEFT CARD: • Technologies to be used (4.9 inches wide)
    # -------------------------------------------------------------
    c_left = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), Inches(1.60), Inches(4.7), Inches(5.15))
    c_left.fill.solid(); c_left.fill.fore_color.rgb = LIGHT_BG
    c_left.line.color.rgb = CARD_BORDER; c_left.line.width = Pt(1.5)

    cl_hdr = s3.shapes.add_textbox(Inches(0.65), Inches(1.70), Inches(4.4), Inches(0.45))
    cl_hp = cl_hdr.text_frame.paragraphs[0]
    cl_hp.text = "• Technologies to be used:"
    cl_hp.font.size = Pt(15); cl_hp.font.bold = True; cl_hp.font.color.rgb = NAVY

    cl_body = s3.shapes.add_textbox(Inches(0.65), Inches(2.15), Inches(4.4), Inches(4.45))
    cl_tf = cl_body.text_frame; cl_tf.word_wrap = True

    tech_specs = [
        ("Languages: ", "Python 3.11 (Backend AI/GIS), TypeScript (Frontend Web App)."),
        ("Frontend GIS: ", "React 19, Vite, Tailwind CSS v4, MapLibre GL (@nextgis/ngw-map)."),
        ("Backend & API: ", "FastAPI, Uvicorn ASGI, Pydantic v2, RESTFUL API Server."),
        ("AI / Vision-Language: ", "PyTorch, Hugging Face Transformers (Fine-tuned BLIP VQA & Grounder)."),
        ("Geospatial Engine: ", "GDAL, Rasterio, NumPy (GeoTIFF, NetCDF, CRS reprojection, band math)."),
        ("Hardware & Portability: ", "Optimized CPU inference (<300ms), optional CUDA GPU acceleration.")
    ]

    for idx, (lead, desc) in enumerate(tech_specs):
        p = cl_tf.paragraphs[0] if idx == 0 else cl_tf.add_paragraph()
        p.space_after = Pt(10)
        r1 = p.add_run(); r1.text = "• " + lead; r1.font.bold = True; r1.font.size = Pt(10.8); r1.font.color.rgb = DARK_GRAY
        r2 = p.add_run(); r2.text = desc; r2.font.bold = False; r2.font.size = Pt(10.2); r2.font.color.rgb = DARK_GRAY

    # -------------------------------------------------------------
    # RIGHT CARD: • Methodology and process for implementation (7.4 inches wide)
    # -------------------------------------------------------------
    c_right = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.4), Inches(1.60), Inches(7.4), Inches(5.15))
    c_right.fill.solid(); c_right.fill.fore_color.rgb = WHITE
    c_right.line.color.rgb = CARD_BORDER; c_right.line.width = Pt(1.5)

    cr_hdr = s3.shapes.add_textbox(Inches(5.55), Inches(1.70), Inches(7.1), Inches(0.45))
    cr_hp = cr_hdr.text_frame.paragraphs[0]
    cr_hp.text = "• Methodology and process for implementation:"
    cr_hp.font.size = Pt(15); cr_hp.font.bold = True; cr_hp.font.color.rgb = NAVY

    # Architecture Banner
    arch_banner = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.55), Inches(2.15), Inches(7.1), Inches(0.30))
    arch_banner.fill.solid(); arch_banner.fill.fore_color.rgb = DARK_BLUE; arch_banner.line.fill.background()
    ab_p = arch_banner.text_frame.paragraphs[0]
    ab_p.text = "SATQUERY AI: MULTIMODAL EARTH OBSERVATION ARCHITECTURE"
    ab_p.font.size = Pt(9.5); ab_p.font.bold = True; ab_p.font.color.rgb = WHITE; ab_p.alignment = PP_ALIGN.CENTER

    # Layer 1: Client & User Access Layer
    l1_card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.55), Inches(2.55), Inches(7.1), Inches(0.68))
    l1_card.fill.solid(); l1_card.fill.fore_color.rgb = RGBColor(242, 247, 255)
    l1_card.line.color.rgb = RGBColor(170, 205, 245); l1_card.line.width = Pt(1.0)
    l1_tf = l1_card.text_frame; l1_tf.word_wrap = True; l1_tf.margin_top = Inches(0.04)
    l1_p1 = l1_tf.paragraphs[0]; l1_p1.text = "1. USER ACCESS & CLIENT LAYER (React 19 + MapLibre GL GIS)"; l1_p1.font.size = Pt(8.5); l1_p1.font.bold = True; l1_p1.font.color.rgb = PRIMARY_BLUE
    l1_p2 = l1_tf.add_paragraph(); l1_p2.text = "[🚨 NDRF Disaster Portal] [🌊 Jal Shakti Hydrology] [🏙️ Municipal Urban Sprawl] [🌾 Field Agritech Mobile]"; l1_p2.font.size = Pt(7.8); l1_p2.font.color.rgb = DARK_GRAY

    # Arrow 1
    arr1 = s3.shapes.add_textbox(Inches(8.8), Inches(3.22), Inches(0.6), Inches(0.18))
    arr1.text_frame.paragraphs[0].text = "▼"; arr1.text_frame.paragraphs[0].font.size = Pt(8); arr1.text_frame.paragraphs[0].font.color.rgb = PRIMARY_BLUE; arr1.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Layer 2: API Gateway & Geospatial Engine
    l2_card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.55), Inches(3.40), Inches(7.1), Inches(0.68))
    l2_card.fill.solid(); l2_card.fill.fore_color.rgb = RGBColor(245, 248, 252)
    l2_card.line.color.rgb = RGBColor(160, 190, 230); l2_card.line.width = Pt(1.0)
    l2_tf = l2_card.text_frame; l2_tf.word_wrap = True; l2_tf.margin_top = Inches(0.04)
    l2_p1 = l2_tf.paragraphs[0]; l2_p1.text = "2. API GATEWAY & CORE GEOSPATIAL BACKEND (FastAPI / Uvicorn)"; l2_p1.font.size = Pt(8.5); l2_p1.font.bold = True; l2_p1.font.color.rgb = DARK_BLUE
    l2_p2 = l2_tf.add_paragraph(); l2_p2.text = "[🔒 RBAC & Query Guard] [🔄 GDAL Dynamic Ingestor] [⚙️ Intent Orchestrator] [📊 ExecutionTracker Audit]"; l2_p2.font.size = Pt(7.8); l2_p2.font.color.rgb = DARK_GRAY

    # Arrow 2
    arr2 = s3.shapes.add_textbox(Inches(8.8), Inches(4.07), Inches(0.6), Inches(0.18))
    arr2.text_frame.paragraphs[0].text = "▼"; arr2.text_frame.paragraphs[0].font.size = Pt(8); arr2.text_frame.paragraphs[0].font.color.rgb = PRIMARY_BLUE; arr2.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Layer 3: Multimodal Intelligence Specialist Engines
    l3_card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.55), Inches(4.25), Inches(7.1), Inches(0.72))
    l3_card.fill.solid(); l3_card.fill.fore_color.rgb = RGBColor(248, 245, 255)
    l3_card.line.color.rgb = RGBColor(210, 190, 245); l3_card.line.width = Pt(1.0)
    l3_tf = l3_card.text_frame; l3_tf.word_wrap = True; l3_tf.margin_top = Inches(0.04)
    l3_p1 = l3_tf.paragraphs[0]; l3_p1.text = "3. MULTIMODAL INTELLIGENCE LAYER (Specialist AI & Spectral Engines)"; l3_p1.font.size = Pt(8.5); l3_p1.font.bold = True; l3_p1.font.color.rgb = PURPLE
    l3_p2 = l3_tf.add_paragraph(); l3_p2.text = "[🧠 BLIP RS-VQA & Grounder (BigEarthNet)] ◀▶ [🛰️ Optical+SAR Fusion] ◀▶ [📊 Bi-Temporal Change Engine]"; l3_p2.font.size = Pt(7.8); l3_p2.font.color.rgb = DARK_GRAY

    # Arrow 3
    arr3 = s3.shapes.add_textbox(Inches(8.8), Inches(4.96), Inches(0.6), Inches(0.18))
    arr3.text_frame.paragraphs[0].text = "▼"; arr3.text_frame.paragraphs[0].font.size = Pt(8); arr3.text_frame.paragraphs[0].font.color.rgb = PRIMARY_BLUE; arr3.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

    # Layer 4 & 5: Persistence & Interoperability
    l4_card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.55), Inches(5.14), Inches(3.45), Inches(0.70))
    l4_card.fill.solid(); l4_card.fill.fore_color.rgb = RGBColor(243, 252, 246)
    l4_card.line.color.rgb = RGBColor(170, 225, 190); l4_card.line.width = Pt(1.0)
    l4_tf = l4_card.text_frame; l4_tf.word_wrap = True; l4_tf.margin_top = Inches(0.04)
    l4_p1 = l4_tf.paragraphs[0]; l4_p1.text = "4. PERSISTENCE LAYER"; l4_p1.font.size = Pt(8.2); l4_p1.font.bold = True; l4_p1.font.color.rgb = GREEN
    l4_p2 = l4_tf.add_paragraph(); l4_p2.text = "• Local GeoTIFF Store (C-SAR/Optical)\n• Tile Cache & Spatio-Temporal Queries"; l4_p2.font.size = Pt(7.4); l4_p2.font.color.rgb = DARK_GRAY

    l5_card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(9.20), Inches(5.14), Inches(3.45), Inches(0.70))
    l5_card.fill.solid(); l5_card.fill.fore_color.rgb = RGBColor(255, 249, 243)
    l5_card.line.color.rgb = RGBColor(250, 200, 160); l5_card.line.width = Pt(1.0)
    l5_tf = l5_card.text_frame; l5_tf.word_wrap = True; l5_tf.margin_top = Inches(0.04)
    l5_p1 = l5_tf.paragraphs[0]; l5_p1.text = "5. SPACE INTEROPERABILITY"; l5_p1.font.size = Pt(8.2); l5_p1.font.bold = True; l5_p1.font.color.rgb = ORANGE
    l5_p2 = l5_tf.add_paragraph(); l5_p2.text = "• ISRO Bhuvan & Bhoonidhi (LISS/RISAT)\n• Copernicus CDSE (Sentinel-1/2 OData)"; l5_p2.font.size = Pt(7.4); l5_p2.font.color.rgb = DARK_GRAY

    # Bottom Goal & Trust Callout
    callout = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.55), Inches(5.95), Inches(7.1), Inches(0.65))
    callout.fill.solid(); callout.fill.fore_color.rgb = RGBColor(246, 248, 252)
    callout.line.color.rgb = RGBColor(190, 205, 225); callout.line.width = Pt(1.0)
    c_tf = callout.text_frame; c_tf.word_wrap = True; c_tf.margin_top = Inches(0.04)
    c_p1 = c_tf.paragraphs[0]; c_p1.text = "🎯 Verification & Evidence Flow: Zero Hallucination Guarantee"; c_p1.font.size = Pt(8.5); c_p1.font.bold = True; c_p1.font.color.rgb = NAVY; c_p1.alignment = PP_ALIGN.CENTER
    c_p2 = c_tf.add_paragraph(); c_p2.text = "Deterministic capability router maps queries to specialist engines -> Pairs all answers with spatial GeoJSON masks, calibrated confidence scores (84-98%), and exportable audit logs."; c_p2.font.size = Pt(7.5); c_p2.font.color.rgb = DARK_GRAY; c_p2.alignment = PP_ALIGN.CENTER

    # Footer
    fbar = s3.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(6.9), Inches(13.333), Inches(0.6))
    fbar.fill.solid(); fbar.fill.fore_color.rgb = PRIMARY_BLUE; fbar.line.fill.background()

    ftxt_l = s3.shapes.add_textbox(Inches(0.6), Inches(6.95), Inches(8.0), Inches(0.5))
    ftxt_l.text_frame.text = "@SIH Idea submission- Template"
    ftxt_l.text_frame.paragraphs[0].font.color.rgb = WHITE
    ftxt_l.text_frame.paragraphs[0].font.size = Pt(12)

    ftxt_r = s3.shapes.add_textbox(Inches(12.0), Inches(6.95), Inches(1.0), Inches(0.5))
    ftxt_r.text_frame.text = "3"
    ftxt_r.text_frame.paragraphs[0].font.color.rgb = WHITE
    ftxt_r.text_frame.paragraphs[0].font.size = Pt(14)
    ftxt_r.text_frame.paragraphs[0].font.bold = True

def update_presentation():
    pptx_path = r"d:\PROJECTS-PUPU\satquery-ai\SatQuery_AI_SIH26167_Presentation.pptx"
    prs = Presentation(pptx_path) if os.path.exists(pptx_path) else Presentation()
    if not os.path.exists(pptx_path):
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]
    s3 = prs.slides.add_slide(blank_layout)
    build_slide3_architecture(prs, s3)
    prs.save(pptx_path)
    print("Slide 3 regenerated with side-by-side Technologies + Visual Architecture!")

if __name__ == "__main__":
    update_presentation()
