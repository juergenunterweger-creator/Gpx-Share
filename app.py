import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import math
import os
from datetime import datetime
from staticmap import StaticMap, Line as MapLine

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro XXL", page_icon="🏍️", layout="centered")

# --- STANDARDWERTE ---
DEFAULTS = {
    "tour_title": "Meine Tour",
    "tour_date": "", 
    "show_date": True,
    "font_scale": 1.5,
    "data_font_scale": 1.2,
    "grid_font_scale": 1.5,
    "data_y_offset": 160,
    "route_scale": 1.0,
    "route_autoscale": True,
    "b_height_adj": 0.20,
    "w_line": 9,
    "b_alpha": 160,
    "r_alpha": 255,
    "c_line": "#8B0000",
    "c_box": "#000000",
}

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

if "persistent_img" not in st.session_state: st.session_state.persistent_img = None
if "persistent_gpx" not in st.session_state: st.session_state.persistent_gpx = None

def reset_parameters():
    for key, val in DEFAULTS.items():
        st.session_state[key] = val

def safe_rect(draw, coords, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = coords
    draw.rectangle([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], 
                   fill=fill, outline=outline, width=width)

# Styling
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #000000; }
    .title-modern {
        font-size: 36px; font-weight: 900;
        background: linear-gradient(90deg, #ff0000 0%, #8b0000 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 20px;
    }
    .stDownloadButton button, .stButton button {
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

def get_fitted_font(draw, text, max_width, start_size, font_path):
    size = int(start_size)
    try: font = ImageFont.truetype(font_path, size)
    except: font = ImageFont.load_default()
    while draw.textlength(text, font=font) > max_width and size > 10:
        size -= 2
        try: font = ImageFont.truetype(font_path, size)
        except: break
    return font

st.markdown("<p class='title-modern'>GPX Share Pro</p>", unsafe_allow_html=True)

# --- UPLOADS ---
c_up1, c_up2 = st.columns(2)
with c_up1:
    up_gpx = st.file_uploader("📍 1. GPX Datei wählen")
    if up_gpx:
        st.session_state.persistent_gpx = up_gpx.read()
        gpx_obj = gpxpy.parse(io.BytesIO(st.session_state.persistent_gpx))
        if st.session_state.tour_title == "Meine Tour":
            st.session_state.tour_title = up_gpx.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
        if gpx_obj.time and st.session_state.tour_date == "":
            st.session_state.tour_date = gpx_obj.time.strftime("%d.%m.%Y")

with c_up2:
    up_img = st.file_uploader("📸 2. Foto wählen (Optional)", type=["jpg", "jpeg", "png"])
    if up_img: st.session_state.persistent_img = up_img.read()

# --- OPTIONEN ---
with st.expander("⚙️ Optionen", expanded=False):
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        new_title = st.text_input("Name", value=st.session_state.tour_title)
        new_date = st.text_input("Datum", value=st.session_state.tour_date)
        if st.button("✅ Übernehmen"):
            st.session_state.tour_title = new_title
            st.session_state.tour_date = new_date
            st.rerun()
        st.checkbox("Datum anzeigen", key="show_date")
    with col_opt2:
        st.slider("Titel-Größe", 0.5, 3.0, key="font_scale")
        st.slider("Daten-Abstand", 50, 400, key="data_y_offset")
        st.color_picker("Routenfarbe", key="c_line")
        st.color_picker("Balkenfarbe", key="c_box")
    st.button("🔄 Reset", on_click=reset_parameters)

# --- ÜBER REITER ---
with st.expander("ℹ️ Über GPX Share Pro", expanded=False):
    # Hier wird das Logo angezeigt (Platzhalter-Check)
    if os.path.exists("logo.png"):
        st.image("logo.png", width=150)
    st.markdown("### GPX Share Pro XXL")
    st.markdown("**Copyright: Jürgen Unterweger** | **Version: 2.3.1**")
    st.markdown("[📸 Instagram](https://www.instagram.com/juergen_rocks/) | [👥 Facebook](https://www.facebook.com/JuergenRocks/)")
    st.divider()
    st.markdown("**📲 App installieren:**")
    st.info("iPhone: Teilen -> 'Zum Home-Bildschirm' | Android: Menü -> 'App installieren'")

st.divider()

# --- VERARBEITUNG ---
if st.session_state.persistent_gpx:
    try:
        gpx = gpxpy.parse(io.BytesIO(st.session_state.persistent_gpx))
        pts, d_total, a_gain = [], 0.0, 0.0
        last, last_elev = None, None
        
        for tr in gpx.tracks:
            for seg in tr.segments:
                for p in seg.points:
                    pts.append([p.latitude, p.longitude])
                    if last:
                        d_total += calc_dist(last[0], last[1], p.latitude, p.longitude)
                        if p.elevation is not None and last_elev is not None:
                            diff = p.elevation - last_elev
                            if diff > 0: a_gain += diff
                    last, last_elev = [p.latitude, p.longitude], p.elevation

        if pts:
            lats, lons = zip(*pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            w, h = 1080, 1920
            
            # --- HINTERGRUND-LOGIK ---
            if st.session_state.persistent_img:
                src_img = ImageOps.exif_transpose(Image.open(io.BytesIO(st.session_state.persistent_img))).convert("RGBA")
                # Bild auf Leinwand einpassen
                src_img = ImageOps.fit(src_img, (w, h), Image.Resampling.LANCZOS)
            else:
                # AUTOMATISCHE OSM KARTE
                m = StaticMap(w, h, url_template="http://tile.openstreetmap.org/{z}/{x}/{y}.png")
                m.add_line(MapLine(list(zip(lons, lats)), 'blue', 0)) # Zoom-Berechnung
                src_img = m.render().convert("RGBA")

            overlay = Image.new('RGBA', (w, h), (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            rgb_box = tuple(int(st.session_state.c_box[i*2+1:i*2+3], 16) for i in range(3))
            bh_top, bh_bot = int(h * st.session_state.b_height_adj), int(h * 0.12)
            
            safe_rect(draw, [0, 0, w, bh_top], fill=rgb_box + (st.session_state.b_alpha,))
            safe_rect(draw, [0, h - bh_bot, w, h], fill=rgb_box + (st.session_state.b_alpha,))

            font_path = "font.ttf" if os.path.exists("font.ttf") else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            
            # Titel
            title_y = int(bh_top * 0.35)
            f_title = get_fitted_font(draw, st.session_state.tour_title, w*0.9, int(w*0.08*st.session_state.font_scale), font_path)
            draw.text((w//2, title_y), st.session_state.tour_title, fill="white", font=f_title, anchor="mm")
            
            # Daten
            txt_data = f"{d_total:.1f} km   |   {int(a_gain)} m"
            f_data = get_fitted_font(draw, txt_data, w*0.7, int(w*0.05*st.session_state.data_font_scale), font_path)
            draw.text((w//2, title_y + st.session_state.data_y_offset), txt_data, fill="white", font=f_data, anchor="mm")

            # Route
            r_margin = 0.20
            rgb_route = tuple(int(st.session_state.c_line[i*2+1:i*2+3], 16) for i in range(3))
            scaled = [((w*r_margin + (lon-mi_lo)/(ma_lo-mi_lo)*w*(1-2*r_margin)), 
                       (h*(1-r_margin) - (lat-mi_la)/(ma_la-mi_la)*h*(1-2*r_margin))) for lat, lon in pts]
            if len(scaled) > 1:
                draw.line(scaled, fill=rgb_route + (st.session_state.r_alpha,), width=st.session_state.w_line, joint="round")

            final = Image.alpha_composite(src_img, overlay).convert('RGB')
            st.image(final, use_container_width=True)
            
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), f"tour_{datetime.now().strftime('%H%M')}.jpg", "image/jpeg")

    except Exception as e: st.error(f"Fehler: {e}")
