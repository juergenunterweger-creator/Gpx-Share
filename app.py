import streamlit as st
import gpxpy
from PIL import Image, ImageDraw
import io
import math
import os

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share", page_icon="🏍️", layout="centered")

# Modernes CSS für den Hochkant-Look & Icons
st.markdown("""
    <style>
    .stApp { background-color: #080a0f; color: #ffffff; }
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

def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# --- HAUPTBEREICH ---
st.markdown("<p class='title-modern'>GPX Share</p>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    up_img = st.file_uploader("📸 1. Foto (Hochformat)", type=["jpg", "jpeg", "png"], key="v7_img")
with col2:
    up_gpx = st.file_uploader("📍 2. GPX Datei", type=["gpx", "xml", "txt"], key="v7_gpx")

# Dynamischer Tour-Name basierend auf der Datei
default_tour_name = "Meine Tour"
if up_gpx:
    # Nimmt den Dateinamen ohne Endung als Vorschlag
    default_tour_name = os.path.splitext(up_gpx.name)[0].replace("_", " ").replace("-", " ")

# --- SIDEBAR EINSTELLUNGEN ---
with st.sidebar:
    st.markdown("<h1 style='color: #00f2fe;'>⚙️ Menü</h1>", unsafe_allow_html=True)
    
    st.write("### 📝 Tour Info")
    # Hier ist der Name änderbar, aber mit dem Dateinamen vorbefüllt
    tour_title = st.text_input("Tour Bezeichnung", value=default_tour_name, key="v7_title")
    
    st.divider()
    
    st.write("### 🎨 Design")
    c_line = st.color_picker("Linienfarbe", "#00F2FE", key="v7_c")
    w_line = st.slider("Linienstärke", 5, 80, 25, key="v7_w")
    b_pos = st.selectbox("Position der Box", ["Unten", "Oben", "Mitte"], key="v7_pos")
    b_alpha = st.slider("Box Deckkraft", 0, 255, 170, key="v7_alpha")

if up_img and up_gpx:
    try:
        # Bild laden
        img = Image.open(up_img).convert("RGB")
        w, h = img.size
        
        # GPX Daten verarbeiten
        gpx_raw = up_gpx.read().decode("utf-8", errors="ignore")
        gpx = gpxpy.parse(gpx_raw)
        
        pts = []
        d_total = 0.0
        a_gain = 0.0
        last = None
        
        for tr in gpx.tracks:
            for seg in tr.segments:
                for p in seg.points:
                    pts.append((p.latitude, p.longitude))
                    if last:
                        d_total += calc_dist(last.latitude, last.longitude, p.latitude, p.longitude)
                        if p.elevation is not None and last.elevation is not None:
                            diff = p.elevation - last.elevation
                            if diff > 0: a_gain += diff
                    last = p

        if pts:
            # Ebene für die Route
            overlay = Image.new('RGBA', img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            
            # Route skalieren & zentrieren
            lats, lons = zip(*pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            margin = 0.22 # Genug Platz zum Rand
            
            # Berechnung der Linienpunkte
            scaled_pts = []
            for lat, lon in pts:
                x = w * margin + (lon - mi_lo) / (ma_lo - mi_lo) * w * (1 - 2*margin)
                y = h * (1 - margin) - (lat - mi_la) / (ma_la - mi_la) * h * (1 - 2*margin)
                scaled_pts.append((x, y))
            
            # Route zeichnen
            rgb = tuple(int(c_line[i:i+2], 16) for i in (1, 3, 5))
            draw.line(scaled_pts, fill=rgb + (255,), width=w_line, joint="round")

            # --- INFO BOX ---
            bw, bh = int(w * 0.88), int(h * 0.13)
            bx = (w - bw) // 2
            
            if b_pos == "Oben": by = 100
            elif b_pos == "Mitte": by = (h - bh) // 2
            else: by = h - bh - 120
            
            # Hintergrund der Box
            draw.rectangle([bx, by, bx+bw, by+bh], fill=(0, 0, 0, b_alpha))
            
            # Werte schreiben
            fs_title = max(40, int(w / 18))
            fs_data = max(35, int(w / 22))
            
            # Zeile 1: Tour Name
            draw.text((bx+50, by+30), f"Tour: {tour_title}", fill="white")
            # Zeile 2: Daten (Distanz & Höhe)
            stats_str = f"Distanz: {d_total:.1f} km   |   Höhe: {int(a_gain)} m"
            draw.text((bx+50, by+30+fs_title+10), stats_str, fill=c_line)

            # Zusammenfügen
            final = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            st.image(final, use_container_width=True)
            
            # Download Bereich
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD FÜR WHATSAPP SPEICHERN", buf.getvalue(), "gpx_share_tour.jpg", "image/jpeg", key="v7_btn")

    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
else:
    st.info("Lade ein Foto und eine GPX-Datei hoch, um dein Tour-Bild zu erstellen!")
