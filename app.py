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
    "bg_opacity": 100,
    "img_zoom": 1.0,
    "img_x_offset": 0,
    "img_y_offset": 0,
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

# DIE RETTER-FUNKTION GEGEN DEN CRASH
def safe_rect(draw, coords, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = coords
    # Erzwingt mathematische Korrektheit: x0 immer kleiner x1, y0 immer kleiner y1
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
with st.expander("⚙️ Optionen & Design", expanded=False):
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        st.write("**🖼️ Hintergrund**")
        st.slider("Sichtbarkeit (%)", 0, 100, key="bg_opacity")
        if st.session_state.persistent_img:
            st.slider("Zoom", 0.5, 3.0, key="img_zoom")
            st.slider("X-Versatz", -1000, 1000, key="img_x_offset")
            st.slider("Y-Versatz", -1000, 1000, key="img_y_offset")
        st.write("**📝 Texte**")
        new_title = st.text_input("Name", value=st.session_state.tour_title)
        new_date = st.text_input("Datum", value=st.session_state.tour_date)
        if st.button("✅ Übernehmen"):
            st.session_state.tour_title = new_title
            st.session_state.tour_date = new_date
            st.rerun()
    with col_opt2:
        st.write("**📈 Route**")
        st.checkbox("Auto-Skalieren", key="route_autoscale")
        if not st.session_state.route_autoscale:
            st.slider("Manuelle Größe", 0.1, 3.0, key="route_scale")
        st.write("**🎨 Farben**")
        st.color_picker("Routenfarbe", key="c_line")
        st.color_picker("Balkenfarbe", key="c_box")
        st.slider("Abstand Daten", 50, 400, key="data_y_offset")
    st.divider()
    st.button("🔄 Reset", on_click=reset_parameters)

# --- VERARBEITUNG ---
if st.session_state.persistent_gpx:
    try:
        gpx = gpxpy.parse(io.BytesIO(st.session_state.persistent_gpx))
        pts, elevs = [], []
        d_total, a_gain = 0.0, 0.0
        last, last_elev = None, None
        
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
            lats, lons = zip(*pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            w, h = 1080, 1920
            
            # HINTERGRUND
            canvas = Image.new('RGBA', (w, h), (255, 255, 255, 255))
            if st.session_state.persistent_img:
                bg_img = ImageOps.exif_transpose(Image.open(io.BytesIO(st.session_state.persistent_img))).convert("RGBA")
                bg_w, bg_h = bg_img.size
                ratio = max(w/bg_w, h/bg_h) * st.session_state.img_zoom
                bg_img = bg_img.resize((int(bg_w * ratio), int(bg_h * ratio)), Image.Resampling.LANCZOS)
                canvas.paste(bg_img, (st.session_state.img_x_offset, st.session_state.img_y_offset))
            else:
                m = StaticMap(w, h, url_template="http://tile.openstreetmap.org/{z}/{x}/{y}.png")
                m.add_line(MapLine(list(zip(lons, lats)), 'blue', 0))
                canvas.paste(m.render().convert("RGBA"), (0, 0))

            if st.session_state.bg_opacity < 100:
                canvas = Image.blend(Image.new('RGBA', (w, h), (255, 255, 255, 255)), canvas, st.session_state.bg_opacity / 100)

            overlay = Image.new('RGBA', (w, h), (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            rgb_box = tuple(int(st.session_state.c_box[i*2+1:i*2+3], 16) for i in range(3))
            bh_top, bh_bot = int(h * st.session_state.b_height_adj), int(h * 0.12)
            
            # BALKEN ZEICHNEN
            safe_rect(draw, [0, 0, w, bh_top], fill=rgb_box + (st.session_state.b_alpha,))
            safe_rect(draw, [0, h - bh_bot, w, h], fill=rgb_box + (st.session_state.b_alpha,))

            font_path = "font.ttf" if os.path.exists("font.ttf") else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            
            # TITEL
            title_y = int(bh_top * 0.35)
            f_title = get_fitted_font(draw, st.session_state.tour_title, w*0.9, int(w*0.08*st.session_state.font_scale), font_path)
            draw.text((w//2, title_y), st.session_state.tour_title, fill="white", font=f_title, anchor="mm")
            
            # DATEN
            txt_data = f"{d_total:.1f} km   |   {int(a_gain)} m"
            f_data = get_fitted_font(draw, txt_data, w*0.7, int(w*0.05*st.session_state.data_font_scale), font_path)
            draw.text((w//2, title_y + st.session_state.data_y_offset), txt_data, fill="white", font=f_data, anchor="mm")

            # DATUM BOX (SAFE DRAW)
            if st.session_state.show_date and st.session_state.tour_date:
                f_date_size = int(w*0.03*st.session_state.font_scale)
                f_date = ImageFont.truetype(font_path, f_date_size)
                tw = draw.textlength(st.session_state.tour_date, font=f_date)
                pad = 15
                # Dynamische Berechnung von rechts
                bx2 = w - 25
                bx1 = bx2 - tw - pad*2
                by2 = h - bh_bot - 20
                by1 = by2 - f_date_size - pad*2
                safe_rect(draw, [bx1, by1, bx2, by2], fill=rgb_box + (st.session_state.b_alpha,), outline="white")
                draw.text((bx1 + pad, by1 + pad), st.session_state.tour_date, fill="white", font=f_date)

            # ROUTE
            margin = 0.20 if st.session_state.route_autoscale else 0.5 * (1.0 - (0.4 * st.session_state.route_scale))
            rgb_route = tuple(int(st.session_state.c_line[i*2+1:i*2+3], 16) for i in range(3))
            route_points = [((w*margin + (lon-mi_lo)/(ma_lo-mi_lo)*w*(1-2*margin)), 
                             (h*(1-margin) - (lat-mi_la)/(ma_la-mi_la)*h*(1-2*margin))) for lat, lon in pts]
            if len(route_points) > 1:
                draw.line(route_points, fill=rgb_route + (st.session_state.r_alpha,), width=st.session_state.w_line, joint="round")

            final = Image.alpha_composite(canvas, overlay).convert('RGB')
            st.image(final, use_container_width=True)
            
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), f"tour_{datetime.now().strftime('%H%M')}.jpg", "image/jpeg")

    except Exception as e: st.error(f"Fehler: {e}")
