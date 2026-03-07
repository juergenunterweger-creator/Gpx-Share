import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont
import io
import math
import os

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro", page_icon="🏍️", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #ffffff; }
    .title-modern {
        font-size: 38px; font-weight: 900;
        background: linear-gradient(90deg, #ff0000 0%, #8b0000 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 20px;
    }
    .stDownloadButton button {
        width: 100%; border-radius: 25px; height: 4em;
        background: linear-gradient(135deg, #ff0000 0%, #8b0000 100%) !important;
        color: white !important; font-weight: bold; border: none;
    }
    </style>
    """, unsafe_allow_html=True)

def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# --- HAUPTBEREICH ---
st.markdown("<p class='title-modern'>GPX Share Pro</p>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    up_img = st.file_uploader("📸 Foto wählen", type=["jpg", "jpeg", "png"], key="v21_img")
with c2:
    up_gpx = st.file_uploader("📍 GPX Datei", type=["gpx", "xml", "txt"], key="v21_gpx")

# Tour-Name Vorschlag
default_name = "Meine Tour"
if up_gpx:
    default_name = os.path.splitext(up_gpx.name)[0].replace("_", " ").replace("-", " ")

with st.sidebar:
    st.markdown("<h1 style='color: #ff0000;'>⚙️ Einstellungen</h1>", unsafe_allow_html=True)
    tour_title = st.text_input("Tour Name", value=default_name)
    st.divider()
    c_line = st.color_picker("Routenfarbe", "#8B0000") # Blutrot
    w_line = st.slider("Linienstärke", 5, 50, 15)
    b_alpha = st.slider("Balken Deckkraft", 0, 255, 180)

if up_img and up_gpx:
    try:
        # 1. Bild laden
        base_img = Image.open(up_img).convert("RGB")
        w, h = base_img.size
        
        # 2. GPX verarbeiten
        up_gpx.seek(0)
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
            # Schriftarten (DejaVu ist Standard auf Streamlit Cloud)
            try:
                f_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                f_title = ImageFont.truetype(f_path, max(50, int(w/15)))
                f_data = ImageFont.truetype(f_path, max(40, int(w/20)))
            except:
                f_title = f_data = ImageFont.load_default()

            overlay = Image.new('RGBA', base_img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            
            # Route skalieren
            lats, lons = zip(*pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            margin = 0.18
            
            scaled_pts = []
            for lat, lon in pts:
                px_x = w * margin + (lon - mi_lo) / (ma_lo - mi_lo) * w * (1 - 2*margin)
                px_y = h * (1 - margin) - (lat - mi_la) / (ma_la - mi_la) * h * (1 - 2*margin)
                scaled_pts.append((px_x, px_y))
            
            # Farbe
            rgb = tuple(int(c_line[1:3], 16) if i==0 else int(c_line[3:5], 16) if i==1 else int(c_line[5:7], 16) for i in range(3))
            
            # Glow & Linie
            for i in range(3, 0, -1):
                draw.line(scaled_pts, fill=rgb + (40,), width=w_line + i*4, joint="round")
            draw.line(scaled_pts, fill=rgb + (255,), width=w_line, joint="round")

            # --- BALKEN OBEN & UNTEN ---
            bh_top = int(h * 0.11)
            bh_bot = int(h * 0.13)
            
            draw.rectangle([0, 0, w, bh_top], fill=(0, 0, 0, b_alpha))
            draw.rectangle([0, h - bh_bot, w, h], fill=(0, 0, 0, b_alpha))
            
            # Texte zentriert setzen
            draw.text((w//2, bh_top//2), tour_title, fill="white", font=f_title, anchor="mm")
            
            stats_text = f"📍 {d_total:.1f} km  |  ⛰️ {int(a_gain)} m"
            draw.text((w//2, h - bh_bot//2), stats_text, fill=c_line, font=f_data, anchor="mm")

            # Finalisieren
            final = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
            st.image(final, use_container_width=True)
            
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 FERTIGES BILD SPEICHERN", buf.getvalue(), "gpx_pro.jpg", "image/jpeg")

    except Exception as e:
        st.error(f"Fehler: {e}")
else:
    st.info("Lade Foto und GPX-Datei hoch!")
