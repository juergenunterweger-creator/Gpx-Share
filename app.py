import streamlit as st
import gpxpy
from PIL import Image, ImageDraw
import io
import math
import os
from streamlit_folium import folium_static
import folium

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share", page_icon="🏍️", layout="centered")

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
    up_img = st.file_uploader("📸 1. Foto (Optional)", type=["jpg", "jpeg", "png"], key="v8_img")
with col2:
    up_gpx = st.file_uploader("📍 2. GPX Datei", type=["gpx", "xml", "txt"], key="v8_gpx")

# Dynamischer Tour-Name
default_name = "Meine Tour"
if up_gpx:
    default_name = os.path.splitext(up_gpx.name)[0].replace("_", " ").replace("-", " ")

with st.sidebar:
    st.markdown("<h1 style='color: #00f2fe;'>⚙️ Menü</h1>", unsafe_allow_html=True)
    tour_title = st.text_input("Tour Bezeichnung", value=default_name, key="v8_title")
    st.divider()
    c_line = st.color_picker("Routenfarbe", "#00F2FE", key="v8_c")
    w_line = st.slider("Linienstärke", 5, 80, 25, key="v8_w")
    b_pos = st.selectbox("Position der Box", ["Unten", "Oben", "Mitte"], key="v8_pos")
    b_alpha = st.slider("Box Deckkraft", 0, 255, 170, key="v8_alpha")

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
                    pts.append((p.latitude, p.longitude))
                    if last:
                        d_total += calc_dist(last.latitude, last.longitude, p.latitude, p.longitude)
                        if p.elevation is not None and last.elevation is not None:
                            diff = p.elevation - last.elevation
                            if diff > 0: a_gain += diff
                    last = p

        if pts:
            # FALL 1: FOTO VORHANDEN -> BILD GENERIEREN
            if up_img:
                img = Image.open(up_img).convert("RGB")
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
                draw.line(scaled_pts, fill=rgb + (255,), width=w_line, joint="round")

                bw, bh = int(w * 0.88), int(h * 0.13)
                bx = (w - bw) // 2
                by = 100 if b_pos == "Oben" else (h - bh) // 2 if b_pos == "Mitte" else h - bh - 120
                draw.rectangle([bx, by, bx+bw, by+bh], fill=(0, 0, 0, b_alpha))
                
                fs_title, fs_data = max(40, int(w / 18)), max(35, int(w / 22))
                draw.text((bx+50, by+30), f"Tour: {tour_title}", fill="white")
                stats_str = f"Distanz: {d_total:.1f} km   |   Höhe: {int(a_gain)} m"
                draw.text((bx+50, by+30+fs_title+10), stats_str, fill=c_line)

                final = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
                st.image(final, use_container_width=True)
                
                buf = io.BytesIO()
                final.save(buf, format="JPEG", quality=95)
                st.download_button("🚀 BILD FÜR WHATSAPP SPEICHERN", buf.getvalue(), "gpx_share_tour.jpg", "image/jpeg")

            # FALL 2: KEIN FOTO -> OSM KARTE ZEIGEN
            else:
                st.success(f"Route geladen: {d_total:.1f} km | {int(a_gain)} m")
                # Mittelpunkt berechnen
                avg_lat = sum(p[0] for p in pts) / len(pts)
                avg_lon = sum(p[1] for p in pts) / len(pts)
                
                m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12, tiles="OpenStreetMap")
                folium.PolyLine(pts, color=c_line, weight=5, opacity=0.8).add_to(m)
                folium_static(m)
                st.info("Lade ein Foto hoch, um das fertige Share-Bild zu erstellen!")

    except Exception as e:
        st.error(f"Fehler: {e}")
else:
    st.info("Wähle eine GPX-Datei aus, um die Tour zu sehen!")
