import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def update_presentation():
    pptx_path = r"d:\PROJECTS-PUPU\satquery-ai\SatQuery_AI_SIH26167_Presentation.pptx"
    prs = Presentation(pptx_path) if os.path.exists(pptx_path) else Presentation()
    if not os.path.exists(pptx_path):
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]

    # Color definitions
    NAVY = RGBColor(11, 44, 91)
    ACCENT_BLUE = RGBColor(24, 119, 242)
    DARK_GRAY = RGBColor(33, 37, 41)
    LIGHT_BG = RGBColor(248, 249, 250)
    CARD_BORDER = RGBColor(220, 224, 230)
    WHITE = RGBColor(255, 255, 255)

    # -------------------------------------------------------------
    # SLIDE 3: EXACT SIH TEMPLATE - TECHNICAL APPROACH
    # -------------------------------------------------------------
    s3 = prs.slides.add_slide(blank_layout)

    # Top Left Oval (Team Name)
    oval = s3.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.6), Inches(0.4), Inches(2.2), Inches(1.1))
    oval.fill.solid(); oval.fill.fore_color.rgb = WHITE
    oval.line.color.rgb = RGBColor(128, 0, 128); oval.line.width = Pt(2.0)
    otf = oval.text_frame; otf.text = "Your Team\nName"
    otf.paragraphs[0].font.size = Pt(14); otf.paragraphs[0].font.bold = True
    otf.paragraphs[0].font.color.rgb = DARK_GRAY; otf.paragraphs[0].alignment = PP_ALIGN.CENTER
    otf.paragraphs[1].font.size = Pt(14); otf.paragraphs[1].font.bold = True
    otf.paragraphs[1].font.color.rgb = DARK_GRAY; otf.paragraphs[1].alignment = PP_ALIGN.CENTER

    # Top Center Title: TECHNICAL APPROACH
    itb = s3.shapes.add_textbox(Inches(3.2), Inches(0.5), Inches(6.8), Inches(0.9))
    itf = itb.text_frame; itf.word_wrap = True
    ip = itf.paragraphs[0]
    ip.text = "TECHNICAL APPROACH"
    ip.font.size = Pt(30); ip.font.bold = True; ip.font.color.rgb = DARK_GRAY
    ip.alignment = PP_ALIGN.CENTER

    # Top Right: SIH 2026 Badge
    sih_box = s3.shapes.add_textbox(Inches(10.2), Inches(0.4), Inches(2.5), Inches(1.1))
    stf = sih_box.text_frame
    sp = stf.paragraphs[0]
    sp.text = "SMART INDIA\nHACKATHON 2026"
    sp.font.size = Pt(15); sp.font.bold = True; sp.font.color.rgb = NAVY
    sp.alignment = PP_ALIGN.RIGHT

    # Card 1: Technologies to be used (Left Side: 5.5 inches wide)
    c1 = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(1.8), Inches(5.9), Inches(4.9))
    c1.fill.solid(); c1.fill.fore_color.rgb = LIGHT_BG
    c1.line.color.rgb = CARD_BORDER; c1.line.width = Pt(1.5)

    c1_hdr = s3.shapes.add_textbox(Inches(0.8), Inches(1.9), Inches(5.5), Inches(0.6))
    c1_hp = c1_hdr.text_frame.paragraphs[0]
    c1_hp.text = "• Technologies to be used (e.g. programming languages, frameworks, hardware)"
    c1_hp.font.size = Pt(14.5); c1_hp.font.bold = True; c1_hp.font.color.rgb = NAVY

    c1_body = s3.shapes.add_textbox(Inches(0.8), Inches(2.5), Inches(5.5), Inches(4.1))
    c1_btf = c1_body.text_frame; c1_btf.word_wrap = True

    tech_items = [
        ("Languages: ", "Python 3.11 (Backend AI/GIS), TypeScript (Frontend Web App)."),
        ("Frontend GIS: ", "React 19, Vite, Tailwind CSS v4, MapLibre GL (@nextgis/ngw-map)."),
        ("Backend & API: ", "FastAPI, Uvicorn ASGI, Pydantic v2, RESTful OpenAPI/Swagger."),
        ("AI / Vision-Language: ", "PyTorch, Hugging Face Transformers (Fine-tuned BLIP VQA & Grounder)."),
        ("Geospatial Engine: ", "GDAL, Rasterio, NumPy (GeoTIFF, NetCDF, CRS reprojection, band math)."),
        ("Hardware & Deployment: ", "Optimized CPU inference (<300ms), optional CUDA GPU acceleration.")
    ]

    for idx, (lead, desc) in enumerate(tech_items):
        p = c1_btf.paragraphs[0] if idx == 0 else c1_btf.add_paragraph()
        p.space_after = Pt(10)
        r1 = p.add_run(); r1.text = "• " + lead; r1.font.bold = True; r1.font.size = Pt(11.5); r1.font.color.rgb = DARK_GRAY
        r2 = p.add_run(); r2.text = desc; r2.font.bold = False; r2.font.size = Pt(11); r2.font.color.rgb = DARK_GRAY

    # Card 2: Methodology & Process (Right Side: 5.9 inches wide)
    c2 = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.8), Inches(5.9), Inches(4.9))
    c2.fill.solid(); c2.fill.fore_color.rgb = LIGHT_BG
    c2.line.color.rgb = CARD_BORDER; c2.line.width = Pt(1.5)

    c2_hdr = s3.shapes.add_textbox(Inches(7.0), Inches(1.9), Inches(5.5), Inches(0.6))
    c2_hp = c2_hdr.text_frame.paragraphs[0]
    c2_hp.text = "• Methodology and process for implementation (Flow Charts/Images/ working prototype)"
    c2_hp.font.size = Pt(14.5); c2_hp.font.bold = True; c2_hp.font.color.rgb = ACCENT_BLUE

    # Flow Chart Step Boxes in Card 2
    flow_steps = [
        ("Step 1: Raster Ingestion & Georeferencing", "Auto-reads GeoTIFFs, reprojects CRS, extracts bounds & metadata (GDAL/Rasterio)"),
        ("Step 2: Natural Language Intent Parsing", "QueryClassifier parses question intent & validates input modality constraints"),
        ("Step 3: Agentic Orchestration & Routing", "Deterministic ModelRegistry routes strictly to verified specialist (Zero Hallucination)"),
        ("Step 4: Specialist AI & Spectral Engines", "Runs BLIP VQA, Text Grounder, Change Detection, Optical+SAR Fusion, or Hydro-NDWI"),
        ("Step 5: Interactive GIS Visualization & Audit", "Renders MapLibre GL vector overlays, confidence score & exportable audit log")
    ]

    box_left = Inches(7.0)
    box_width = Inches(5.5)
    box_height = Inches(0.58)
    start_top = Inches(2.55)
    step_gap = Inches(0.78)

    for i, (step_title, step_desc) in enumerate(flow_steps):
        cur_top = start_top + i * step_gap

        # Flow Step Container Box
        f_box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, box_left, cur_top, box_width, box_height)
        f_box.fill.solid()
        f_box.fill.fore_color.rgb = WHITE if i % 2 == 0 else RGBColor(241, 245, 250)
        f_box.line.color.rgb = ACCENT_BLUE if i % 2 == 1 else RGBColor(180, 195, 215)
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
            arr_top = cur_top + box_height
            arr_box = s3.shapes.add_textbox(box_left + Inches(2.5), arr_top - Inches(0.04), Inches(0.5), Inches(0.25))
            ap = arr_box.text_frame.paragraphs[0]
            ap.text = "▼"
            ap.font.size = Pt(10)
            ap.font.bold = True
            ap.font.color.rgb = ACCENT_BLUE
            ap.alignment = PP_ALIGN.CENTER

    # Footer
    fbar = s3.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(6.9), Inches(13.333), Inches(0.6))
    fbar.fill.solid(); fbar.fill.fore_color.rgb = ACCENT_BLUE; fbar.line.fill.background()

    ftxt_l = s3.shapes.add_textbox(Inches(0.6), Inches(6.95), Inches(8.0), Inches(0.5))
    ftxt_l.text_frame.text = "@SIH Idea submission- Template"
    ftxt_l.text_frame.paragraphs[0].font.color.rgb = WHITE
    ftxt_l.text_frame.paragraphs[0].font.size = Pt(12)

    ftxt_r = s3.shapes.add_textbox(Inches(12.0), Inches(6.95), Inches(1.0), Inches(0.5))
    ftxt_r.text_frame.text = "3"
    ftxt_r.text_frame.paragraphs[0].font.color.rgb = WHITE
    ftxt_r.text_frame.paragraphs[0].font.size = Pt(14)
    ftxt_r.text_frame.paragraphs[0].font.bold = True

    prs.save(pptx_path)
    print(f"Slide 3 added and presentation saved to {pptx_path}")

if __name__ == "__main__":
    update_presentation()
