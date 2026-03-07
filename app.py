import streamlit as st
import gpxpy
import gpxpy.gpx
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
        text-align: center;
    }
    .stDownloadButton button {
        width: 100%; border-radius: 20px; height: 4em;
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%) !important;
        color: white !important; font-weight: bold; border: none;
        box-shadow: 0 10px 20px rgba(0, 242, 254, 0.2);
    }
    /* Optimierung für mobile Upload-Felder */
    [data-testid="stFileUploader"] { margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# --- SIDEBAR EINSTELLUNGEN ---
with st.sidebar:
    st.markdown("<h1 style='color: #00f2fe;'>GPX Share</h1>", unsafe_allow_html=True)
    st.write("### 🎨 Design")
    c_route = st.color_picker("Routenfarbe", "#00F2FE", key="v5_c")
    w_route = st.slider("Linienstärke", 5, 60, 20, key="v5_w")
    
    st.divider()
    
    st.write("### 📝 Info-Box")
    t_name = st.text_input("Tour Name", "Ranna Stausee", key="v5_name")
    b_pos = st.selectbox("Position", ["Oben", "Mitte", "Unten"], key="v5_pos")
    b_alpha = st.slider("Deckkraft Box", 0, 255, 160, key="v5_alpha")

# --- HAUPTBEREICH (HOCHKANT FOKUS) ---
st.markdown("<p class='title-modern'>GPX Share</p>", unsafe_allow_html=True)

up_img = st.file_uploader("1. Hochkant-Foto (9:16)", type=["jpg", "jpeg", "png"], key="v5_up_i")
up_gpx = st.file_uploader("2. GPX Datei", type=["gpx", "xml", "txt"], key="v5_up_g")

if up_img and up_gpx:
    try:
        img = Image.open(up_img).convert("RGB")
        w, h = img.size
        
        # GPX Parse
        gpx = gpxpy.parse(up_gpx.read().decode("utf-8"))
        pts = []
        dist, alt = 0.0, 0.0
        last = None
        
        for tr in gpx.tracks:
            for se in tr.segments:
                for p in se.points:
                    pts.append((p.latitude, p.longitude))
                    if last:
                        dist += calc_dist(last.latitude, last.longitude, p.latitude, p.longitude)
                        if p.elevation and last.elevation and p.elevation > last.elevation:
                            alt += (p.elevation - last.elevation)
                    last = p

        if pts:
            overlay = Image.new('RGBA', img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            
            # Route skalieren (zentriert mit mehr Rand für Hochkant)
            lats, lons = zip(*pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            
            # Dynamischer Rand (20% bei Hochkant sieht besser aus)
            m = 0.20
            cw, ch = w * (1 - 2*m), h * (1 - 2*m)
            
            scaled = []
            for lat, lon in pts:
                # Längengrad auf X, Breitengrad auf Y
                x = w * m + (lon - mi_lo) / (ma_lo - mi_lo) * cw
                y = h * (1 - m) - (lat - mi_la) / (ma_la - mi_la) * ch
                scaled.append((x, y))
            
            # Farbe
            rgb = tuple(int(c_route[i:i+2], 16) for i in (1, 3, 5))
            draw.line(scaled, fill=rgb + (255,), width=w_route, joint="round")

            # INFO BOX (Hochkant optimiert)
            bw, bh = int(w * 0.8), int(h * 0.12) # Breitere Box für Hochkant
            bx = (w - bw) // 2 # Immer zentriert
            
            if b_pos == "Oben": by = 60
            elif b_pos == "Mitte": by = (h - bh) // 2
            else: by = h - bh - 80
            
            # Glas-Box zeichnen
            draw.rectangle([bx, by, bx+bw, by+bh], fill=(0, 0, 0, b_alpha))
            
            # Text einfügen
            fs = max(30, int(w / 25))
            draw.text((bx+40, by+30), t_name, fill="white")
            draw.text((bx+40, by+30+fs*1.3), f"{dist:.1f} km | {int(alt)} hm", fill=c_route)

            # Finales Bild
            res = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            st.image(res, use_container_width=True)
            
            # DOWNLOAD
            buf = io.BytesIO()
            res.save(buf, format="JPEG", quality=95)
            st.download_button("💾 BILD FÜR WHATSAPP SPEICHERN", buf.getvalue(), "tour_portrait.jpg", "image/jpeg", key="v5_dl")

    except Exception as e:
        st.error(f"Fehler: {e}")
else:
    st.info("Lade ein Hochkant-Foto und deine GPX-Daten hoch!")
