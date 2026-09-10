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

    # 1. TOP TITLE
    tb_title = s3.shapes.add_textbox(Inches(0.5), Inches(0.20), Inches(9.8), Inches(0.42))
    p_t = tb_title.text_frame.paragraphs[0]
    p_t.text = "TECHNICAL APPROACH"
    p_t.font.size = Pt(22)
    p_t.font.bold = True
    p_t.font.color.rgb = DARK_GRAY
    p_t.alignment = PP_ALIGN.CENTER

    # Top Right SIH Logo / Badge
    sih_box = s3.shapes.add_textbox(Inches(10.55), Inches(0.15), Inches(2.3), Inches(0.70))
    sp = sih_box.text_frame.paragraphs[0]
    sp.text = "SMART INDIA\nHACKATHON 2026"
    sp.font.size = Pt(13)
    sp.font.bold = True
    sp.font.color.rgb = NAVY
    sp.alignment = PP_ALIGN.CENTER

    # Subtitle Banner with pulse decoration
    sub_box = s3.shapes.add_textbox(Inches(0.5), Inches(0.62), Inches(9.8), Inches(0.35))
    sp_sub = sub_box.text_frame.paragraphs[0]
    sp_sub.text = "⚡ SATQUERY AI ARCHITECTURE: MULTIMODAL EARTH OBSERVATION & INTELLIGENCE FLOW ⚡"
    sp_sub.font.size = Pt(11.5)
    sp_sub.font.bold = True
    sp_sub.font.color.rgb = NAVY
    sp_sub.alignment = PP_ALIGN.CENTER

    # -------------------------------------------------------------
    # LAYER 1: USER ACCESS & CLIENT LAYER
    # -------------------------------------------------------------
    l1_box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), Inches(1.02), Inches(9.8), Inches(1.02))
    l1_box.fill.solid(); l1_box.fill.fore_color.rgb = RGBColor(242, 247, 255)
    l1_box.line.color.rgb = RGBColor(170, 205, 245); l1_box.line.width = Pt(1.5)

    # Header Tab
    l1_hdr = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2.3), Inches(1.05), Inches(6.2), Inches(0.24))
    l1_hdr.fill.solid(); l1_hdr.fill.fore_color.rgb = PRIMARY_BLUE
    l1_hdr.line.fill.background()
    l1_hp = l1_hdr.text_frame.paragraphs[0]
    l1_hp.text = "1. USER ACCESS & CLIENT LAYER   built with React 19, Vite, TypeScript & Tailwind CSS"
    l1_hp.font.size = Pt(9.2); l1_hp.font.bold = True; l1_hp.font.color.rgb = WHITE; l1_hp.alignment = PP_ALIGN.CENTER

    # 5 Client Persona Cards
    personas = [
        ("🚨 Disaster Responders", "NDRF / SDMA View\n(Flood & Crisis Rescue)"),
        ("🌊 Water Authorities", "Jal Shakti Portal\n(Reservoir & Hydrology)"),
        ("🏙️ Urban Planners", "Municipal Dashboard\n(Sprawl & Encroachment)"),
        ("🌾 Field Officers", "Mobile Agritech\n(Crop Canopy & Drought)"),
        ("🛡️ Defense & Maritime", "ISRO / SAC Systems\n(SAR Coastal Security)")
    ]

    p_w = Inches(1.84)
    p_gap = Inches(0.08)
    for i, (p_title, p_desc) in enumerate(personas):
        px = Inches(0.60) + i * (p_w + p_gap)
        p_card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, px, Inches(1.33), p_w, Inches(0.65))
        p_card.fill.solid(); p_card.fill.fore_color.rgb = WHITE
        p_card.line.color.rgb = RGBColor(200, 220, 245); p_card.line.width = Pt(1.0)

        tf = p_card.text_frame; tf.word_wrap = True
        tf.margin_top = Inches(0.04); tf.margin_bottom = Inches(0.04)
        tf.margin_left = Inches(0.06); tf.margin_right = Inches(0.06)

        p1 = tf.paragraphs[0]; p1.text = p_title; p1.font.size = Pt(8.8); p1.font.bold = True; p1.font.color.rgb = NAVY; p1.alignment = PP_ALIGN.CENTER
        p2 = tf.add_paragraph(); p2.text = p_desc; p2.font.size = Pt(7.8); p2.font.color.rgb = DARK_GRAY; p2.alignment = PP_ALIGN.CENTER

    # Connecting Arrow Down to Layer 2
    arr1 = s3.shapes.add_textbox(Inches(4.9), Inches(2.04), Inches(1.0), Inches(0.20))
    ap1 = arr1.text_frame.paragraphs[0]; ap1.text = "▼  ▼  ▼"; ap1.font.size = Pt(8); ap1.font.bold = True; ap1.font.color.rgb = PRIMARY_BLUE; ap1.alignment = PP_ALIGN.CENTER

    # -------------------------------------------------------------
    # LAYER 2: API GATEWAY & CORE BACKEND
    # -------------------------------------------------------------
    l2_box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), Inches(2.24), Inches(9.8), Inches(1.02))
    l2_box.fill.solid(); l2_box.fill.fore_color.rgb = RGBColor(245, 248, 252)
    l2_box.line.color.rgb = RGBColor(160, 190, 230); l2_box.line.width = Pt(1.5)

    l2_hdr = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2.6), Inches(2.27), Inches(5.6), Inches(0.24))
    l2_hdr.fill.solid(); l2_hdr.fill.fore_color.rgb = DARK_BLUE
    l2_hdr.line.fill.background()
    l2_hp = l2_hdr.text_frame.paragraphs[0]
    l2_hp.text = "2. API GATEWAY & CORE GEOSPATIAL BACKEND (FastAPI / Uvicorn)"
    l2_hp.font.size = Pt(9.5); l2_hp.font.bold = True; l2_hp.font.color.rgb = WHITE; l2_hp.alignment = PP_ALIGN.CENTER

    backend_cards = [
        ("🔒 RBAC & Query Guard", "Sanitizes inputs,\nenforces CRS rules"),
        ("🔄 Raster Ingestion", "Auto-reprojects CRS,\ncalibrates bands (GDAL)"),
        ("⚙️ Agent Orchestrator", "Intent parsing &\nmodel routing registry"),
        ("</> REST API Flow", "FastAPI endpoints &\nGeoJSON raster streams")
    ]

    b_w = Inches(1.60)
    b_gap = Inches(0.08)
    for i, (b_title, b_desc) in enumerate(backend_cards):
        bx = Inches(0.60) + i * (b_w + b_gap)
        b_card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bx, Inches(2.55), b_w, Inches(0.65))
        b_card.fill.solid(); b_card.fill.fore_color.rgb = WHITE
        b_card.line.color.rgb = RGBColor(190, 210, 235); b_card.line.width = Pt(1.0)

        tf = b_card.text_frame; tf.word_wrap = True
        tf.margin_top = Inches(0.04); tf.margin_bottom = Inches(0.04)
        tf.margin_left = Inches(0.05); tf.margin_right = Inches(0.05)

        p1 = tf.paragraphs[0]; p1.text = b_title; p1.font.size = Pt(8.5); p1.font.bold = True; p1.font.color.rgb = NAVY; p1.alignment = PP_ALIGN.CENTER
        p2 = tf.add_paragraph(); p2.text = b_desc; p2.font.size = Pt(7.5); p2.font.color.rgb = DARK_GRAY; p2.alignment = PP_ALIGN.CENTER

    # Side Box: Automated Audit & Telemetry Delivery
    side_box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.35), Inches(2.55), Inches(2.85), Inches(0.65))
    side_box.fill.solid(); side_box.fill.fore_color.rgb = RGBColor(238, 244, 255)
    side_box.line.color.rgb = PRIMARY_BLUE; side_box.line.width = Pt(1.2)
    s_tf = side_box.text_frame; s_tf.word_wrap = True
    s_tf.margin_top = Inches(0.03); s_tf.margin_bottom = Inches(0.03)
    s_p1 = s_tf.paragraphs[0]; s_p1.text = "📊 ExecutionTracker (Automated Delivery)"; s_p1.font.size = Pt(8.5); s_p1.font.bold = True; s_p1.font.color.rgb = DARK_BLUE; s_p1.alignment = PP_ALIGN.CENTER
    s_p2 = s_tf.add_paragraph(); s_p2.text = "• Exportable JSON Audit  • SHA-256 Hashes\n• <300ms CPU Profiling  • Mask GeoJSON"; s_p2.font.size = Pt(7.5); s_p2.font.color.rgb = DARK_GRAY; s_p2.alignment = PP_ALIGN.CENTER

    # Connecting Arrow Down to Layer 3
    arr2 = s3.shapes.add_textbox(Inches(4.9), Inches(3.26), Inches(1.0), Inches(0.20))
    ap2 = arr2.text_frame.paragraphs[0]; ap2.text = "▼  ▼  ▼"; ap2.font.size = Pt(8); ap2.font.bold = True; ap2.font.color.rgb = PRIMARY_BLUE; ap2.alignment = PP_ALIGN.CENTER

    # -------------------------------------------------------------
    # LAYER 3: MULTIMODAL INTELLIGENCE LAYER
    # -------------------------------------------------------------
    l3_box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), Inches(3.46), Inches(9.8), Inches(1.02))
    l3_box.fill.solid(); l3_box.fill.fore_color.rgb = RGBColor(248, 245, 255)
    l3_box.line.color.rgb = RGBColor(210, 190, 245); l3_box.line.width = Pt(1.5)

    l3_hdr = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2.4), Inches(3.49), Inches(6.0), Inches(0.24))
    l3_hdr.fill.solid(); l3_hdr.fill.fore_color.rgb = PURPLE
    l3_hdr.line.fill.background()
    l3_hp = l3_hdr.text_frame.paragraphs[0]
    l3_hp.text = "3. MULTIMODAL INTELLIGENCE LAYER (Specialist AI & Spectral Engines)"
    l3_hp.font.size = Pt(9.5); l3_hp.font.bold = True; l3_hp.font.color.rgb = WHITE; l3_hp.alignment = PP_ALIGN.CENTER

    ai_modules = [
        ("🧠 BLIP RS-VQA & Grounder", "Fine-tuned on BigEarthNet\nOpen-vocabulary grounding & VQA"),
        ("🛰️ Optical + SAR Fusion Tool", "Cloud-penetrating radar C-SAR\nBackscatter + Specular water agreement"),
        ("📊 Bi-Temporal Change Engine", "Radiometric differential raster math\nPixel anomaly area calculation")
    ]

    m_w = Inches(3.02)
    m_gap = Inches(0.26)
    for i, (m_title, m_desc) in enumerate(ai_modules):
        mx = Inches(0.62) + i * (m_w + m_gap)
        m_card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, mx, Inches(3.77), m_w, Inches(0.65))
        m_card.fill.solid(); m_card.fill.fore_color.rgb = WHITE
        m_card.line.color.rgb = RGBColor(215, 195, 245); m_card.line.width = Pt(1.2)

        tf = m_card.text_frame; tf.word_wrap = True
        tf.margin_top = Inches(0.04); tf.margin_bottom = Inches(0.04)
        tf.margin_left = Inches(0.06); tf.margin_right = Inches(0.06)

        p1 = tf.paragraphs[0]; p1.text = m_title; p1.font.size = Pt(8.8); p1.font.bold = True; p1.font.color.rgb = PURPLE; p1.alignment = PP_ALIGN.CENTER
        p2 = tf.add_paragraph(); p2.text = m_desc; p2.font.size = Pt(7.8); p2.font.color.rgb = DARK_GRAY; p2.alignment = PP_ALIGN.CENTER

    # Bidirectional arrows between AI modules
    arr_b1 = s3.shapes.add_textbox(Inches(3.64), Inches(3.90), Inches(0.30), Inches(0.30))
    arr_b1.text_frame.paragraphs[0].text = "◀▶"; arr_b1.text_frame.paragraphs[0].font.size = Pt(9); arr_b1.text_frame.paragraphs[0].font.color.rgb = PURPLE

    arr_b2 = s3.shapes.add_textbox(Inches(6.92), Inches(3.90), Inches(0.30), Inches(0.30))
    arr_b2.text_frame.paragraphs[0].text = "◀▶"; arr_b2.text_frame.paragraphs[0].font.size = Pt(9); arr_b2.text_frame.paragraphs[0].font.color.rgb = PURPLE

    # -------------------------------------------------------------
    # LAYER 4 & 5: DUAL PERSISTENCE & INTEROPERABILITY
    # -------------------------------------------------------------
    # Layer 4 (Left: Green)
    l4_box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), Inches(4.55), Inches(4.75), Inches(0.92))
    l4_box.fill.solid(); l4_box.fill.fore_color.rgb = RGBColor(243, 252, 246)
    l4_box.line.color.rgb = RGBColor(170, 225, 190); l4_box.line.width = Pt(1.5)

    l4_hdr = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(4.58), Inches(4.15), Inches(0.22))
    l4_hdr.fill.solid(); l4_hdr.fill.fore_color.rgb = GREEN
    l4_hdr.line.fill.background()
    l4_hp = l4_hdr.text_frame.paragraphs[0]
    l4_hp.text = "4. PERSISTENCE LAYER (Hybrid Storage)"
    l4_hp.font.size = Pt(9.0); l4_hp.font.bold = True; l4_hp.font.color.rgb = WHITE; l4_hp.alignment = PP_ALIGN.CENTER

    c4a = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.62), Inches(4.84), Inches(2.20), Inches(0.57))
    c4a.fill.solid(); c4a.fill.fore_color.rgb = WHITE; c4a.line.color.rgb = RGBColor(180, 225, 200); c4a.line.width = Pt(1.0)
    c4a_tf = c4a.text_frame; c4a_tf.word_wrap = True; c4a_tf.margin_top = Inches(0.04)
    c4a_tf.paragraphs[0].text = "🗄️ Local GeoTIFF Store"; c4a_tf.paragraphs[0].font.size = Pt(8.5); c4a_tf.paragraphs[0].font.bold = True; c4a_tf.paragraphs[0].font.color.rgb = GREEN; c4a_tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    p = c4a_tf.add_paragraph(); p.text = "Multispectral & SAR Rasters"; p.font.size = Pt(7.5); p.font.color.rgb = DARK_GRAY; p.alignment = PP_ALIGN.CENTER

    c4b = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2.92), Inches(4.84), Inches(2.20), Inches(0.57))
    c4b.fill.solid(); c4b.fill.fore_color.rgb = WHITE; c4b.line.color.rgb = RGBColor(180, 225, 200); c4b.line.width = Pt(1.0)
    c4b_tf = c4b.text_frame; c4b_tf.word_wrap = True; c4b_tf.margin_top = Inches(0.04)
    c4b_tf.paragraphs[0].text = "⚡ Tile Cache & Audit DB"; c4b_tf.paragraphs[0].font.size = Pt(8.5); c4b_tf.paragraphs[0].font.bold = True; c4b_tf.paragraphs[0].font.color.rgb = GREEN; c4b_tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    p = c4b_tf.add_paragraph(); p.text = "Indexed Spatial Queries"; p.font.size = Pt(7.5); p.font.color.rgb = DARK_GRAY; p.alignment = PP_ALIGN.CENTER

    # Layer 5 (Right: Orange)
    l5_box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.55), Inches(4.55), Inches(4.75), Inches(0.92))
    l5_box.fill.solid(); l5_box.fill.fore_color.rgb = RGBColor(255, 249, 243)
    l5_box.line.color.rgb = RGBColor(250, 200, 160); l5_box.line.width = Pt(1.5)

    l5_hdr = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.85), Inches(4.58), Inches(4.15), Inches(0.22))
    l5_hdr.fill.solid(); l5_hdr.fill.fore_color.rgb = ORANGE
    l5_hdr.line.fill.background()
    l5_hp = l5_hdr.text_frame.paragraphs[0]
    l5_hp.text = "5. INTEROPERABILITY LAYER (Standardized Exchange)"
    l5_hp.font.size = Pt(9.0); l5_hp.font.bold = True; l5_hp.font.color.rgb = WHITE; l5_hp.alignment = PP_ALIGN.CENTER

    c5a = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.67), Inches(4.84), Inches(2.20), Inches(0.57))
    c5a.fill.solid(); c5a.fill.fore_color.rgb = WHITE; c5a.line.color.rgb = RGBColor(245, 210, 180); c5a.line.width = Pt(1.0)
    c5a_tf = c5a.text_frame; c5a_tf.word_wrap = True; c5a_tf.margin_top = Inches(0.04)
    c5a_tf.paragraphs[0].text = "🛰️ ISRO Bhuvan / Bhoonidhi"; c5a_tf.paragraphs[0].font.size = Pt(8.5); c5a_tf.paragraphs[0].font.bold = True; c5a_tf.paragraphs[0].font.color.rgb = ORANGE; c5a_tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    p = c5a_tf.add_paragraph(); p.text = "Resourcesat, Cartosat, RISAT"; p.font.size = Pt(7.5); p.font.color.rgb = DARK_GRAY; p.alignment = PP_ALIGN.CENTER

    c5b = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.97), Inches(4.84), Inches(2.20), Inches(0.57))
    c5b.fill.solid(); c5b.fill.fore_color.rgb = WHITE; c5b.line.color.rgb = RGBColor(245, 210, 180); c5b.line.width = Pt(1.0)
    c5b_tf = c5b.text_frame; c5b_tf.word_wrap = True; c5b_tf.margin_top = Inches(0.04)
    c5b_tf.paragraphs[0].text = "🌍 Copernicus CDSE Gateway"; c5b_tf.paragraphs[0].font.size = Pt(8.5); c5b_tf.paragraphs[0].font.bold = True; c5b_tf.paragraphs[0].font.color.rgb = ORANGE; c5b_tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    p = c5b_tf.add_paragraph(); p.text = "Sentinel-1 SAR, Sentinel-2 MSI"; p.font.size = Pt(7.5); p.font.color.rgb = DARK_GRAY; p.alignment = PP_ALIGN.CENTER

    # -------------------------------------------------------------
    # BOTTOM SUMMARY BADGES (5 Pill Badges)
    # -------------------------------------------------------------
    pills = [
        ("🌐 Unified Access", "Cross-departmental GIS"),
        ("🧠 Zero Hallucination", "Strict deterministic routing"),
        ("🔒 Air-Gapped Secure", "100% on-premise execution"),
        ("🛰️ Multi-Sensor Fusion", "Optical + SAR co-analysis"),
        ("⚡ <300ms Latency", "Standard CPU inference")
    ]
    pill_w = Inches(1.84)
    pill_gap = Inches(0.08)
    for i, (p_title, p_sub) in enumerate(pills):
        px = Inches(0.60) + i * (pill_w + pill_gap)
        pill = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, px, Inches(5.53), pill_w, Inches(0.40))
        pill.fill.solid(); pill.fill.fore_color.rgb = WHITE
        pill.line.color.rgb = RGBColor(200, 215, 235); pill.line.width = Pt(1.0)
        ptf = pill.text_frame; ptf.word_wrap = True; ptf.margin_top = Inches(0.02); ptf.margin_bottom = Inches(0.02)
        p1 = ptf.paragraphs[0]; p1.text = p_title; p1.font.size = Pt(8.2); p1.font.bold = True; p1.font.color.rgb = DARK_BLUE; p1.alignment = PP_ALIGN.CENTER
        p2 = ptf.add_paragraph(); p2.text = p_sub; p2.font.size = Pt(7.2); p2.font.color.rgb = LIGHT_GRAY; p2.alignment = PP_ALIGN.CENTER

    # -------------------------------------------------------------
    # GOAL CALLOUT BOX
    # -------------------------------------------------------------
    g_box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), Inches(6.00), Inches(9.8), Inches(0.36))
    g_box.fill.solid(); g_box.fill.fore_color.rgb = RGBColor(246, 248, 252)
    g_box.line.color.rgb = RGBColor(190, 205, 225); g_box.line.width = Pt(1.0)
    gtf = g_box.text_frame; gtf.word_wrap = True; gtf.margin_top = Inches(0.04)
    gp = gtf.paragraphs[0]
    gp.text = "🎯 OUR GOAL: Democratize satellite Earth observation intelligence with zero hallucination and 24/7 all-weather situational awareness."
    gp.font.size = Pt(9.5); gp.font.bold = True; gp.font.color.rgb = NAVY; gp.alignment = PP_ALIGN.CENTER

    # -------------------------------------------------------------
    # RIGHT SIDEBAR: TECHSTACKS USED
    # -------------------------------------------------------------
    r_card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(10.55), Inches(0.95), Inches(2.3), Inches(5.41))
    r_card.fill.solid(); r_card.fill.fore_color.rgb = WHITE
    r_card.line.color.rgb = CARD_BORDER; r_card.line.width = Pt(1.5)

    rtb = s3.shapes.add_textbox(Inches(10.6), Inches(1.02), Inches(2.2), Inches(0.38))
    rp = rtb.text_frame.paragraphs[0]
    rp.text = "Techstacks Used"
    rp.font.size = Pt(15); rp.font.bold = True; rp.font.color.rgb = DARK_GRAY; rp.alignment = PP_ALIGN.CENTER

    tech_stack_items = [
        ("🐍 Python 3.11", "Backend AI & Engines", RGBColor(53, 114, 165)),
        ("⚡ FastAPI", "Async RESTful Framework", RGBColor(5, 153, 138)),
        ("⚛️ React 19", "Modern Interactive UI", RGBColor(0, 180, 216)),
        ("🗺️ MapLibre GL", "WebGL Vector Map Engine", RGBColor(30, 144, 255)),
        ("🎨 Tailwind CSS", "Utility-First Design", RGBColor(14, 165, 233)),
        ("🔥 PyTorch", "Deep Learning & VLM", RGBColor(238, 76, 44)),
        ("🌐 GDAL / Rasterio", "Geospatial Raster Math", RGBColor(76, 175, 80)),
        ("🤗 Transformers", "BLIP VQA & Grounding", RGBColor(255, 179, 0))
    ]

    r_start_y = Inches(1.48)
    r_gap = Inches(0.59)
    for i, (t_name, t_role, t_color) in enumerate(tech_stack_items):
        ry = r_start_y + i * r_gap
        # Little colored icon container
        ic_box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(10.70), ry, Inches(2.0), Inches(0.50))
        ic_box.fill.solid(); ic_box.fill.fore_color.rgb = RGBColor(250, 252, 255)
        ic_box.line.color.rgb = t_color; ic_box.line.width = Pt(1.0)

        tf = ic_box.text_frame; tf.word_wrap = True
        tf.margin_top = Inches(0.04); tf.margin_bottom = Inches(0.02)
        tf.margin_left = Inches(0.06); tf.margin_right = Inches(0.06)

        p1 = tf.paragraphs[0]; p1.text = t_name; p1.font.size = Pt(9.5); p1.font.bold = True; p1.font.color.rgb = DARK_GRAY
        p2 = tf.add_paragraph(); p2.text = t_role; p2.font.size = Pt(7.5); p2.font.color.rgb = LIGHT_GRAY

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
    print("Slide 3 regenerated with Health-System style architecture diagram!")

if __name__ == "__main__":
    update_presentation()
