import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont
import io
import math
import os

# --- APP KONFIGURATION & DESIGN ---
# RideLink Theme: Dunkler Hintergrund, Rote Buttons
st.set_page_config(page_title="RideLink Share", page_icon="🏍️", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #ffffff; }
    .title-modern {
        font-size: 36px; font-weight: 900;
        background: linear-gradient(90deg, #ff0000 0%, #8b0000 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 30px;
    }
    .stDownloadButton button {
        width: 100%; border-radius: 20px;
        background: linear-gradient(135deg, #ff0000 0%, #8b0000 100%) !important;
        color: white !important; font-weight: bold; border: none; height: 3em;
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
st.markdown("<p class='title-modern'>RideLink Share Pro</p>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    up_img = st.file_uploader("📸 1. Foto wählen", type=["jpg", "jpeg", "png"])
with c2:
    up_gpx = st.file_uploader("📍 2. GPX Datei (Tour)", type=["gpx"])

with st.sidebar:
    st.markdown("<h1 style='color: #ff0000;'>⚙️ Design-Setup</h1>", unsafe_allow_html=True)
    tour_title = st.text_input("Tour Name", value="Meine Tour")
    st.divider()
    font_size = st.slider("Schriftgröße", 20, 150, 70)
    c_line = st.color_picker("Routenfarbe", "#8B0000")
    w_line = st.slider("Linienstärke Route", 1, 30, 9) # Standard ist jetzt 9
    b_alpha = st.slider("Balken Deckkraft", 0, 255, 180)

if up_img and up_gpx:
    try:
        base_img = Image.open(up_img).convert("RGB")
        w, h = base_img.size
        
        up_gpx.seek(0)
        gpx = gpxpy.parse(up_gpx.read().decode("utf-8", errors="ignore"))
        
        pts, elevs = [], []
        d_total, a_gain = 0.0, 0.0
        last = None
        last_elev = None
        
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
            bh_top = int(h * 0.12)
            bh_bot = int(h * 0.14)
            draw.rectangle([0, 0, w, bh_top], fill=(0, 0, 0, b_alpha))
            draw.rectangle([0, h - bh_bot, w, h], fill=(0, 0, 0, b_alpha))

            # Höhenprofil
            if len(elevs) > 1:
                e_min, e_max = min(elevs), max(elevs)
                e_range = e_max - e_min if e_max > e_min else 1
                profile_pts = [((i/len(elevs))*w, (h-bh_bot)+(bh_bot*0.85)-((ev-e_min)/e_range)*(bh_bot*0.6)) for i, ev in enumerate(elevs)]
                # Farbe des Profils (60% des Routen-Rots)
                rgb = tuple(int(c_line[1:3], 16) if i==0 else int(c_line[3:5], 16) if i==1 else int(c_line[5:7], 16) for i in range(3))
                draw.polygon(profile_pts + [(w, h), (0, h)], fill=rgb + (60,))

            # Route zeichnen (Stärke 9)
            lats, lons = zip(*pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            margin = 0.20
            scaled_pts = [(w*margin + (lon-mi_lo)/(ma_lo-mi_lo)*w*(1-2*margin), 
                           h*(1-margin) - (lat-mi_la)/(ma_la-mi_la)*h*(1-2*margin)) for lat, lon in pts]
            # Route (Stärke 9, deckend)
            draw.line(scaled_pts, fill=rgb + (255,), width=w_line, joint="round")

            # Schrift laden
            try:
                # Pfad für Standard Linux Schriften auf Server
                f_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                if not os.path.exists(f_path):
                    f_path = "Roboto-Bold.ttf" # Falls du eine hochlädst
                font = ImageFont.truetype(f_path, font_size)
            except:
                font = ImageFont.load_default()

            # Texte schreiben
            draw.text((w//2, bh_top//2), tour_title, fill="white", font=font, anchor="mm")
            stats_text = f"📍 {d_total:.1f} km  |  ⛰️ {int(a_gain)} m"
            draw.text((w//2, h - bh_bot//2), stats_text, fill="white", font=font, anchor="mm")

            final = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
            st.image(final, use_container_width=True)
            
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            # Roter Download Button
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), "ride_share.jpg", "image/jpeg")

    except Exception as e:
        st.error(f"Fehler bei der Verarbeitung: {e}")
