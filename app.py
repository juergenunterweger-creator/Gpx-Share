import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont
import io
import math
import os

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share", page_icon="🏍️", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #ffffff; }
    .title-modern {
        font-size: 42px; font-weight: 900;
        background: linear-gradient(90deg, #ff0000 0%, #8b0000 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 20px;
    }
    .stDownloadButton button {
        width: 100%; border-radius: 25px; height: 4.5em;
        background: linear-gradient(135deg, #ff0000 0%, #8b0000 100%) !important;
        color: white !important; font-weight: bold; border: none;
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
    up_img = st.file_uploader("📸 1. Foto wählen", type=["jpg", "jpeg", "png"], key="v14_img")
with col2:
    up_gpx = st.file_uploader("📍 2. GPX Datei", type=["gpx", "xml", "txt"], key="v14_gpx")

# Tour-Name Vorschlag
default_name = "Meine Tour"
if up_gpx:
    default_name = os.path.splitext(up_gpx.name)[0].replace("_", " ").replace("-", " ")

with st.sidebar:
    st.markdown("<h1 style='color: #ff0000;'>⚙️ Menü</h1>", unsafe_allow_html=True)
    tour_title = st.text_input("Tour Name", value=default_name, key="v14_title")
    st.divider()
    # AUTOMATISCH BLUTROT (#8B0000)
    c_line = st.color_picker("Routenfarbe", "#8B0000", key="v14_c")
    # AUTOMATISCH STÄRKE 7
    w_line = st.slider("Linienstärke", 1, 50, 7, key="v14_w")
    b_pos = st.selectbox("Position der Box", ["Unten", "Oben", "Mitte"], key="v14_pos")
    b_alpha = st.slider("Box Deckkraft", 0, 255, 170, key="v14_alpha")

if up_img and up_gpx:
    try:
        base_img = Image.open(up_img).convert("RGB")
        w, h = base_img.size
        
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
            
            rgb = tuple(int(c_line[1:3], 16) if i==0 else int(c_line[3:5], 16) if i==1 else int(c_line[5:7], 16) for i in range(3))
            draw.line(scaled_pts, fill=rgb + (255,), width=w_line, joint="round")

            bw, bh = int(w * 0.88), int(h * 0.14)
            bx = (w - bw) // 2
            if b_pos == "Oben": by = 100
            elif b_pos == "Mitte": by = (h - bh) // 2
            else: by = h - bh - 150
            
            draw.rectangle([bx, by, bx+bw, by+bh], fill=(0, 0, 0, b_alpha))
            
            try:
                f_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                fs_title = max(40, int(w / 18))
                f_title = ImageFont.truetype(f_path, fs_title)
                f_data = ImageFont.truetype(f_path, int(fs_title * 0.8))
            except:
                f_title = f_data = ImageFont.load_default()

            draw.text((bx+50, by+35), f"Tour: {tour_title}", fill="white", font=f_title)
            draw.text((bx+50, by+35+fs_title+10), f"Distanz: {d_total:.1f} km  |  Höhe: {int(a_gain)} m", fill=c_line, font=f_data)

            final = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
            st.image(final, use_container_width=True)
            
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), "gpx_share.jpg", "image/jpeg")

    except Exception as e:
        st.error(f"Fehler: {e}")
else:
    st.info("Bitte lade ein Foto und eine GPX-Datei hoch!")
