import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont
import io
import math
import os

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro XXL", page_icon="🏍️", layout="centered")

def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color: #ff0000;'>⚙️ Design-Setup</h1>", unsafe_allow_html=True)
    tour_title = st.text_input("Tour Name", value="Meine Tour")
    st.divider()
    # XXL SCHRIFT-EINSTELLUNGEN
    f_size_title = st.slider("Schriftgröße Titel", 50, 800, 300) 
    f_size_data = st.slider("Schriftgröße Daten", 50, 600, 180)
    b_height_adj = st.slider("Balken Dicke", 0.05, 0.50, 0.20)
    text_y_adj = st.slider("Text Position", -200, 200, 0)
    st.divider()
    c_line = st.color_picker("Routenfarbe", "#8B0000")
    w_line = st.slider("Linienstärke Route", 1, 100, 9)
    b_alpha = st.slider("Balken Deckkraft", 0, 255, 200)

# --- HAUPTBEREICH ---
up_img = st.file_uploader("📸 1. Foto wählen", type=["jpg", "jpeg", "png"])
up_gpx = st.file_uploader("📍 2. GPX Datei (Tour)")

if up_img and up_gpx:
    try:
        base_img = Image.open(up_img).convert("RGB")
        w, h = base_img.size
        
        up_gpx.seek(0)
        gpx = gpxpy.parse(up_gpx.read().decode("utf-8", errors="ignore"))
        
        pts, elevs = [], []
        d_total, a_gain = 0.0, 0.0
        last = None
        
        for tr in gpx.tracks:
            for seg in tr.segments:
                for p in seg.points:
                    pts.append([p.latitude, p.longitude])
                    elevs.append(p.elevation if p.elevation is not None else 0)
                    if last:
                        d_total += calc_dist(last[0], last[1], p.latitude, p.longitude)
                        if p.elevation is not None and last_elev is not None:
                            diff = p.elevation - last_elev
                            if diff > 0: a_gain += diff
                    last, last_elev = [p.latitude, p.longitude], p.elevation

        if pts:
            overlay = Image.new('RGBA', base_img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            
            # Balken
            bh_top = int(h * b_height_adj)
            bh_bot = int(h * (b_height_adj + 0.02))
            draw.rectangle([0, 0, w, bh_top], fill=(0, 0, 0, b_alpha))
            draw.rectangle([0, h - bh_bot, w, h], fill=(0, 0, 0, b_alpha))

            # --- DER SCHRIFT-FIX ---
            font_t = None
            # Wir suchen an allen Ecken nach einer Datei
            possible_fonts = [
                "font.ttf", # Deine eigene Datei in GitHub
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
            ]
            
            for fpath in possible_fonts:
                if os.path.exists(fpath):
                    font_t = ImageFont.truetype(fpath, f_size_title)
                    font_d = ImageFont.truetype(fpath, f_size_data)
                    break
            
            if font_t is None:
                st.error("KEINE SCHRIFT GEFUNDEN! Bitte lade eine .ttf Datei als 'font.ttf' in dein GitHub hoch.")
                font_t = font_d = ImageFont.load_default()

            # Texte schreiben
            draw.text((w//2, (bh_top//2) + text_y_adj), tour_title, fill="white", font=font_t, anchor="mm")
            stats_text = f"📍 {d_total:.1f} km  |  ⛰️ {int(a_gain)} m"
            draw.text((w//2, (h - bh_bot//2) + text_y_adj), stats_text, fill="white", font=font_d, anchor="mm")

            # Route (Stärke 9)
            lats, lons = zip(*pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            margin = 0.20
            scaled_pts = [(w*margin + (lon-mi_lo)/(ma_lo-mi_lo)*w*(1-2*margin), 
                           h*(1-margin) - (lat-mi_la)/(ma_la-mi_la)*h*(1-2*margin)) for lat, lon in pts]
            rgb = tuple(int(c_line[1:3], 16) if i==0 else int(c_line[3:5], 16) if i==1 else int(c_line[5:7], 16) for i in range(3))
            draw.line(scaled_pts, fill=rgb + (255,), width=w_line, joint="round")

            final = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
            st.image(final, use_container_width=True)
            
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), "gpx_share.jpg", "image/jpeg")

    except Exception as e:
        st.error(f"Fehler: {e}")
