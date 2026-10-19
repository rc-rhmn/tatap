#!/usr/bin/env python3
"""
tools/generate_android_icons.py - Generate Android Adaptive Icons, Legacy Mipmaps,
Android TV Leanback Banners, and Desktop Assets with Supersampled Antialiasing.
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_IMAGE_PATH = "/home/b-ict/.gemini/antigravity-cli/brain/f7f616a4-3347-4f19-b691-28b965e20724/tatap_app_icon_v2_1792026526885.jpg"

if not os.path.exists(SRC_IMAGE_PATH):
    print(f"Error: Source image not found at {SRC_IMAGE_PATH}")
    sys.exit(1)

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def generate_master_canvas(src_img, canvas_size=1024, char_scale=0.76):
    """
    Creates a full-bleed square canvas with the character mascot scaled and centered
    comfortably within the Android adaptive icon safe zone (66%-72%).
    """
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (10, 13, 20, 255)) # #0A0D14
    target_char_size = int(canvas_size * char_scale)
    scaled_char = src_img.resize((target_char_size, target_char_size), Image.Resampling.LANCZOS)
    
    offset_x = (canvas_size - target_char_size) // 2
    offset_y = (canvas_size - target_char_size) // 2 + int(canvas_size * 0.01)
    
    canvas.paste(scaled_char, (offset_x, offset_y))
    return canvas

def generate_circle_icon(master_img, size):
    """
    Generates a legacy round icon with an exact circular mask and smooth anti-aliased edges.
    """
    # 4x supersampling
    super_size = size * 4
    supersampled = master_img.resize((super_size, super_size), Image.Resampling.LANCZOS)
    
    mask = Image.new("L", (super_size, super_size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, super_size - 1, super_size - 1), fill=255)
    
    result = Image.new("RGBA", (super_size, super_size), (0, 0, 0, 0))
    result.paste(supersampled, (0, 0), mask)
    
    return result.resize((size, size), Image.Resampling.LANCZOS)

def generate_square_icon(master_img, size):
    """
    Generates a square / full-bleed icon downsampled with Lanczos.
    """
    return master_img.resize((size, size), Image.Resampling.LANCZOS)

def generate_tv_banner(src_img, width=640, height=360):
    """
    Generates an Android TV Leanback Banner (16:9) conforming to overscan safety rules.
    """
    banner = Image.new("RGBA", (width, height), (10, 13, 20, 255)) # #0A0D14
    
    # Left ambient soft cyan glow
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw_g = ImageDraw.Draw(glow)
    draw_g.ellipse((-int(width * 0.08), -int(height * 0.15), int(width * 0.6), int(height * 1.15)), fill=(14, 165, 233, 48))
    glow = glow.filter(ImageFilter.GaussianBlur(int(height * 0.12)))
    banner = Image.alpha_composite(banner, glow)
    
    # Character mascot on the left
    char_h = int(height * 0.92)
    char_scaled = src_img.resize((char_h, char_h), Image.Resampling.LANCZOS)
    char_x = int(width * 0.035)
    char_y = int(height * 0.04)
    banner.paste(char_scaled, (char_x, char_y), char_scaled)
    
    # Right-side typography
    draw = ImageDraw.Draw(banner)
    font_scale = height / 360.0
    
    font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    if not os.path.exists(font_path):
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        
    font_title = ImageFont.truetype(font_path, int(58 * font_scale))
    font_sub = ImageFont.truetype(font_path, int(18 * font_scale))
    font_badge = ImageFont.truetype(font_path, int(16 * font_scale))
    
    text_x = int(width * 0.56)
    title_y = int(height * 0.32)
    sub_y = int(height * 0.52)
    badge_y = int(height * 0.62)
    
    # Title: TATAP
    draw.text((text_x, title_y), "TATAP", font=font_title, fill=(255, 255, 255, 255))
    
    # Subtitle: ANIME STREAMING
    draw.text((text_x + int(4 * font_scale), sub_y), "ANIME STREAMING", font=font_sub, fill=(148, 163, 184, 255))
    
    # TV Badge pill
    badge_w = int(64 * font_scale)
    badge_h = int(30 * font_scale)
    badge_rect = (text_x + int(4 * font_scale), badge_y, text_x + int(4 * font_scale) + badge_w, badge_y + badge_h)
    draw.rounded_rectangle(badge_rect, radius=int(6 * font_scale), outline=(56, 189, 248, 255), width=max(1, int(2 * font_scale)), fill=(15, 23, 42, 220))
    
    # Center text inside badge
    badge_text_x = badge_rect[0] + int(19 * font_scale)
    badge_text_y = badge_rect[1] + int(6 * font_scale)
    draw.text((badge_text_x, badge_text_y), "TV", font=font_badge, fill=(56, 189, 248, 255))
    
    return banner

def main():
    print(f"Loading source mascot artwork from {SRC_IMAGE_PATH}...")
    src_img = Image.open(SRC_IMAGE_PATH).convert("RGBA")
    
    print("Generating 1024x1024 master canvas...")
    master_1024 = generate_master_canvas(src_img, canvas_size=1024, char_scale=0.76)
    
    # 1. Update project root assets
    assets_dir = os.path.join(ROOT_DIR, "assets")
    ensure_dir(assets_dir)
    master_1024.convert("RGB").save(os.path.join(assets_dir, "tatap_icon_master.png"), quality=95)
    generate_square_icon(master_1024, 512).convert("RGB").save(os.path.join(assets_dir, "tatap_icon_512.png"), quality=95)
    print("Updated assets/tatap_icon_master.png and assets/tatap_icon_512.png")
    
    # 2. Update frontend web assets
    frontend_assets_dir = os.path.join(ROOT_DIR, "frontend", "assets")
    ensure_dir(frontend_assets_dir)
    generate_square_icon(master_1024, 512).convert("RGB").save(os.path.join(frontend_assets_dir, "icon.png"), quality=95)
    generate_square_icon(master_1024, 512).convert("RGB").save(os.path.join(frontend_assets_dir, "icon-512.png"), quality=95)
    generate_square_icon(master_1024, 192).convert("RGB").save(os.path.join(frontend_assets_dir, "icon-192.png"), quality=95)
    
    # Favicon and launcher .ico
    ico_img = generate_circle_icon(master_1024, 256)
    ico_path = os.path.join(ROOT_DIR, "frontend", "favicon.ico")
    ico_img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    
    launcher_ico = os.path.join(ROOT_DIR, "launcher", "icon.ico")
    launcher_winres_ico = os.path.join(ROOT_DIR, "launcher", "winres", "icon.ico")
    ico_img.save(launcher_ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    ico_img.save(launcher_winres_ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("Updated frontend assets, favicon.ico, and launcher icon.ico")
    
    # 3. Android Adaptive Icons & Foreground Layer
    # Foreground canvas for 108dp is typically 432x432 px (xxxhdpi = 4x)
    # The character itself sits in the center safe zone (72dp = 288px)
    res_main_dir = os.path.join(ROOT_DIR, "android", "app", "src", "main", "res")
    drawable_dir = os.path.join(res_main_dir, "drawable")
    ensure_dir(drawable_dir)
    
    fg_canvas = Image.new("RGBA", (432, 432), (0, 0, 0, 0))
    fg_char_size = int(432 * 0.74)
    fg_scaled = src_img.resize((fg_char_size, fg_char_size), Image.Resampling.LANCZOS)
    fg_x = (432 - fg_char_size) // 2
    fg_y = (432 - fg_char_size) // 2 + 5
    fg_canvas.paste(fg_scaled, (fg_x, fg_y), fg_scaled)
    fg_canvas.save(os.path.join(drawable_dir, "ic_launcher_foreground.png"))
    
    # Adaptive Icon XMLs in mipmap-anydpi-v26
    v26_dir = os.path.join(res_main_dir, "mipmap-anydpi-v26")
    ensure_dir(v26_dir)
    
    adaptive_xml = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
    <monochrome android:drawable="@drawable/ic_launcher_monochrome" />
</adaptive-icon>
"""
    with open(os.path.join(v26_dir, "ic_launcher.xml"), "w") as f:
        f.write(adaptive_xml)
    with open(os.path.join(v26_dir, "ic_launcher_round.xml"), "w") as f:
        f.write(adaptive_xml)
    print("Generated mipmap-anydpi-v26/ic_launcher.xml & ic_launcher_round.xml")
    
    # Background XML
    bg_xml = """<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <solid android:color="#0A0D14" />
</shape>
"""
    with open(os.path.join(drawable_dir, "ic_launcher_background.xml"), "w") as f:
        f.write(bg_xml)
        
    # Monochrome Vector XML (for Material You Themed Icons API 33+)
    # Clean vector silhouette of headphone + anime girl head profile
    mono_xml = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <!-- Center 72dp safe zone (X:18..90, Y:18..90) -->
    <!-- Headphone Arch -->
    <path
        android:fillColor="#00000000"
        android:strokeColor="#FFFFFF"
        android:strokeWidth="4"
        android:strokeLineCap="round"
        android:pathData="M32,54 C32,32 76,32 76,54" />
    <!-- Ear Cups -->
    <path
        android:fillColor="#FFFFFF"
        android:pathData="M27,48 L35,48 A3,3 0 0,1 38,51 L38,65 A3,3 0 0,1 35,68 L27,68 A3,3 0 0,1 24,65 L24,51 A3,3 0 0,1 27,48 Z" />
    <path
        android:fillColor="#FFFFFF"
        android:pathData="M73,48 L81,48 A3,3 0 0,1 84,51 L84,65 A3,3 0 0,1 81,68 L73,68 A3,3 0 0,1 70,65 L70,51 A3,3 0 0,1 73,48 Z" />
    <!-- Anime Hair / Face silhouette -->
    <path
        android:fillColor="#FFFFFF"
        android:pathData="M40,46 C44,38 64,38 68,46 C64,52 66,58 64,68 C58,74 50,74 44,68 C42,58 44,52 40,46 Z" />
    <!-- Anime Eyes -->
    <path
        android:fillColor="#000000"
        android:pathData="M47,56 L51,55 L50,58 Z" />
    <path
        android:fillColor="#000000"
        android:pathData="M57,55 L61,56 L58,58 Z" />
</vector>
"""
    with open(os.path.join(drawable_dir, "ic_launcher_monochrome.xml"), "w") as f:
        f.write(mono_xml)
    print("Generated ic_launcher_background.xml & ic_launcher_monochrome.xml")
    
    # 4. Android Legacy Mipmap Densities
    densities = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    
    for folder, size in densities.items():
        target_dir = os.path.join(res_main_dir, folder)
        ensure_dir(target_dir)
        
        sq = generate_square_icon(master_1024, size)
        sq.convert("RGB").save(os.path.join(target_dir, "ic_launcher.png"), quality=95)
        
        rnd = generate_circle_icon(master_1024, size)
        rnd.save(os.path.join(target_dir, "ic_launcher_round.png"), format="PNG")
        print(f"Generated {folder}/ic_launcher.png ({size}x{size}) & round")
        
    # Large drawables
    generate_square_icon(master_1024, 512).convert("RGB").save(os.path.join(drawable_dir, "ic_launcher.png"), quality=95)
    generate_circle_icon(master_1024, 512).save(os.path.join(drawable_dir, "ic_launcher_round.png"), format="PNG")
    print("Generated drawable/ic_launcher.png (512x512) & round")
    
    # 5. Android TV Leanback Banners
    tv_res_dir = os.path.join(ROOT_DIR, "android", "app", "src", "tv", "res")
    tv_drawable_dir = os.path.join(tv_res_dir, "drawable")
    tv_drawable_xhdpi_dir = os.path.join(tv_res_dir, "drawable-xhdpi")
    ensure_dir(tv_drawable_dir)
    ensure_dir(tv_drawable_xhdpi_dir)
    
    banner_320 = generate_tv_banner(src_img, 320, 180)
    banner_320.save(os.path.join(tv_drawable_dir, "tv_banner.png"), format="PNG")
    
    banner_640 = generate_tv_banner(src_img, 640, 360)
    banner_640.save(os.path.join(tv_drawable_xhdpi_dir, "tv_banner.png"), format="PNG")
    print("Generated TV banners: 320x180 and 640x360")
    
    print("\nAll Android icons and banners generated successfully!")

if __name__ == "__main__":
    main()
