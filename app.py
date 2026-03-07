import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFilter
import io
import math
import os
import folium
from streamlit_folium import folium_static

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share", page_icon="🏍️", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #080a0f; color: #ffffff; }
    .title-modern {
        font-size: 42px; font-weight: 900;
        background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 10px;
    }
    .stDownloadButton button {
        width: 100%; border-radius: 25px; height: 4.5em;
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%) !important;
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
st.markdown("<p class='title-modern'>GPX Share</p>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    up_img = st.file_uploader("📸 Foto (Optional)", type=["jpg", "jpeg", "png"], key="v12_img")
with col2:
    up_gpx = st.file_uploader("📍 GPX Datei", type=["gpx", "xml", "txt"], key="v12_gpx")

default_name = "Meine Tour"
if up_gpx:
    default_name = os.path.splitext(up_gpx.name)[0].replace("_", " ").replace("-", " ")

with st.sidebar:
    st.markdown("<h1 style='color: #00f2fe;'>⚙️ Menü</h1>", unsafe_allow_html=True)
    tour_title = st.text_input("Tour Name", value=default_name, key="v12_title")
    st.divider()
    c_line = st.color_picker("Linienfarbe", "#00F2FE", key="v12_c")
    w_line = st.slider("Linienstärke", 5, 80, 25, key="v12_w")
    b_pos = st.selectbox("Position der Box", ["Unten", "Oben", "Mitte"], key="v12_pos")
    b_alpha = st.slider("Box Deckkraft", 0, 255, 170, key="v12_alpha")

if up_gpx:
    try:
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
            # Hintergrund erstellen
            if up_img:
                img = Image.open(up_img).convert("RGB")
            else:
                # Erstellt einen vertikalen Blau-Schwarz Verlauf für den "Modern Look"
                img = Image.new('RGB', (1080, 1920), color=(10, 15, 30))
                draw_bg = ImageDraw.Draw(img)
                for i in range(1920):
                    color = (10, 15 + int(i/40), 30 + int(i/60))
                    draw_bg.line([(0, i), (1080, i)], fill=color)
            
            w, h = img.size
            overlay = Image.new('RGBA', img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            
            lats, lons = zip(*pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            margin = 0.22
            
            scaled_pts = []
            for lat, lon in pts:
                x = w * margin + (lon - mi_lo) / (ma_lo - mi_lo) * w * (1 - 2*margin)
                y = h * (1 - margin) - (lat - mi_la) / (ma_la - mi_la) * h * (1 - 2*margin)
                scaled_pts.append((x, y))
            
            rgb = tuple(int(c_line[1:3], 16) if i==0 else int(c_line[3:5], 16) if i==1 else int(c_line[5:7], 16) for i in range(3))
            
            # Glow-Effekt für die Route (optional, sieht auf dunklem Grund super aus)
            if not up_img:
                for i in range(5, 0, -1):
                    draw.line(scaled_pts, fill=rgb + (50,), width=w_line + i*4, joint="round")

            draw.line(scaled_pts, fill=rgb + (255,), width=w_line, joint="round")

            # Info Box
            bw, bh = int(w * 0.88), int(h * 0.14)
            bx = (w - bw) // 2
            by = 120 if b_pos == "Oben" else (h - bh) // 2 if b_pos == "Mitte" else h - bh - 150
            
            # Hellerer Rand für die Box ohne Foto
            draw.rectangle([bx, by, bx+bw, by+bh], fill=(0, 0, 0, b_alpha), outline=rgb if not up_img else None, width=5)
            
            draw.text((bx+50, by+40), f"Tour: {tour_title}", fill="white")
            draw.text((bx+50, by+40+70), f"{d_total:.1f} km  |  {int(a_gain)} m", fill=c_line)

            final = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            
            # Anzeige
            if not up_img:
                st.write("### 📍 Karten-Vorschau")
                m = folium.Map(tiles="OpenStreetMap")
                folium.PolyLine(pts, color=c_line, weight=5, opacity=0.8).add_to(m)
                m.fit_bounds([min(pts), max(pts)])
                folium_static(m, width=700, height=450)
            
            st.image(final, use_container_width=True, caption="Vorschau für den Download")
            
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), "gpx_share.jpg", "image/jpeg")

    except Exception as e:
        st.error(f"Fehler: {e}")
