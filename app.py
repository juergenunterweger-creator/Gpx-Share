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
    up_img = st.file_uploader("📸 Foto wählen", type=["jpg", "jpeg", "png"], key="v23_1_img")
with c2:
    up_gpx = st.file_uploader("📍 GPX Datei", type=["gpx", "xml", "txt"], key="v23_1_gpx")

with st.sidebar:
    st.markdown("<h1 style='color: #ff0000;'>⚙️ Text-Turbo</h1>", unsafe_allow_html=True)
    tour_title = st.text_input("Tour Name", value="Meine Tour")
    st.divider()
    # Erhöhte Limits für massive Schriften
    f_size_title = st.slider("Größe Titel", 50, 500, 180) 
    f_size_data = st.slider("Größe Daten", 50, 400, 130)
    # Flexibler Balken-Faktor
    b_height_adj = st.slider("Balken Dicke", 0.05, 0.30, 0.16)
    text_y_adj = st.slider("Text Position", -150, 150, 0)
    st.divider()
    c_line = st.color_picker("Routenfarbe", "#8B0000")
    w_line = st.slider("Linienstärke", 5, 100, 25)
    b_alpha = st.slider("Balken Deckkraft", 0, 255, 190)

if up_img and up_gpx:
    try:
        base_img = Image.open(up_img).convert("RGB")
        w, h = base_img.size
        
        up_gpx.seek(0)
        gpx_raw = up_gpx.read().decode("utf-8", errors="ignore")
        gpx = gpxpy.parse(gpx_raw)
        
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
            
            # Route zeichnen
            lats, lons = zip(*pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            margin = 0.20
            scaled_pts = [(w*margin + (lon-mi_lo)/(ma_lo-mi_lo)*w*(1-2*margin), 
                           h*(1-margin) - (lat-mi_la)/(ma_la-mi_la)*h*(1-2*margin)) for lat, lon in pts]
            
            rgb = tuple(int(c_line[1:3], 16) if i==0 else int(c_line[3:5], 16) if i==1 else int(c_line[5:7], 16) for i in range(3))
            draw.line(scaled_pts, fill=rgb + (255,), width=w_line, joint="round")

            # Balken-Höhen basierend auf neuem Slider
            bh_top = int(h * b_height_adj)
            bh_bot = int(h * (b_height_adj + 0.02))
            
            draw.rectangle([0, 0, w, bh_top], fill=(0, 0, 0, b_alpha))
            draw.rectangle([0, h - bh_bot, w, h], fill=(0, 0, 0, b_alpha))

            # Höhenprofil im Hintergrund des unteren Balkens
            if len(elevs) > 1:
                e_min, e_max = min(elevs), max(elevs)
                e_range = e_max - e_min if e_max > e_min else 1
                profile_pts = [((i/len(elevs))*w, (h-bh_bot)+(bh_bot*0.8)-((ev-e_min)/e_range)*(bh_bot*0.6)) for i, ev in enumerate(elevs)]
                draw.polygon(profile_pts + [(w, h), (0, h)], fill=rgb + (60,))

            # Fette Schriftart laden
            try:
                f_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                font_t = ImageFont.truetype(f_path, f_size_title)
                font_d = ImageFont.truetype(f_path, f_size_data)
            except:
                font_t = font_d = ImageFont.load_default()

            # Texte zentriert mit manuellem Offset
            draw.text((w//2, (bh_top//2) + text_y_adj), tour_title, fill="white", font=font_t, anchor="mm")
            
            stats_text = f"📍 {d_total:.1f} km  |  ⛰️ {int(a_gain)} m"
            draw.text((w//2, (h - bh_bot//2) + text_y_adj), stats_text, fill="white", font=font_d, anchor="mm")

            final = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
            st.image(final, use_container_width=True)
            
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD MIT XXL-SCHRIFT SPEICHERN", buf.getvalue(), "gpx_share_big.jpg", "image/jpeg")

    except Exception as e:
        st.error(f"Fehler: {e}")
