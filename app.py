import streamlit as st
import gpxpy
import gpxpy.gpx
from PIL import Image, ImageDraw, ImageFont
import io
import math

# --- KONFIGURATION & STYLING ---
st.set_page_config(page_title="GPX Share", page_icon="🏍️", layout="wide")

# Modernes CSS für den "Dark Look" und bessere Buttons
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #00f2fe;
        color: black;
        font-weight: bold;
        border: none;
    }
    .stDownloadButton>button {
        background-image: linear-gradient(to right, #00f2fe 0%, #4facfe 100%);
        color: white;
    }
    .css-10trblm { color: #00f2fe; } /* Überschriften Farbe */
    </style>
    """, unsafe_allow_html=True)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1); dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# --- SIDEBAR (MODERNE EINSTELLUNGEN) ---
with st.sidebar:
    st.title("⚙️ GPX Share")
    st.subheader("Design")
    line_color = st.color_picker("Linienfarbe", "#00F2FE")
    line_width = st.slider("Linienstärke", 1, 20, 8)
    
    st.divider()
    
    st.subheader("Infobox")
    show_stats = st.checkbox("Statistiken einblenden", value=True)
    box_pos = st.selectbox("Position", ["Oben Links", "Oben Rechts", "Unten Links", "Unten Rechts"])
    box_opacity = st.slider("Deckkraft Box", 0, 255, 180)
    
    st.divider()
    tour_name_input = st.text_input("Tour Name", "Meine Tour")

# --- HAUPTBEREICH ---
st.title("📸 GPX Share")
st.caption("Erstelle professionelle Bilder deiner Motorrad-Touren")

col1, col2 = st.columns([1, 1])
with col1:
    uploaded_image = st.file_uploader("1. Foto hochladen", type=["jpg", "jpeg", "png"])
with col2:
    uploaded_gpx = st.file_uploader("2. GPX Datei wählen", type=["gpx", "xml", "txt"])

if uploaded_image and uploaded_gpx:
    img = Image.open(uploaded_image).convert("RGB")
    w, h = img.size
    
    try:
        gpx = gpxpy.parse(uploaded_gpx.read().decode("utf-8"))
        points = []
        total_dist = 0.0
        alt_gain = 0.0
        last_p = None
        
        for track in gpx.tracks:
            for seg in track.segments:
                for p in seg.points:
                    points.append((p.latitude, p.longitude))
                    if last_p:
                        total_dist += haversine(last_p.latitude, last_p.longitude, p.latitude, p.longitude)
                        if p.elevation and last_p.elevation and p.elevation > last_p.elevation:
                            alt_gain += (p.elevation - last_p.elevation)
                    last_p = p

        if points:
            # Route skalieren & zeichnen
            lats, lons = zip(*points)
            min_lat, max_lat, min_lon, max_lon = min(lats), max(lats), min(lons), max(lons)
            margin = 0.15
            
            scaled = []
            for lat, lon in points:
                x = w * margin + (lon - min_lon) / (max_lon - min_lon) * w * (1 - 2*margin)
                y = h * (1 - margin) - (lat - min_lat) / (max_lat - min_lat) * h * (1 - 2*margin)
                scaled.append((x, y))
            
            draw_img = img.copy()
            draw = ImageDraw.Draw(draw_img)
            draw.line(scaled, fill=line_color, width=line_width, joint="round")

            if show_stats:
                # Box Design
                bw, bh = int(w * 0.38), int(h * 0.16)
                pos_map = {
                    "Oben Links": (40, 40), "Oben Rechts": (w-bw-40, 40),
                    "Unten Links": (40, h-bh-40), "Unten Rechts": (w-bw-40, h-bh-40)
                }
                bx, by = pos_map[box_pos]
                
                # Glas-Effekt Box
                overlay = Image.new('RGBA', draw_img.size, (0,0,0,0))
                odraw = ImageDraw.Draw(overlay)
                odraw.rectangle([bx, by, bx+bw, by+bh], fill=(0, 0, 0, box_opacity))
                draw_img = Image.alpha_composite(draw_img.convert('RGBA'), overlay).convert('RGB')
                
                # Text
                draw = ImageDraw.Draw(draw_img)
                f_size = max(24, int(w / 40))
                draw.text((bx+30, by+20), tour_name_input, fill="white")
                draw.text((bx+30, by+20+f_size*1.3), f"{total_dist:.1f} km | {int(alt_gain)} hm", fill=line_color)

            st.image(draw_img, use_container_width=True)
            
            # Export
            buf = io.BytesIO()
            draw_img.save(buf, format="JPEG", quality=95)
            st.download_button("💾 BILD SPEICHERN", buf.getvalue(), "gpx_share_export.jpg", "image/jpeg")

    except Exception as e:
        st.error(f"Fehler: {e}")
