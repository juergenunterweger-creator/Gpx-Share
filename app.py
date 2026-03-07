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
        font-size: 40px; font-weight: 900;
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
st.markdown("<p class='title-modern'>GPX Share Pro</p>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    up_img = st.file_uploader("📸 1. Foto wählen", type=["jpg", "jpeg", "png"], key="v18_img")
with c2:
    up_gpx = st.file_uploader("📍 2. GPX Datei", type=["gpx", "xml", "txt"], key="v18_gpx")

# Tour-Name Vorschlag
default_name = "Meine Tour"
if up_gpx:
    default_name = os.path.splitext(up_gpx.name)[0].replace("_", " ").replace("-", " ")

with st.sidebar:
    st.markdown("<h1 style='color: #00f2fe;'>⚙️ Menü</h1>", unsafe_allow_html=True)
    tour_title = st.text_input("Tour Name", value=default_name, key="v18_title")
    st.divider()
    c_line = st.color_picker("Routenfarbe", "#00F2FE", key="v18_c")
    w_line = st.slider("Linienstärke", 5, 80, 25, key="v18_w")
    b_alpha = st.slider("Balken Deckkraft", 0, 255, 180, key="v18_alpha")

if up_img and up_gpx:
    try:
        # 1. Bild laden und in festes HOCHFORMAT (1080x1920) bringen
        user_img = Image.open(up_img).convert("RGB")
        uw, uh = user_img.size
        target_w, target_h = 1080, 1920
        base_img = Image.new('RGB', (target_w, target_h), (0, 0, 0))
        
        ratio = min(target_w/uw, target_h/uh)
        new_w, new_h = int(uw*ratio), int(uh*ratio)
        user_img_resized = user_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        offset = ((target_w - new_w) // 2, (target_h - new_h) // 2)
        base_img.paste(user_img_resized, offset)
        
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
            # --- DIE EINFACH-LÖSUNG FÜR SCHRIFTEN ---
            try:
                # Pfad für Linux/Streamlit Cloud Server
                f_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                f_title = ImageFont.truetype(f_path, 65)
                f_data = ImageFont.truetype(f_path, 50)
            except:
                # Fallback für Windows/Mac oder falls Pfad anders ist
                f_title = f_data = ImageFont.load_default()

            # 3. Zeichnen
            overlay = Image.new('RGBA', (target_w, target_h), (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            
            lats, lons = zip(*pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            
            margin = 60 
            draw_area_w = new_w - 2*margin
            draw_area_h = new_h - 2*margin
            
            scaled_pts = []
            for lat, lon in pts:
                x = offset[0] + margin + (lon - mi_lo) / (ma_lo - mi_lo) * draw_area_w
                y = offset[1] + new_h - margin - (lat - mi_la) / (ma_la - mi_la) * draw_area_h
                scaled_pts.append((x, y))
            
            rgb = tuple(int(c_line[1:3], 16) if i==0 else int(c_line[3:5], 16) if i==1 else int(c_line[5:7], 16) for i in range(3))
            draw.line(scaled_pts, fill=rgb + (255,), width=w_line, joint="round")

            # --- GETEILTE BALKEN ---
            bh_top = 230
            draw.rectangle([0, 0, target_w, bh_top], fill=(0, 0, 0, b_alpha))
            bh_bot = 260
            draw.rectangle([0, target_h - bh_bot, target_w, target_h], fill=(0, 0, 0, b_alpha))
            
            # Texte schreiben (mm = middle/middle anchor)
            draw.text((target_w//2, bh_top//2), f"Tour: {tour_title}", fill="white", font=f_title, anchor="mm")
            stats_text = f"Distanz: {d_total:.1f} km  |  Höhe: {int(a_gain)} m"
            draw.text((target_w//2, target_h - bh_bot//2), stats_text, fill=c_line, font=f_data, anchor="mm")

            # Zusammenführen
            final = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
            st.image(final, use_container_width=True)
            
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD IM HOCHFORMAT SPEICHERN", buf.getvalue(), "gpx_share.jpg", "image/jpeg")

    except Exception as e:
        st.error(f"Fehler: {e}")
else:
    st.info("Lade Foto und GPX-Datei hoch!")
