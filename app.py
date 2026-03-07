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
        width: 100%; border-radius: 25px; height: 4em;
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
    up_img = st.file_uploader("📸 1. Foto wählen", type=["jpg", "jpeg", "png"], key="v16_img")
with c2:
    up_gpx = st.file_uploader("📍 2. GPX Datei wählen", type=["gpx", "xml", "txt"], key="v16_gpx")

# Tour-Name Vorschlag
default_name = "Meine Tour"
if up_gpx:
    default_name = os.path.splitext(up_gpx.name)[0].replace("_", " ").replace("-", " ")

with st.sidebar:
    st.markdown("<h1 style='color: #00f2fe;'>⚙️ Menü</h1>", unsafe_allow_html=True)
    tour_title = st.text_input("Tour Name", value=default_name, key="v16_title")
    st.divider()
    c_line = st.color_picker("Routenfarbe", "#00F2FE", key="v16_c")
    w_line = st.slider("Linienstärke", 5, 80, 25, key="v16_w")
    b_alpha = st.slider("Balken Deckkraft", 0, 255, 180, key="v16_alpha")

if up_img and up_gpx:
    try:
        # 1. Bild laden
        base_img = Image.open(up_img).convert("RGB")
        w, h = base_img.size
        
        # 2. GPX verarbeiten (mit 'seek(0)' um Fehler zu vermeiden)
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
            # Schriftart laden (System-Standard für Streamlit Cloud)
            try:
                # Nutzt die Standard Linux-Schriftart auf dem Server
                f_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                f_title = ImageFont.truetype(f_path, max(45, int(w/18)))
                f_data = ImageFont.truetype(f_path, max(35, int(w/22)))
            except:
                f_title = f_data = ImageFont.load_default()

            # 3. Zeichnen
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
            
            # Farbe konvertieren
            rgb = tuple(int(c_line[1:3], 16) if i==0 else int(c_line[3:5], 16) if i==1 else int(c_line[5:7], 16) for i in range(3))
            draw.line(scaled_pts, fill=rgb + (255,), width=w_line, joint="round")

            # --- GETEILTE INFO BALKEN ---
            # Balken oben
            bh_top = int(h * 0.10)
            draw.rectangle([0, 0, w, bh_top], fill=(0, 0, 0, b_alpha))
            # Balken unten
            bh_bot = int(h * 0.12)
            draw.rectangle([0, h - bh_bot, w, h], fill=(0, 0, 0, b_alpha))
            
            # Texte zentrieren (mm = middle/middle anchor)
            t_title = f"Tour: {tour_title}"
            t_data = f"Distanz: {d_total:.1f} km  |  Höhe: {int(a_gain)} m"
            
            # Text Oben
            draw.text((w//2, bh_top//2), t_title, fill="white", font=f_title, anchor="mm")
            # Text Unten
            draw.text((w//2, h - bh_bot//2), t_data, fill=c_line, font=f_data, anchor="mm")

            # Zusammenführen
            final = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
            st.image(final, use_container_width=True)
            
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD JETZT SPEICHERN", buf.getvalue(), "gpx_share.jpg", "image/jpeg")

    except Exception as e:
        st.error(f"Fehler: {e}")
else:
    st.info("Lade ein Foto und eine GPX-Datei hoch!")import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageFilter
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
        color: white !important; font-weight: bold; border: none; font-size: 18px;
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
st.markdown("<p class='title-modern'>GPX Share Pro</p>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    up_img = st.file_uploader("📸 1. Foto", type=["jpg", "jpeg", "png"], key="v20_img")
with col2:
    up_gpx = st.file_uploader("📍 2. GPX Datei", type=["gpx", "xml", "txt"], key="v20_gpx")

# Tour-Name Vorschlag
default_name = "Meine Tour"
if up_gpx:
    default_name = os.path.splitext(up_gpx.name)[0].replace("_", " ").replace("-", " ")

with st.sidebar:
    st.markdown("<h1 style='color: #00f2fe;'>⚙️ Menü</h1>", unsafe_allow_html=True)
    tour_title = st.text_input("Tour Name", value=default_name, key="v20_title")
    st.divider()
    c_line = st.color_picker("Routenfarbe", "#00F2FE", key="v20_c")
    w_line = st.slider("Linienstärke", 5, 80, 25, key="v20_w")
    b_alpha = st.slider("Deckkraft Box", 0, 255, 170, key="v20_alpha")

if up_img and up_gpx:
    try:
        # 1. Bild laden (Immer in festes 1080x1920 Hochformat zwingen)
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
            # --- DIE EINFACH-LÖSUNG FÜR SCHRIFTEN & ICONS ---
            try:
                # Pfad für Linux/Streamlit Cloud Server (DejaVuSans ist Standard)
                f_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                # Schriftgrößen massiv erhöht
                f_title = ImageFont.truetype(f_path, 80)
                f_data = ImageFont.truetype(f_path, 60)
            except:
                # Fallback für Windows/Mac
                f_title = f_data = ImageFont.load_default()

            # 3. Zeichnen (direkt auf das Bild, um Ausfransen zu vermeiden)
            draw = ImageDraw.Draw(base_img)
            
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
            
            # Glow-Effekt für die Route (verhindert das Ausfransen und sieht super aus)
            for i in range(6, 0, -2):
                draw.line(scaled_pts, fill=rgb + (50,), width=w_line + i, joint="round")
            draw.line(scaled_pts, fill=rgb + (255,), width=w_line, joint="round")

            # --- MODERNE INFO BOX (Glassmorphism + Icons) ---
            bw, bh = int(target_w * 0.90), int(target_h * 0.16)
            bx = (target_w - bw) // 2
            by = 100 # Box immer oben fixieren für den Pro-Look
            
            # Ebene für die Box (Overlay)
            box_overlay = Image.new('RGBA', (target_w, target_h), (0,0,0,0))
            draw_ov = ImageDraw.Draw(box_overlay)
            
            # Schatten (Blurred Rectangle)
            shadow_rect = [bx+10, by+10, bx+bw+10, by+bh+10]
            draw_ov.rectangle(shadow_rect, fill=(0, 0, 0, 80))
            
            # Haupt-Box (Transparent Schwarz)
            draw_ov.rectangle([bx, by, bx+bw, by+bh], fill=(0, 0, 0, b_alpha))
            
            # Farblinie am Rand (unten)
            draw_ov.rectangle([bx, by + bh - 12, bx+bw, by+bh], fill=rgb + (255,))
            
            # Zusammenfügen der Box mit dem Bild
            base_img = Image.alpha_composite(base_img.convert('RGBA'), box_overlay).convert('RGB')
            
            # Texte zentrieren (mm = middle/middle anchor)
            draw_final = ImageDraw.Draw(base_img)
            draw_final.text((target_w//2, by + bh//2 - 35), f"{tour_title}", fill="white", font=f_title, anchor="mm")
            
            # --- ICONS ---
            i_dist = "🗺️" # Landkarte für Distanz
            i_elev = "⛰️" # Berg für Höhe
            
            # Zeile Unten: Größer und mit Icons
            stats_text = f"{i_dist} {d_total:.1f} km  |  {i_elev} {int(a_gain)} m"
            draw_final.text((target_w//2, by + bh//2 + 45), stats_text, fill=c_line, font=f_data, anchor="mm")

            # Zusammenführen & Anzeigen
            st.image(base_img, use_container_width=True, caption="Dein fertiges Pro-Bild")
            
            buf = io.BytesIO()
            base_img.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD IM PRO-DESIGN SPEICHERN", buf.getvalue(), "gpx_share_pro.jpg", "image/jpeg")

    except Exception as e:
        st.error(f"Fehler: {e}")
else:
    st.info("Lade ein Foto und eine GPX-Datei hoch für den Pro-Look!")
