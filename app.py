import streamlit as st
import gpxpy
import gpxpy.gpx
from PIL import Image, ImageDraw, ImageFont
import io
import math

# --- MODERN UI CONFIGURATION ---
st.set_page_config(page_title="GPX Share", page_icon="🏍️", layout="wide")

# Custom CSS für den "High-End" Look
st.markdown("""
    <style>
    /* Hintergrund und Schrift */
    .stApp { background-color: #0b0e14; color: #e0e0e0; }
    
    /* Der 'Menü'-Bereich in der Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid #30363d;
    }
    
    /* Buttons stylen */
    .stButton>button {
        border-radius: 12px;
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
        color: white;
        border: none;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 242, 254, 0.2);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 242, 254, 0.4);
    }
    
    /* Upload Box Design */
    [data-testid="stFileUploadDropzone"] {
        border: 2px dashed #30363d;
        border-radius: 15px;
        background-color: #1c2128;
    }
    
    /* Titel-Styling */
    h1 {
        background: -webkit-linear-gradient(#00f2fe, #4facfe);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
    }
    </style>
    """, unsafe_allow_html=True)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1); dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# --- SIDEBAR: DER DESIGN-HUB ---
with st.sidebar:
    st.markdown("## 🛠️ Menü")
    with st.expander("🎨 Farben & Stil", expanded=True):
        line_color = st.color_picker("Routenfarbe", "#00F2FE")
        line_width = st.slider("Linienstärke", 2, 25, 10)
        line_opacity = st.slider("Deckkraft Linie", 50, 255, 255)
    
    with st.expander("📊 Infobox & Text"):
        show_stats = st.checkbox("Statistiken anzeigen", value=True)
        tour_name = st.text_input("Tour Name", "Ranna Stausee")
        box_pos = st.selectbox("Position", ["Oben Links", "Oben Rechts", "Unten Links", "Unten Rechts"])
        box_alpha = st.slider("Box-Transparenz", 0, 255, 170)

    st.markdown("---")
    st.caption("GPX Share v2.0 | Made for Bikers 🏍️")

# --- MAIN INTERFACE ---
st.title("GPX Share")
st.markdown("Verwandle deine RideLink-Daten in hochwertige Social-Media-Bilder.")

c1, c2 = st.columns(2)
with c1:
    img_file = st.file_uploader("📸 Foto wählen", type=["jpg", "jpeg", "png"])
with c2:
    gpx_file = st.file_uploader("📍 GPX wählen", type=["gpx", "xml", "txt"])

if img_file and gpx_file:
    # Bildverarbeitung
    img = Image.open(img_file).convert("RGB")
    w, h = img.size
    
    try:
        gpx = gpxpy.parse(gpx_file.read().decode("utf-8"))
        points = []
        dist = 0.0
        alt = 0.0
        last = None
        
        for t in gpx.tracks:
            for s in t.segments:
                for p in s.points:
                    points.append((p.latitude, p.longitude))
                    if last:
                        dist += haversine(last.latitude, last.longitude, p.latitude, p.longitude)
                        if p.elevation and last.elevation and p.elevation > last.elevation:
                            alt += (p.elevation - last.elevation)
                    last = p

        if points:
            # Route skalieren
            lats, lons = zip(*points)
            min_lat, max_lat, min_lon, max_lon = min(lats), max(lats), min(lons), max(lons)
            
            # Zeichnen vorbereiten
            overlay = Image.new('RGBA', img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            
            margin = 0.15
            scaled = []
            for lat, lon in points:
                x = w * margin + (lon - min_lon) / (max_lon - min_lon) * w * (1 - 2*margin)
                y = h * (1 - margin) - (lat - min_lat) / (max_lat - min_lat) * h * (1 - 2*margin)
                scaled.append((x, y))
            
            # RGB Farbe zu RGBA konvertieren
            r = int(line_color[1:3], 16)
            g = int(line_color[3:5], 16)
            b = int(line_color[5:7], 16)
            
            draw.line(scaled, fill=(r, g, b, line_opacity), width=line_width, joint="round")

            if show_stats:
                bw, bh = int(w * 0.4), int(h * 0.15)
                pos_map = {
                    "Oben Links": (40, 40), "Oben Rechts": (w-bw-40, 40),
                    "Unten Links": (40, h-bh-40), "Unten Rechts": (w-bw-40, h-bh-40)
                }
                bx, by = pos_map[box_pos]
                
                # Modern Glass Box
                draw.rectangle([bx, by, bx+bw, by+bh], fill=(0, 0, 0, box_alpha))
                
                # Text auf das Overlay
                f_size = max(24, int(w / 45))
                draw.text((bx+25, by+20), tour_name, fill="white")
                draw.text((bx+25, by+20+f_size*1.4), f"{dist:.1f} km | {int(alt)} hm", fill=line_color)

            # Bilder zusammenführen
            final_img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            
            # Display & Download
            st.image(final_img, use_container_width=True)
            
            buf = io.BytesIO()
            final_img.save(buf, format="JPEG", quality=95)
            st.download_button("⚡ BILD JETZT SPEICHERN", buf.getvalue(), "gpx_share.jpg", "image/jpeg")

    except Exception as e:
        st.error(f"Daten-Fehler: {e}")
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
