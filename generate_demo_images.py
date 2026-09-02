import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import os

assets_dir = r"d:\PROJECTS-PUPU\satquery-ai\app\static\assets"
os.makedirs(assets_dir, exist_ok=True)

def generate_optical_2024():
    w, h = 800, 600
    img = Image.new("RGB", (w, h), (45, 85, 40)) # Base vegetation green
    draw = ImageDraw.Draw(img)

    # Add topography texture
    np.random.seed(42)
    noise = np.random.randint(-15, 15, (h, w, 3), dtype=np.int16)
    arr = np.array(img, dtype=np.int16) + noise
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)

    # Agricultural field patches
    fields = [
        [(50, 50), (220, 50), (240, 180), (70, 190)],
        [(250, 40), (420, 30), (400, 150), (230, 160)],
        [(60, 210), (220, 200), (200, 350), (40, 340)],
        [(450, 60), (600, 50), (580, 170), (430, 180)],
        [(620, 70), (750, 80), (740, 220), (610, 200)],
    ]
    colors = [(120, 140, 60), (160, 170, 80), (140, 110, 50), (90, 120, 50), (180, 160, 90)]
    for pts, col in zip(fields, colors):
        draw.polygon(pts, fill=col, outline=(30, 60, 30))

    # Meandering River (Water body)
    river_points = [(0, 450), (150, 420), (300, 460), (450, 400), (600, 430), (700, 380), (800, 400)]
    # Draw thick curve
    for i in range(len(river_points)-1):
        x1, y1 = river_points[i]
        x2, y2 = river_points[i+1]
        draw.line([x1, y1, x2, y2], fill=(20, 75, 130), width=45)

    # Small lake connected to river
    draw.ellipse([320, 480, 480, 570], fill=(15, 65, 120), outline=(25, 85, 140))

    # Built-up Urban Area (small in 2024)
    # Blocks around (480, 220) to (600, 340)
    urban_area = [(480, 220), (580, 220), (580, 320), (480, 320)]
    draw.polygon(urban_area, fill=(160, 155, 150), outline=(100, 100, 100))
    # Buildings / roads
    for bx in range(490, 570, 20):
        for by in range(230, 310, 20):
            draw.rectangle([bx, by, bx+12, by+12], fill=(210, 205, 195), outline=(70, 70, 70))

    # Roads
    draw.line([(0, 280), (800, 300)], fill=(120, 120, 120), width=6)
    draw.line([(530, 0), (530, 600)], fill=(110, 110, 110), width=6)

    img.save(os.path.join(assets_dir, "optical_2024.png"))
    print("Generated optical_2024.png")

def generate_optical_2026():
    # Same base as 2024, but with significant urban expansion & deforestation
    w, h = 800, 600
    img = Image.new("RGB", (w, h), (45, 85, 40))
    draw = ImageDraw.Draw(img)

    np.random.seed(42)
    noise = np.random.randint(-15, 15, (h, w, 3), dtype=np.int16)
    arr = np.array(img, dtype=np.int16) + noise
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)

    fields = [
        [(50, 50), (220, 50), (240, 180), (70, 190)],
        [(250, 40), (420, 30), (400, 150), (230, 160)],
        # Field 3 converted to industrial park in 2026!
        [(60, 210), (220, 200), (200, 350), (40, 340)],
        [(450, 60), (600, 50), (580, 170), (430, 180)],
        [(620, 70), (750, 80), (740, 220), (610, 200)],
    ]
    colors = [(120, 140, 60), (160, 170, 80), (145, 140, 135), (90, 120, 50), (180, 160, 90)]
    for pts, col in zip(fields, colors):
        draw.polygon(pts, fill=col, outline=(30, 60, 30))

    # Meandering River
    river_points = [(0, 450), (150, 420), (300, 460), (450, 400), (600, 430), (700, 380), (800, 400)]
    for i in range(len(river_points)-1):
        x1, y1 = river_points[i]
        x2, y2 = river_points[i+1]
        draw.line([x1, y1, x2, y2], fill=(20, 75, 130), width=45)

    # Expanded lake / reservoir in 2026
    draw.ellipse([300, 460, 510, 590], fill=(15, 65, 120), outline=(25, 85, 140))

    # EXPANDED Urban Area in 2026 (Much larger!)
    urban_area = [(420, 180), (720, 180), (720, 370), (420, 370)]
    draw.polygon(urban_area, fill=(175, 170, 165), outline=(100, 100, 100))
    for bx in range(430, 710, 18):
        for by in range(190, 360, 18):
            draw.rectangle([bx, by, bx+11, by+11], fill=(225, 220, 210), outline=(60, 60, 60))

    # Additional industrial complex in field 3 (west side)
    for bx in range(70, 200, 25):
        for by in range(220, 330, 25):
            draw.rectangle([bx, by, bx+16, by+16], fill=(190, 185, 180), outline=(80, 80, 80))

    # Highways
    draw.line([(0, 280), (800, 300)], fill=(120, 120, 120), width=8)
    draw.line([(530, 0), (530, 600)], fill=(110, 110, 110), width=8)
    draw.line([(200, 300), (420, 180)], fill=(130, 130, 130), width=6)

    img.save(os.path.join(assets_dir, "optical_2026.png"))
    print("Generated optical_2026.png")

def generate_optical_sar_pair():
    w, h = 800, 600
    # Optical RGB Sentinel-2 mock
    opt = Image.new("RGB", (w, h), (55, 95, 45))
    draw_opt = ImageDraw.Draw(opt)
    
    # Forest / Agr fields
    draw_opt.polygon([(100, 50), (400, 50), (350, 300), (80, 250)], fill=(35, 110, 45))
    draw_opt.polygon([(420, 50), (750, 80), (720, 280), (410, 260)], fill=(150, 160, 70))
    
    # Big Water Bay
    draw_opt.polygon([(0, 350), (800, 380), (800, 600), (0, 600)], fill=(22, 85, 145))
    
    # Built-up Port & City
    draw_opt.polygon([(250, 280), (550, 280), (580, 400), (220, 400)], fill=(180, 175, 165))
    for x in range(260, 540, 20):
        for y in range(290, 390, 20):
            draw_opt.rectangle([x, y, x+12, y+12], fill=(230, 225, 215), outline=(50, 50, 50))
            
    opt.save(os.path.join(assets_dir, "optical_multimodal.png"))
    print("Generated optical_multimodal.png")

    # SAR Sentinel-1 Mock (Radar intensity backscatter)
    # Water = pitch dark specular reflection (low backscatter ~ 10-30)
    # Double bounce buildings = bright white spots (~ 220-255)
    # Vegetation = medium grey volume scattering (~ 80-130)
    sar_arr = np.random.normal(100, 25, (h, w)).clip(0, 255).astype(np.uint8)
    
    # Water region dark
    water_mask = np.zeros((h, w), dtype=bool)
    # polygon [(0, 350), (800, 380), (800, 600), (0, 600)]
    for y in range(h):
        for x in range(w):
            water_y = 350 + (x / 800.0) * 30
            if y >= water_y:
                water_mask[y, x] = True
    
    sar_arr[water_mask] = np.random.normal(20, 8, np.sum(water_mask)).clip(0, 255).astype(np.uint8)
    
    # Built up region high backscatter
    built_mask = np.zeros((h, w), dtype=bool)
    for y in range(280, 400):
        for x in range(220, 580):
            if y < 350 + (x / 800.0) * 30:
                built_mask[y, x] = True
                
    sar_arr[built_mask] = np.random.normal(210, 35, np.sum(built_mask)).clip(0, 255).astype(np.uint8)

    sar = Image.fromarray(sar_arr).convert("RGB")
    sar.save(os.path.join(assets_dir, "sar_multimodal.png"))
    print("Generated sar_multimodal.png")

if __name__ == "__main__":
    generate_optical_2024()
    generate_optical_2026()
    generate_optical_sar_pair()
