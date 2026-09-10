import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def build_perfect_sih_deck():
    output_path = r"d:\PROJECTS-PUPU\satquery-ai\SatQuery_AI_SIH26167_Official_6Slides.pptx"
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Color Palette matching official template image
    NAVY = RGBColor(11, 44, 91)
    SIH_BLUE = RGBColor(13, 110, 204)       # The exact bright blue from the template header & footer
    DARK_GRAY = RGBColor(33, 37, 41)
    LIGHT_BG = RGBColor(248, 249, 250)
    CARD_BORDER = RGBColor(218, 224, 233)
    WHITE = RGBColor(255, 255, 255)
    PURPLE = RGBColor(128, 0, 128)

    def add_template_header_and_footer(slide, title_text, slide_num):
        # 1. Top Left: Oval with "Your Team Name"
        oval = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.45), Inches(0.18), Inches(1.85), Inches(1.1))
        oval.fill.solid(); oval.fill.fore_color.rgb = WHITE
        oval.line.color.rgb = PURPLE; oval.line.width = Pt(1.8)
        otf = oval.text_frame; otf.word_wrap = True
        p1 = otf.paragraphs[0]; p1.text = "Your"; p1.font.size = Pt(11); p1.font.bold = True; p1.font.color.rgb = DARK_GRAY; p1.alignment = PP_ALIGN.CENTER
        p2 = otf.add_paragraph(); p2.text = "Team"; p2.font.size = Pt(11); p2.font.bold = True; p2.font.color.rgb = DARK_GRAY; p2.alignment = PP_ALIGN.CENTER
        p3 = otf.add_paragraph(); p3.text = "Name"; p3.font.size = Pt(11); p3.font.bold = True; p3.font.color.rgb = DARK_GRAY; p3.alignment = PP_ALIGN.CENTER

        # 2. Top Center: IDEA TITLE
        itb = slide.shapes.add_textbox(Inches(2.5), Inches(0.28), Inches(8.3), Inches(0.9))
        itf = itb.text_frame; itf.word_wrap = True
        ip = itf.paragraphs[0]
        ip.text = title_text
        ip.font.size = Pt(25 if len(title_text) > 30 else 30); ip.font.bold = True; ip.font.color.rgb = DARK_GRAY
        ip.alignment = PP_ALIGN.CENTER

        # 3. Top Right: SIH 2026 Badge
        sih_box = slide.shapes.add_textbox(Inches(10.8), Inches(0.18), Inches(2.2), Inches(1.0))
        stf = sih_box.text_frame
        sp1 = stf.paragraphs[0]; sp1.text = "SMART INDIA"; sp1.font.size = Pt(14); sp1.font.bold = True; sp1.font.color.rgb = NAVY; sp1.alignment = PP_ALIGN.RIGHT
        sp2 = stf.add_paragraph(); sp2.text = "HACKATHON"; sp2.font.size = Pt(14); sp2.font.bold = True; sp2.font.color.rgb = NAVY; sp2.alignment = PP_ALIGN.RIGHT
        sp3 = stf.add_paragraph(); sp3.text = "2026"; sp3.font.size = Pt(14); sp3.font.bold = True; sp3.font.color.rgb = NAVY; sp3.alignment = PP_ALIGN.RIGHT

        # 4. Bottom: Solid Blue Footer Bar (Exact match to template image)
        fbar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(6.88), Inches(13.333), Inches(0.62))
        fbar.fill.solid(); fbar.fill.fore_color.rgb = SIH_BLUE; fbar.line.fill.background()

        # Center Text on Footer
        f_txt = slide.shapes.add_textbox(Inches(1.0), Inches(6.92), Inches(11.333), Inches(0.48))
        ftp = f_txt.text_frame.paragraphs[0]
        ftp.text = "@SIH Idea submission- Template"
        ftp.font.size = Pt(11.5); ftp.font.color.rgb = WHITE; ftp.alignment = PP_ALIGN.CENTER

        # Slide number on right of footer
        f_num = slide.shapes.add_textbox(Inches(12.2), Inches(6.92), Inches(0.8), Inches(0.48))
        fnp = f_num.text_frame.paragraphs[0]
        fnp.text = str(slide_num)
        fnp.font.size = Pt(12.5); fnp.font.bold = True; fnp.font.color.rgb = WHITE; fnp.alignment = PP_ALIGN.RIGHT

    # =========================================================================
    # SLIDE 1: TITLE SLIDE (Official SIH Format)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    top_accent = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.35))
    top_accent.fill.solid(); top_accent.fill.fore_color.rgb = NAVY; top_accent.line.fill.background()

    card_s1 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.7), Inches(11.733), Inches(5.8))
    card_s1.fill.solid(); card_s1.fill.fore_color.rgb = LIGHT_BG
    card_s1.line.color.rgb = CARD_BORDER; card_s1.line.width = Pt(1.5)

    tb1 = s1.shapes.add_textbox(Inches(1.1), Inches(0.85), Inches(11.133), Inches(5.4))
    tf1 = tb1.text_frame; tf1.word_wrap = True

    p = tf1.paragraphs[0]
    p.text = "SatQuery AI"
    p.font.size = Pt(40); p.font.bold = True; p.font.color.rgb = NAVY; p.alignment = PP_ALIGN.CENTER

    p2 = tf1.add_paragraph()
    p2.text = "An Interactive Vision-Language Assistant for Multimodal Remote Sensing Image Analysis through Text Queries"
    p2.font.size = Pt(16.5); p2.font.bold = True; p2.font.color.rgb = SIH_BLUE; p2.alignment = PP_ALIGN.CENTER; p2.space_before = Pt(6)

    p_tag = tf1.add_paragraph()
    p_tag.text = "SMART INDIA HACKATHON 2026 | IDEA SUBMISSION"
    p_tag.font.size = Pt(13); p_tag.font.bold = True; p_tag.font.color.rgb = PURPLE; p_tag.alignment = PP_ALIGN.CENTER; p_tag.space_before = Pt(14)

    s1_metadata = [
        ("Problem Statement ID:", "SIH26167"),
        ("Problem Statement Title:", "Interactive Vision-Language Assistant for Multimodal Remote Sensing Image Analysis"),
        ("Category / Theme:", "Space Technology / Disaster Management / Water Resources"),
        ("Aligned Ministries/Agencies:", "ISRO / Space Applications Centre (SAC) & Ministry of Jal Shakti"),
        ("Team Name:", "Your Team Name"),
        ("Team Leader & Members:", "Team Leader (Leader) | Member 1 | Member 2 | Member 3 | Member 4 | Member 5"),
        ("College / Institute Name:", "Your College / University Name, City, State"),
    ]

    for label, val in s1_metadata:
        p_row = tf1.add_paragraph()
        p_row.space_before = Pt(6)
        r1 = p_row.add_run(); r1.text = f"{label} "; r1.font.bold = True; r1.font.size = Pt(12); r1.font.color.rgb = DARK_GRAY
        r2 = p_row.add_run(); r2.text = val; r2.font.size = Pt(12); r2.font.color.rgb = NAVY if "SIH" in val or "ISRO" in val else DARK_GRAY

    # Footer slide 1
    fbar1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(6.88), Inches(13.333), Inches(0.62))
    fbar1.fill.solid(); fbar1.fill.fore_color.rgb = SIH_BLUE; fbar1.line.fill.background()
    f1_txt = s1.shapes.add_textbox(Inches(1.0), Inches(6.92), Inches(11.333), Inches(0.48))
    f1_txt.text_frame.paragraphs[0].text = "@SIH Idea submission- Template"
    f1_txt.text_frame.paragraphs[0].font.size = Pt(11.5); f1_txt.text_frame.paragraphs[0].font.color.rgb = WHITE; f1_txt.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    f1_num = s1.shapes.add_textbox(Inches(12.2), Inches(6.92), Inches(0.8), Inches(0.48))
    f1_num.text_frame.paragraphs[0].text = "1"; f1_num.text_frame.paragraphs[0].font.size = Pt(12.5); f1_num.text_frame.paragraphs[0].font.bold = True; f1_num.text_frame.paragraphs[0].font.color.rgb = WHITE; f1_num.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT

    # =========================================================================
    # SLIDE 2: EXACT SIH TEMPLATE - PROPOSED SOLUTION
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_template_header_and_footer(s2, "SatQuery AI: Interactive Multimodal RS Assistant", 2)

    # Big Template Underlined Section Header (Exactly like the image)
    hdr_box = s2.shapes.add_textbox(Inches(0.5), Inches(1.45), Inches(12.333), Inches(0.6))
    hf = hdr_box.text_frame
    hp = hf.paragraphs[0]
    hrun = hp.add_run()
    hrun.text = "❖ Proposed Solution (Describe your Idea/Solution/Prototype)"
    hrun.font.size = Pt(23); hrun.font.bold = True; hrun.font.underline = True; hrun.font.color.rgb = SIH_BLUE

    # 3 Distinct Columns / Visual Cards corresponding directly to the template pointers:
    # Pointer 1: Detailed explanation of the proposed solution
    # Pointer 2: How it addresses the problem
    # Pointer 3: Innovation and uniqueness of the solution
    col_w = Inches(3.95)
    gap = Inches(0.24)
    c_top = Inches(2.2)
    c_h = Inches(4.45)

    s2_sections = [
        ("• Detailed explanation of the proposed solution", [
            ("Agentic AI Assistant: ", "Translates natural-language text questions into multi-spectral satellite analytics without requiring manual GIS tooling."),
            ("7 Specialist AI Engines: ", "Integrates fine-tuned BLIP VQA, dense scene captioning, text-guided grounding, change detection, Optical+SAR fusion, NDWI, and NDBI."),
            ("Multi-Sensor Ingestion: ", "Natively ingests single GeoTIFFs, bi-temporal pairs, and optical+radar stacks while preserving real CRS georeferencing and spectral bit-depth."),
            ("Interactive Map Canvas: ", "Delivers human-readable answers coupled with interactive MapLibre GL map layers (bounding boxes, pixel masks, and bi-temporal swipe wipes).")
        ]),
        ("• How it addresses the problem", [
            ("Democratizes Space Data: ", "Enables hydrologists, disaster teams, and planners to query complex satellite data in plain English without learning GIS software."),
            ("All-Weather Continuity: ", "Combines optical scenes with Sentinel-1 / RISAT C-band SAR radar to penetrate monsoon cloud cover and heavy haze during disasters."),
            ("Sub-Second Turnaround: ", "Cuts geospatial turnaround time from hours to milliseconds (<70ms for spectral tools, <260ms for multimodal fusion)."),
            ("Automated Preprocessing: ", "Auto-reprojects coordinate systems (EPSG), scales 16-bit to 8-bit dynamic contrast, and co-registers multi-sensor rasters.")
        ]),
        ("• Innovation and uniqueness of the solution", [
            ("Zero-Hallucination Routing: ", "Deterministic QueryClassifier maps queries strictly to verified capabilities, guaranteeing factual, auditable answers."),
            ("Native ISRO Mission Support: ", "Built-in adapters for Resourcesat-2A (LISS-4 5.8m), Cartosat-2S/3, and RISAT-1A with authentic product metadata."),
            ("Multimodal Optical+SAR Co-Analysis: ", "Simultaneously reasons across optical surface reflectance and calibrated radar backscatter on a single grid."),
            ("Transparent Execution Audit: ", "Every result includes an immutable audit log detailing exact model latency, confidence scores, and parameters.")
        ])
    ]

    for idx, (ptr_title, bullets) in enumerate(s2_sections):
        x_pos = Inches(0.5) + idx * (col_w + gap)
        card = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x_pos, c_top, col_w, c_h)
        card.fill.solid(); card.fill.fore_color.rgb = LIGHT_BG; card.line.color.rgb = CARD_BORDER; card.line.width = Pt(1.5)

        t_card = s2.shapes.add_textbox(x_pos + Inches(0.18), c_top + Inches(0.12), col_w - Inches(0.36), c_h - Inches(0.24))
        t_cf = t_card.text_frame; t_cf.word_wrap = True

        p_th = t_cf.paragraphs[0]
        p_th.text = ptr_title
        p_th.font.size = Pt(13); p_th.font.bold = True; p_th.font.color.rgb = NAVY

        for b_lead, b_body in bullets:
            p_b = t_cf.add_paragraph(); p_b.space_before = Pt(7)
            r_lead = p_b.add_run(); r_lead.text = f"• {b_lead}"; r_lead.font.bold = True; r_lead.font.size = Pt(10.2); r_lead.font.color.rgb = DARK_GRAY
            r_body = p_b.add_run(); r_body.text = b_body; r_body.font.size = Pt(10.2); r_body.font.color.rgb = DARK_GRAY

    # =========================================================================
    # SLIDE 3: EXACT SIH TEMPLATE - TECHNICAL APPROACH
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_template_header_and_footer(s3, "TECHNICAL APPROACH", 3)

    hdr_box3 = s3.shapes.add_textbox(Inches(0.5), Inches(1.45), Inches(12.333), Inches(0.6))
    h3_run = hdr_box3.text_frame.paragraphs[0].add_run()
    h3_run.text = "❖ Technical Approach (Architecture, Stack & Methodology)"
    h3_run.font.size = Pt(23); h3_run.font.bold = True; h3_run.font.underline = True; h3_run.font.color.rgb = SIH_BLUE

    w_card_w = Inches(6.02)
    w_gap = Inches(0.29)

    # Card 1: Technologies to be used (Stack & Hardware)
    c1_s3 = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), c_top, w_card_w, c_h)
    c1_s3.fill.solid(); c1_s3.fill.fore_color.rgb = LIGHT_BG; c1_s3.line.color.rgb = CARD_BORDER; c1_s3.line.width = Pt(1.5)

    tb_s3_1 = s3.shapes.add_textbox(Inches(0.7), c_top + Inches(0.12), w_card_w - Inches(0.4), c_h - Inches(0.24))
    tf_s3_1 = tb_s3_1.text_frame; tf_s3_1.word_wrap = True

    p_s3_1 = tf_s3_1.paragraphs[0]
    p_s3_1.text = "• Technologies to be used (e.g. programming languages, frameworks, hardware)"
    p_s3_1.font.size = Pt(14); p_s3_1.font.bold = True; p_s3_1.font.color.rgb = NAVY

    tech_bullets = [
        ("Languages: ", "Python 3.11 (Backend AI/GIS Engines), TypeScript (Frontend Web App)."),
        ("Frontend GIS: ", "React 19, Vite 8, Tailwind CSS v4, MapLibre GL (@nextgis/ngw-map)."),
        ("Backend & API: ", "FastAPI, Uvicorn ASGI, Pydantic v2 schemas, RESTful OpenAPI/Swagger."),
        ("AI / Vision-Language: ", "PyTorch, Hugging Face Transformers (Fine-tuned BLIP VQA & Grounder)."),
        ("Geospatial Engine: ", "GDAL, Rasterio, NumPy (GeoTIFF, NetCDF, CRS reprojection, band math)."),
        ("Hardware & Portability: ", "Optimized CPU inference (<300ms), optional CUDA GPU acceleration.")
    ]

    for lead, desc in tech_bullets:
        p = tf_s3_1.add_paragraph(); p.space_before = Pt(8)
        r1 = p.add_run(); r1.text = f"• {lead}"; r1.font.bold = True; r1.font.size = Pt(11.0); r1.font.color.rgb = DARK_GRAY
        r2 = p.add_run(); r2.text = desc; r2.font.size = Pt(11.0); r2.font.color.rgb = DARK_GRAY

    # Card 2: Methodology & Implementation Process
    c2_s3 = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5) + w_card_w + w_gap, c_top, w_card_w, c_h)
    c2_s3.fill.solid(); c2_s3.fill.fore_color.rgb = LIGHT_BG; c2_s3.line.color.rgb = CARD_BORDER; c2_s3.line.width = Pt(1.5)

    tb_s3_2 = s3.shapes.add_textbox(Inches(0.5) + w_card_w + w_gap + Inches(0.2), c_top + Inches(0.12), w_card_w - Inches(0.4), c_h - Inches(0.24))
    tf_s3_2 = tb_s3_2.text_frame; tf_s3_2.word_wrap = True

    p_s3_2 = tf_s3_2.paragraphs[0]
    p_s3_2.text = "• Methodology and process for implementation (Flow Charts/Images/ working prototype)"
    p_s3_2.font.size = Pt(14); p_s3_2.font.bold = True; p_s3_2.font.color.rgb = NAVY

    # Flow Chart Step Boxes in Card 2
    flow_steps = [
        ("Step 1: Raster Ingestion & Georeferencing", "Auto-reads GeoTIFFs, reprojects CRS, extracts bounds & metadata (GDAL/Rasterio)"),
        ("Step 2: Natural Language Intent Parsing", "QueryClassifier parses question intent & validates input modality constraints"),
        ("Step 3: Agentic Orchestration & Routing", "Deterministic ModelRegistry routes strictly to verified specialist (Zero Hallucination)"),
        ("Step 4: Specialist AI & Spectral Engines", "Runs BLIP VQA, Text Grounder, Change Detection, Optical+SAR Fusion, or Hydro-NDWI"),
        ("Step 5: Interactive GIS Visualization & Audit", "Renders MapLibre GL vector overlays, confidence score & exportable audit log")
    ]

    f_box_left = Inches(0.5) + w_card_w + w_gap + Inches(0.2)
    f_box_width = w_card_w - Inches(0.4)
    f_box_height = Inches(0.56)
    f_start_top = c_top + Inches(0.58)
    f_step_gap = Inches(0.76)

    for i, (step_title, step_desc) in enumerate(flow_steps):
        cur_top = f_start_top + i * f_step_gap

        # Flow Step Container Box
        f_box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, f_box_left, cur_top, f_box_width, f_box_height)
        f_box.fill.solid()
        f_box.fill.fore_color.rgb = WHITE if i % 2 == 0 else RGBColor(241, 245, 250)
        f_box.line.color.rgb = SIH_BLUE if i % 2 == 1 else RGBColor(180, 195, 215)
        f_box.line.width = Pt(1.2)

        # Step Text
        f_tf = f_box.text_frame
        f_tf.word_wrap = True
        f_tf.margin_left = Inches(0.12)
        f_tf.margin_right = Inches(0.12)
        f_tf.margin_top = Inches(0.04)
        f_tf.margin_bottom = Inches(0.04)

        p_st = f_tf.paragraphs[0]
        p_st.text = step_title
        p_st.font.size = Pt(10.5)
        p_st.font.bold = True
        p_st.font.color.rgb = NAVY

        p_sd = f_tf.add_paragraph()
        p_sd.text = step_desc
        p_sd.font.size = Pt(9.2)
        p_sd.font.color.rgb = DARK_GRAY

        # Down Arrow between boxes
        if i < len(flow_steps) - 1:
            arr_top = cur_top + f_box_height
            arr_box = s3.shapes.add_textbox(f_box_left + Inches(2.6), arr_top - Inches(0.04), Inches(0.5), Inches(0.25))
            ap = arr_box.text_frame.paragraphs[0]
            ap.text = "▼"
            ap.font.size = Pt(10)
            ap.font.bold = True
            ap.font.color.rgb = SIH_BLUE
            ap.alignment = PP_ALIGN.CENTER

    # =========================================================================
    # SLIDE 4: EXACT SIH TEMPLATE - FEASIBILITY & CHALLENGES
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_template_header_and_footer(s4, "FEASIBILITY & CHALLENGES", 4)

    hdr_box4 = s4.shapes.add_textbox(Inches(0.5), Inches(1.45), Inches(12.333), Inches(0.6))
    h4_run = hdr_box4.text_frame.paragraphs[0].add_run()
    h4_run.text = "❖ Feasibility, Challenges & Mitigation Strategies"
    h4_run.font.size = Pt(23); h4_run.font.bold = True; h4_run.font.underline = True; h4_run.font.color.rgb = SIH_BLUE

    s4_sections = [
        ("• Analysis of the feasibility of the idea", [
            ("Technical: ", "Proven working prototype tested on Sentinel-1/2, BigEarthNet, and ISRO rasters."),
            ("Operational: ", "100% self-contained; zero paid API dependencies; works offline/air-gapped."),
            ("Economic: ", "Open-source stack (GDAL, PyTorch); eliminates expensive per-seat GIS software fees."),
            ("Hardware: ", "Runs smoothly on standard CPUs (<300ms) with optional CUDA acceleration.")
        ]),
        ("• Potential challenges and risks", [
            ("Data Heterogeneity: ", "Varying CRS projections, resolutions (5.8m–20m), and band orders."),
            ("Weather & Clouds: ", "Monsoon cloud cover and haze obscure critical optical satellite imagery."),
            ("SAR Speckle Noise: ", "Radar backscatter noise artifacts causing false detection alarms."),
            ("AI Hallucination: ", "Generic LLMs inventing ungrounded coordinates and false features.")
        ]),
        ("• Strategies for overcoming these challenges", [
            ("Auto-Normalization: ", "Ingestor auto-detects CRS, aligns projections, and standardizes bands."),
            ("Optical + SAR Fusion: ", "Radar microwaves pierce clouds and rain for 24/7 all-weather monitoring."),
            ("Speckle Filtering: ", "VV/VH dual-polarization filtering and adaptive Otsu thresholding."),
            ("Deterministic Routing: ", "Grounded pixel masks, audit logs, and calibrated confidence (84–98%).")
        ])
    ]

    for idx, (ptr_title, bullets) in enumerate(s4_sections):
        x_pos = Inches(0.5) + idx * (col_w + gap)
        card = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x_pos, c_top, col_w, c_h)
        card.fill.solid(); card.fill.fore_color.rgb = LIGHT_BG; card.line.color.rgb = CARD_BORDER; card.line.width = Pt(1.5)

        t_card = s4.shapes.add_textbox(x_pos + Inches(0.18), c_top + Inches(0.12), col_w - Inches(0.36), c_h - Inches(0.24))
        t_cf = t_card.text_frame; t_cf.word_wrap = True

        p_th = t_cf.paragraphs[0]; p_th.text = ptr_title; p_th.font.size = Pt(13); p_th.font.bold = True; p_th.font.color.rgb = NAVY

        for b_lead, b_body in bullets:
            p_b = t_cf.add_paragraph(); p_b.space_before = Pt(7)
            r_lead = p_b.add_run(); r_lead.text = f"• {b_lead}"; r_lead.font.bold = True; r_lead.font.size = Pt(10.2); r_lead.font.color.rgb = DARK_GRAY
            r_body = p_b.add_run(); r_body.text = b_body; r_body.font.size = Pt(10.2); r_body.font.color.rgb = DARK_GRAY

    # =========================================================================
    # SLIDE 5: EXACT SIH TEMPLATE - IMPACT & BENEFITS
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_template_header_and_footer(s5, "IMPACT & BENEFITS", 5)

    hdr_box5 = s5.shapes.add_textbox(Inches(0.5), Inches(1.45), Inches(12.333), Inches(0.6))
    h5_run = hdr_box5.text_frame.paragraphs[0].add_run()
    h5_run.text = "❖ Impact & Benefits (Target Audience, Social & Economic Value)"
    h5_run.font.size = Pt(23); h5_run.font.bold = True; h5_run.font.underline = True; h5_run.font.color.rgb = SIH_BLUE

    # Card 1: Potential Impact on Target Audience
    c1_s5 = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), c_top, w_card_w, c_h)
    c1_s5.fill.solid(); c1_s5.fill.fore_color.rgb = LIGHT_BG; c1_s5.line.color.rgb = CARD_BORDER; c1_s5.line.width = Pt(1.5)

    tb_s5_1 = s5.shapes.add_textbox(Inches(0.7), c_top + Inches(0.12), w_card_w - Inches(0.4), c_h - Inches(0.24))
    tf_s5_1 = tb_s5_1.text_frame; tf_s5_1.word_wrap = True

    p_s5_1 = tf_s5_1.paragraphs[0]
    p_s5_1.text = "• Potential Impact on Target Audience"
    p_s5_1.font.size = Pt(15); p_s5_1.font.bold = True; p_s5_1.font.color.rgb = NAVY

    audience_impacts = [
        ("Disaster Response Teams (NDRF, SDMA): ", "Provides instant flood boundary maps and inundated area calculations (Hydro-NDWI in <70ms) to prioritize life-saving rescue operations."),
        ("Water Resource Authorities (Ministry of Jal Shakti): ", "Enables automated monitoring of reservoir levels, seasonal surface water shrinkage, and wetland conservation without dedicated GIS teams."),
        ("Urban Planning & Municipal Corporations: ", "Automatically detects illegal urban encroachments, built-up sprawl, and changes in green cover using NDBI and bi-temporal comparison."),
        ("Agricultural & Drought Monitoring: ", "Tracks crop canopy variations, irrigation patterns, and drought stress via spectral index calculations and land-cover VQA."),
        ("Defense & Coastal Maritime Security: ", "Detects marine vessels, coastal changes, and infrastructure expansions through day-and-night SAR object grounding.")
    ]

    for lead, desc in audience_impacts:
        p = tf_s5_1.add_paragraph(); p.space_before = Pt(7)
        r1 = p.add_run(); r1.text = f"• {lead}"; r1.font.bold = True; r1.font.size = Pt(10.2); r1.font.color.rgb = DARK_GRAY
        r2 = p.add_run(); r2.text = desc; r2.font.size = Pt(10.2); r2.font.color.rgb = DARK_GRAY

    # Card 2: Benefits of the Solution
    c2_s5 = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5) + w_card_w + w_gap, c_top, w_card_w, c_h)
    c2_s5.fill.solid(); c2_s5.fill.fore_color.rgb = LIGHT_BG; c2_s5.line.color.rgb = CARD_BORDER; c2_s5.line.width = Pt(1.5)

    tb_s5_2 = s5.shapes.add_textbox(Inches(0.5) + w_card_w + w_gap + Inches(0.2), c_top + Inches(0.12), w_card_w - Inches(0.4), c_h - Inches(0.24))
    tf_s5_2 = tb_s5_2.text_frame; tf_s5_2.word_wrap = True

    p_s5_2 = tf_s5_2.paragraphs[0]
    p_s5_2.text = "• Benefits of the Solution (Social, Commercial, Env.)"
    p_s5_2.font.size = Pt(15); p_s5_2.font.bold = True; p_s5_2.font.color.rgb = NAVY

    benefits_bullets = [
        ("Social & Humanitarian Impact: ", "Democratizes complex space technology. First responders can type plain-language queries and receive life-saving disaster maps in seconds."),
        ("Economic & Cost Efficiency: ", "Reduces GIS workflow times by 95%; replaces expensive per-seat commercial GIS software licensing with an open-source, scalable platform."),
        ("Environmental Sustainability: ", "Provides continuous, objective ecological monitoring for deforestation, wetland depletion, and urban heat island mitigation."),
        ("National Self-Reliance (Atmanirbhar Bharat): ", "Natively leverages Indian space assets (ISRO Resourcesat, Cartosat, RISAT) via Bhoonidhi standards alongside global Sentinel constellations."),
        ("Scalability & Commercial Potential: ", "Easily extensible to state-wide disaster management portals, smart cities, and private environmental audit firms.")
    ]

    for lead, desc in benefits_bullets:
        p = tf_s5_2.add_paragraph(); p.space_before = Pt(7)
        r1 = p.add_run(); r1.text = f"• {lead}"; r1.font.bold = True; r1.font.size = Pt(10.2); r1.font.color.rgb = DARK_GRAY
        r2 = p.add_run(); r2.text = desc; r2.font.size = Pt(10.2); r2.font.color.rgb = DARK_GRAY

    # =========================================================================
    # SLIDE 6: EXACT SIH TEMPLATE - RESEARCH & REFERENCES
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_template_header_and_footer(s6, "RESEARCH & REFERENCES", 6)

    hdr_box6 = s6.shapes.add_textbox(Inches(0.5), Inches(1.45), Inches(12.333), Inches(0.6))
    h6_run = hdr_box6.text_frame.paragraphs[0].add_run()
    h6_run.text = "❖ Research, Benchmarks & Geospatial Standards"
    h6_run.font.size = Pt(23); h6_run.font.bold = True; h6_run.font.underline = True; h6_run.font.color.rgb = SIH_BLUE

    # Card 1: Prescribed Datasets & Benchmarks
    c1_s6 = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5), c_top, w_card_w, c_h)
    c1_s6.fill.solid(); c1_s6.fill.fore_color.rgb = LIGHT_BG; c1_s6.line.color.rgb = CARD_BORDER; c1_s6.line.width = Pt(1.5)

    tb_s6_1 = s6.shapes.add_textbox(Inches(0.7), c_top + Inches(0.12), w_card_w - Inches(0.4), c_h - Inches(0.24))
    tf_s6_1 = tb_s6_1.text_frame; tf_s6_1.word_wrap = True

    p_s6_1 = tf_s6_1.paragraphs[0]
    p_s6_1.text = "• Prescribed Datasets & Benchmarks Used"
    p_s6_1.font.size = Pt(15); p_s6_1.font.bold = True; p_s6_1.font.color.rgb = NAVY

    research_datasets = [
        ("1. BigEarthNet (Sentinel-1 & Sentinel-2): ", "590,326 multi-spectral patches annotated with CORINE Land Cover (CLC) classes. Used for fine-tuning our BLIP VQA checkpoint (100% token F1 on test split). Reference: Sumbul et al., IEEE IGARSS 2019 / arXiv:1902.06148."),
        ("2. RSVQA (Remote Sensing Visual Question Answering): ", "High-resolution aerial (RSVQA-HR) and low-resolution Sentinel-2 (RSVQA-LR) benchmarks establishing baseline QA accuracy. Reference: Lobry et al., IEEE TGRS 2020."),
        ("3. VRSBench (Visual Reasoning in Remote Sensing): ", "Standardized benchmark for dense captioning, natural-language object grounding, and spatial reasoning. Reference: Li et al., IEEE TGRS 2024."),
        ("4. CDVQA (Change Detection Visual QA): ", "Bi-temporal remote-sensing dataset for evaluating multi-temporal change detection through questions. Reference: Yuan et al., IEEE GRSL 2022.")
    ]

    for lead, desc in research_datasets:
        p = tf_s6_1.add_paragraph(); p.space_before = Pt(7)
        r1 = p.add_run(); r1.text = f"• {lead}"; r1.font.bold = True; r1.font.size = Pt(10.2); r1.font.color.rgb = DARK_GRAY
        r2 = p.add_run(); r2.text = desc; r2.font.size = Pt(10.2); r2.font.color.rgb = DARK_GRAY

    # Card 2: Sensor Specifications & Standards
    c2_s6 = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5) + w_card_w + w_gap, c_top, w_card_w, c_h)
    c2_s6.fill.solid(); c2_s6.fill.fore_color.rgb = LIGHT_BG; c2_s6.line.color.rgb = CARD_BORDER; c2_s6.line.width = Pt(1.5)

    tb_s6_2 = s6.shapes.add_textbox(Inches(0.5) + w_card_w + w_gap + Inches(0.2), c_top + Inches(0.12), w_card_w - Inches(0.4), c_h - Inches(0.24))
    tf_s6_2 = tb_s6_2.text_frame; tf_s6_2.word_wrap = True

    p_s6_2 = tf_s6_2.paragraphs[0]
    p_s6_2.text = "• Sensor Specifications & Geospatial Standards"
    p_s6_2.font.size = Pt(15); p_s6_2.font.bold = True; p_s6_2.font.color.rgb = NAVY

    sensor_standards = [
        ("5. ISRO / SAC Mission Standards: ", "Resourcesat-2/2A LISS-4 (5.8m multispectral), Cartosat-1/2S/3 high-resolution terrain mapping, and RISAT-1A (EOS-04 C-band SAR). Ingested via NRSC Bhoonidhi OpenSearch/STAC APIs."),
        ("6. ESA Copernicus Constellations: ", "Sentinel-1 (C-band SAR radar, dual-pol VV/VH) and Sentinel-2 (13-band MSI, 10m/20m multispectral). Ingested via Copernicus Data Space Ecosystem (CDSE) OData v4 APIs."),
        ("7. Remote Sensing Spectral Indices: ", "Normalized Difference Water Index (NDWI) by McFeeters (1996) and Normalized Difference Built-Up Index (NDBI) by Zha et al. (2003)."),
        ("8. Geospatial Data Standards: ", "Complies with Open Geospatial Consortium (OGC) specifications, SpatioTemporal Asset Catalog (STAC), GeoTIFF metadata, and EPSG Coordinate Reference Systems.")
    ]

    for lead, desc in sensor_standards:
        p = tf_s6_2.add_paragraph(); p.space_before = Pt(7)
        r1 = p.add_run(); r1.text = f"• {lead}"; r1.font.bold = True; r1.font.size = Pt(10.2); r1.font.color.rgb = DARK_GRAY
        r2 = p.add_run(); r2.text = desc; r2.font.size = Pt(10.2); r2.font.color.rgb = DARK_GRAY

    # Save
    prs.save(output_path)
    # Also overwrite the primary presentation file so user gets the exact 6 slides
    prs.save(r"d:\PROJECTS-PUPU\satquery-ai\SatQuery_AI_SIH26167_Presentation.pptx")
    print(f"[SUCCESS] Built perfect SIH official 6-slide deck at:\n{output_path}")

if __name__ == "__main__":
    build_perfect_sih_deck()
