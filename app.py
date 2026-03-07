import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont
import io
import math
import os
import requests

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro", page_icon="🏍️", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #ffffff; }
    .title-modern {
        font-size: 42px; font-weight: 900;
        background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 20px;
    }
    .stDownloadButton button {
        width: 100%; border-radius: 25px; height: 4.5em;
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%) !important;
        color: white !important; font-weight: bold; border: none; font-size: 18px;
    }
    div.stFileUploader { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# Hilfsfunktion zum Laden der Schriftart von GitHub
def get_font(url, size):
    response = requests.get(url)
    return ImageFont.truetype(io.BytesIO(response.content), size)

def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# --- HAUPTBEREICH ---
st.markdown("<p class='title-modern'>GPX Share Pro</p>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    up_img = st.file_uploader("📸 1. Foto (Portrait)", type=["jpg", "jpeg", "png"], key="v15_img")
with col2:
    up_gpx = st.file_uploader("📍 2. GPX Datei", type=["gpx", "xml", "txt"], key="v15_gpx")

# Tour-Name Vorschlag
default_name = "Meine Tour"
if up_gpx:
    default_name = os.path.splitext(up_gpx.name)[0].replace("_", " ").replace("-", " ")

with st.sidebar:
    st.markdown("<h1 style='color: #00f2fe;'>⚙️ Menü</h1>", unsafe_allow_html=True)
    tour_title = st.text_input("Tour Bezeichnung", value=default_name, key="v15_title")
    st.divider()
    c_line = st.color_picker("Routenfarbe", "#00F2FE", key="v15_c")
    w_line = st.slider("Linienstärke", 5, 80, 25, key="v15_w")
    b_alpha = st.slider("Deckkraft Balken", 0, 255, 170, key="v15_alpha")

if up_img and up_gpx:
    try:
        # 1. Bild laden
        base_img = Image.open(up_img).convert("RGB")
        w, h = base_img.size
        
        # 2. GPX verarbeiten
        gpx_raw = up_gpx.read().decode("utf-8", errors="ignore")
        gpx = gpxpy.parse(gpx_raw)
        
        pts = []
        d_total, a_gain = 0.0, 0.0
        last = None
        
        for tr in gpx.tracks:
            for seg in tr.segments:
                for p in seg.points:
                    pts.append([p.latitude, p.longitude])
                    if last:
                        d_total += calc_dist(last[0], last[1], p.latitude, p.longitude)
                        if p.elevation is not None and last_elev is not None:
                            diff = p.elevation - last_elev
                            if diff > 0: a_gain += diff
                    last = [p.latitude, p.longitude]
                    last_elev = p.elevation

        if pts:
            # --- SCHRIFTART LADEN (WICHTIG!) ---
            # Ersetze DEIN_USERNAME und DEIN_REPO durch deine Daten!
            FONT_URL = "https://raw.githubusercontent.com/DEIN_USERNAME/DEIN_REPO/main/Roboto-Bold.ttf"
            font_title = get_font(FONT_URL, max(50, int(w / 15)))
            font_data = get_font(FONT_URL, max(45, int(w / 18)))

            # 3. Zeichnen
            overlay = Image.new('RGBA', base_img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            
            lats, lons = zip(*pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            margin = 0.20
            
            scaled_pts = []
            for lat, lon in pts:
                x = w * margin + (lon - mi_lo) / (ma_lo - mi_lo) * w * (1 - 2*margin)
                y = h * (1 - margin) - (lat - mi_la) / (ma_la - mi_la) * h * (1 - 2*margin)
                scaled_pts.append((x, y))
            
            # Farbe konvertieren
            rgb = tuple(int(c_line[1:3], 16) if i==0 else int(c_line[3:5], 16) if i==1 else int(c_line[5:7], 16) for i in range(3))
            draw.line(scaled_pts, fill=rgb + (255,), width=w_line, joint="round")

            # --- GETEILTE INFO BALKEN ---
            
            # Balken Oben (für Tour Name)
            bh_top = int(h * 0.12)
            draw.rectangle([0, 0, w, bh_top], fill=(0, 0, 0, b_alpha))
            
            # Balken Unten (für Daten)
            bh_bot = int(h * 0.14)
            draw.rectangle([0, h - bh_bot, w, h], fill=(0, 0, 0, b_alpha))
            
            # --- TEXTE SCHREIBEN (MIT PRO-FONT) ---
            
            # Text Oben (Zentriert)
            title_text = f"Tour: {tour_title}"
            title_w, title_h = draw.textsize(title_text, font=font_title)
            draw.text(((w - title_w) // 2, (bh_top - title_h) // 2), title_text, fill="white", font=font_title)
            
            # Text Unten (Zentriert)
            data_text = f"Distanz: {d_total:.1f} km  |  Höhe: {int(a_gain)} m"
            data_w, data_h = draw.textsize(data_text, font=font_data)
            draw.text(((w - data_w) // 2, h - bh_bot + (bh_bot - data_h) // 2), data_text, fill=c_line, font=font_data)

            # Zusammenführen & Anzeigen
            final = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
            st.image(final, use_container_width=True, caption="Dein fertiges Pro-Bild")
            
            # Download
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD IN FOTOS SPEICHERN", buf.getvalue(), "gpx_share_pro.jpg", "image/jpeg")

    except Exception as e:
        st.error(f"Fehler: {e}")
else:
    st.info("Bitte Foto und GPX-Datei hochladen für den Pro-Look!")
