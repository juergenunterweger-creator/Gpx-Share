import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont
import io
import math
import os
import random
import gc

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro XXL", page_icon="🏍️", layout="centered")

# --- STANDARDWERTE ---
DEFAULTS = {
    "tour_title": "Meine Tour",
    "font_scale": 1.5,
    "data_font_scale": 1.2,
    "data_y_offset": 160,
    "route_x_offset": 0,
    "route_y_offset": 0,
    "route_scale": 1.0,
    "route_autoscale": True,
    "img_x_offset": 0,
    "img_y_offset": 0,
    "img_zoom": 1.0,
    "b_height_adj": 0.20,
    "w_line": 9,
    "b_alpha": 160,
    "r_alpha": 255,
    "bg_alpha": 255,
    "c_line": "#8B0000",
    "c_fill": "#8B0000",
    "c_box": "#000000",
    "map_style": "OSM Standard",
    "show_logo": False,
    "show_profile": True,
    "show_grid": True,
    "show_icons": True,
    "show_units": True,
    "fill_profile": True,
    "selected_track_idx": 0 
}

# Initialisierung Session State
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

if "persistent_img" not in st.session_state: st.session_state.persistent_img = None
if "persistent_gpx" not in st.session_state: st.session_state.persistent_gpx = None
if "uploader_key" not in st.session_state: st.session_state.uploader_key = 0

def full_app_reset():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.uploader_key = random.randint(1, 9999)
    gc.collect()

def reset_parameters():
    for key, val in DEFAULTS.items():
        st.session_state[key] = val

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
    up_gpx = st.file_uploader("📍 1. GPX Datei wählen", key=f"gpx_up_{st.session_state.uploader_key}")
    if up_gpx:
        new_gpx_data = up_gpx.read()
        if st.session_state.persistent_gpx != new_gpx_data:
            st.session_state.persistent_gpx = new_gpx_data
            st.session_state.selected_track_idx = 0
            st.session_state.tour_title = up_gpx.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
            st.rerun()

with c_up2:
    up_img = st.file_uploader("📸 2. Foto wählen", type=["jpg", "jpeg", "png"], key=f"img_up_{st.session_state.uploader_key}")
    if up_img: st.session_state.persistent_img = up_img.read()

# --- OPTIONEN ---
with st.expander("⚙️ Optionen & Reset", expanded=False):
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        new_title = st.text_input("Tour Name", value=st.session_state.tour_title)
        if st.button("✅ Name übernehmen"):
            st.session_state.tour_title = new_title
            st.rerun()
        if st.session_state.persistent_gpx:
            try:
                temp_gpx = gpxpy.parse(io.BytesIO(st.session_state.persistent_gpx))
                if len(temp_gpx.tracks) > 1:
                    track_names = [f"Spur {i+1}: {t.name[:20] if t.name else 'Route'}" for i, t in enumerate(temp_gpx.tracks)]
                    st.selectbox("📍 Aktive Spur wählen", range(len(track_names)), format_func=lambda x: track_names[x], key="selected_track_idx")
            except: pass
        st.checkbox("Höhenprofil anzeigen", key="show_profile")
    with col_opt2:
        st.slider("Titel-Größe", 0.5, 3.0, key="font_scale")
        st.checkbox("Route Auto-Skalierung", key="route_autoscale")
        st.slider("Linienstärke", 1, 50, key="w_line")
        st.color_picker("Routenfarbe", key="c_line")
        st.color_picker("Infobox-Farbe", key="c_box")
    
    st.divider()
    c_res1, c_res2 = st.columns(2)
    with c_res1: st.button("🔄 Design zurücksetzen", on_click=reset_parameters)
    with c_res2: st.button("🗑️ KOMPLETT-RESET", on_click=full_app_reset)

with st.expander("ℹ️ Über"):
    st.markdown(f"**Copyright: Jürgen Unterweger** | **Version: 2.2**")
    st.markdown(f'[PayPal Spende](https://www.paypal.com/donate?hosted_button_id=FF6FBUE84V7MG)')

st.divider()

# --- PROCESSING (STRICT ISOLATION) ---
if st.session_state.persistent_gpx:
    try:
        gpx = gpxpy.parse(io.BytesIO(st.session_state.persistent_gpx))
        segments_pts = [] 
        elevs = []
        d_total, a_gain = 0.0, 0.0
        
        if len(gpx.tracks) > 0:
            # Nur den einen gewählten Track anfassen
            idx = min(st.session_state.selected_track_idx, len(gpx.tracks)-1)
            target_track = gpx.tracks[idx]
            
            for seg in target_track.segments:
                current_seg, last, last_elev = [], None, None
                for p in seg.points:
                    # De-Duplikation: Punkt nur hinzufügen, wenn er neu ist
                    if last and p.latitude == last[0] and p.longitude == last[1]:
                        continue
                        
                    current_seg.append([p.latitude, p.longitude])
                    elevs.append(p.elevation if p.elevation is not None else 0)
                    if last:
                        d_total += calc_dist(last[0], last[1], p.latitude, p.longitude)
                        if p.elevation is not None and last_elev is not None:
                            diff = p.elevation - last_elev
                            if diff > 0: a_gain += diff
                    last, last_elev = [p.latitude, p.longitude], p.elevation
                if current_seg: segments_pts.append(current_seg)

        if segments_pts:
            all_pts = [pt for seg in segments_pts for pt in seg]
            lats, lons = zip(*all_pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            
            # Bildaufbau
            if st.session_state.persistent_img:
                src_img = Image.open(io.BytesIO(st.session_state.persistent_img)).convert("RGBA")
                w, h = src_img.size
                src_img = src_img.resize((int(w * st.session_state.img_zoom), int(h * st.session_state.img_zoom)), Image.Resampling.LANCZOS)
            else:
                from staticmap import StaticMap, Line
                w, h = 1080, 1920
                m = StaticMap(w, h, url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png")
                m.add_line(Line(list(zip(lons, lats)), st.session_state.c_line, st.session_state.w_line))
                src_img = m.render().convert("RGBA")

            base_img = Image.new('RGBA', (w, h), (255, 255, 255, 255))
            base_img.paste(src_img, (0,0), src_img)
            overlay = Image.new('RGBA', base_img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            
            rgb_box = tuple(int(st.session_state.c_box[i*2+1:i*2+3], 16) for i in range(3))
            bh_top, bh_bot = int(h * st.session_state.b_height_adj), int(h * 0.12)
            draw.rectangle([0, 0, w, bh_top], fill=rgb_box + (st.session_state.b_alpha,))
            draw.rectangle([0, h - bh_bot, w, h], fill=rgb_box + (st.session_state.b_alpha,))

            # ROUTE ZEICHNEN
            base_margin = 0.20 if st.session_state.route_autoscale else 0.5 * (1.0 - (0.6 * st.session_state.route_scale))
            rgb_route = tuple(int(st.session_state.c_line[i*2+1:i*2+3], 16) for i in range(3))
            for seg in segments_pts:
                s_seg = [((w*base_margin + (lon-mi_lo)/(ma_lo-mi_lo)*w*(1-2*base_margin)) + st.session_state.route_x_offset, 
                          (h*(1-base_margin) - (lat-mi_la)/(ma_la-mi_la)*h*(1-2*base_margin)) + st.session_state.route_y_offset) for lat, lon in seg]
                if len(s_seg) > 1: draw.line(s_seg, fill=rgb_route + (st.session_state.r_alpha,), width=st.session_state.w_line, joint="round")

            font_path = "font.ttf" if os.path.exists("font.ttf") else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            font_t = get_fitted_font(draw, st.session_state.tour_title, w * 0.9, int(w * 0.085 * st.session_state.font_scale), font_path)
            draw.text((w//2, int(bh_top * 0.35)), st.session_state.tour_title, fill="white", font=font_t, anchor="mm")
            
            final = Image.alpha_composite(base_img, overlay).convert('RGB')
            st.image(final, use_container_width=True)
            
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), f"tour_{random.randint(1000,9999)}.jpg", "image/jpeg")
            
            # Speicher freigeben
            del segments_pts, elevs, all_pts, gpx
            gc.collect()

    except Exception as e: st.error(f"Fehler: {e}")
