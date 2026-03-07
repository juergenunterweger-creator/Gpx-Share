import streamlit as st
import gpxpy
from PIL import Image, ImageDraw
import io
import math

# --- VERTICAL APP DESIGN ---
st.set_page_config(page_title="GPX Share", page_icon="🏍️", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #080a0f; color: #ffffff; }
    .title-modern {
        font-size: 38px; font-weight: 900;
        background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 20px;
    }
    .stDownloadButton button {
        width: 100%; border-radius: 20px; height: 4em;
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%) !important;
        color: white !important; font-weight: bold; border: none;
    }
    </style>
    """, unsafe_allow_html=True)

def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color: #00f2fe;'>GPX Share</h1>", unsafe_allow_html=True)
    st.write("### 🎨 Design")
    c_route = st.color_picker("Routenfarbe", "#00F2FE", key="v6_c")
    w_route = st.slider("Linienstärke", 5, 60, 20, key="v6_w")
    st.divider()
    st.write("### 📝 Info-Box")
    t_name = st.text_input("Tour Name", "Ranna Stausee", key="v6_name")
    b_pos = st.selectbox("Position", ["Oben", "Mitte", "Unten"], key="v6_pos")
    b_alpha = st.slider("Deckkraft Box", 0, 255, 160, key="v6_alpha")

# --- MAIN ---
st.markdown("<p class='title-modern'>GPX Share</p>", unsafe_allow_html=True)

up_img = st.file_uploader("1. Foto (Hochkant)", type=["jpg", "jpeg", "png"], key="v6_img")
up_gpx = st.file_uploader("2. GPX Datei", type=["gpx", "xml", "txt"], key="v6_gpx")

if up_img and up_gpx:
    try:
        img = Image.open(up_img).convert("RGB")
        w, h = img.size
        
        # GPX robuster einlesen
        gpx_content = up_gpx.read().decode("utf-8", errors="ignore")
        gpx = gpxpy.parse(gpx_content)
        
        pts = []
        dist_total = 0.0
        alt_gain = 0.0
        last_pt = None
        
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    pts.append((point.latitude, point.longitude))
                    if last_pt:
                        dist_total += calc_dist(last_pt.latitude, last_pt.longitude, point.latitude, point.longitude)
                        if point.elevation is not None and last_pt.elevation is not None:
                            diff = point.elevation - last_pt.elevation
                            if diff > 0: alt_gain += diff
                    last_pt = point

        if pts:
            overlay = Image.new('RGBA', img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            
            lats, lons = zip(*pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            m = 0.20
            cw, ch = w * (1 - 2*m), h * (1 - 2*m)
            
            scaled = []
            for lat, lon in pts:
                x = w * m + (lon - mi_lo) / (ma_lo - mi_lo) * cw
                y = h * (1 - m) - (lat - mi_la) / (ma_la - mi_la) * ch
                scaled.append((x, y))
            
            # Route zeichnen
            rgb = tuple(int(c_route[i:i+2], 16) for i in (1, 3, 5))
            draw.line(scaled, fill=rgb + (255,), width=w_route, joint="round")

            # INFO BOX (Werte fixieren)
            bw, bh = int(w * 0.85), int(h * 0.14)
            bx = (w - bw) // 2
            if b_pos == "Oben": by = 80
            elif b_pos == "Mitte": by = (h - bh) // 2
            else: by = h - bh - 100
            
            draw.rectangle([bx, by, bx+bw, by+bh], fill=(0, 0, 0, b_alpha))
            
            # Text einfügen - mit Fallback falls keine Daten da sind
            fs = max(35, int(w / 22))
            val_text = f"{dist_total:.1f} km  |  {int(alt_gain)} hm"
            
            draw.text((bx+45, by+35), t_name, fill="white")
            draw.text((bx+45, by+35+fs*1.3), val_text, fill=c_route)

            res = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            st.image(res, use_container_width=True)
            
            buf = io.BytesIO()
            res.save(buf, format="JPEG", quality=95)
            st.download_button("💾 BILD SPEICHERN", buf.getvalue(), "motorrad_tour.jpg", "image/jpeg", key="v6_dl_btn")

    except Exception as e:
        st.error(f"Fehler beim Auslesen: {e}")
else:
    st.info("Bitte Foto und GPX-Datei hochladen. Dann erscheinen hier die Werte!")
