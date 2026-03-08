import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps
import io
import math
import os
from datetime import datetime
from staticmap import StaticMap, Line as MapLine

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro XXL", page_icon="🏍️", layout="centered")

# --- STANDARDWERTE (v2.4.4: Kilometer-Meilensteine) ---
DEFAULTS = {
    "tour_title": "Meine Tour",
    "tour_date": "",
    "show_date": True,
    "bg_mode": "Automatisch",
    "weather": "Sonne",
    "bg_opacity": 100,
    "font_scale": 1.5,
    "data_font_scale": 1.2,
    "grid_font_scale": 1.5,
    "data_y_offset": 150,
    "route_scale": 1.0,
    "route_autoscale": True,
    "w_line": 9,
    "b_alpha": 160,
    "r_alpha": 255,
    "c_line": "#8B0000",
    "c_fill": "#8B0000",
    "c_box": "#000000",
    "b_height_adj": 0.20,
    "show_logo_on_img": True,
    "show_profile": True,
    "show_grid": True,
    "fill_profile": True,
    "selected_track_idx": 0,
    "show_markers": True,
    "show_km_steps": True,
    "km_interval": 20 
}

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

if "persistent_img" not in st.session_state: st.session_state.persistent_img = None
if "persistent_gpx" not in st.session_state: st.session_state.persistent_gpx = None

def reset_parameters():
    for key, val in DEFAULTS.items():
        st.session_state[key] = val

def load_font(size):
    paths = ["font.ttf", "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for p in paths:
        try: return ImageFont.truetype(p, int(size))
        except: continue
    return ImageFont.load_default()

def safe_rect(draw, coords, fill=None, outline=None, width=1):
    try:
        x0, y0, x1, y1 = coords
        sorted_coords = [int(min(x0, x1)), int(min(y0, y1)), int(max(x0, x1)), int(max(y0, y1))]
        draw.rectangle(sorted_coords, fill=fill, outline=outline, width=int(width))
    except: pass

def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def get_fitted_font(text, max_width, start_size):
    size = int(start_size)
    font = load_font(size)
    try:
        d = ImageDraw.Draw(Image.new('RGB', (1,1)))
        while d.textlength(text, font=font) > max_width and size > 10:
            size -= 2
            font = load_font(size)
    except: pass
    return font

def draw_text_with_shadow(draw, pos, text, font, fill="white", shadow_color="black", offset=2, anchor="mm"):
    x, y = pos
    draw.text((int(x+offset), int(y+offset)), text, fill=shadow_color, font=font, anchor=anchor)
    draw.text((int(x), int(y)), text, fill=fill, font=font, anchor=anchor)

def draw_marker(draw, pos, color, label=""):
    x, y = pos
    r = 14
    draw.ellipse([x-r-2, y-r-2, x+r+2, y+r+2], fill="white")
    draw.ellipse([x-r, y-r, x+r, y+r], fill=color, outline="black", width=2)
    if label:
        f = load_font(16)
        draw.text((x, y), label, fill="white", font=f, anchor="mm")

def draw_km_marker(draw, pos, km):
    x, y = pos
    r = 10
    draw.ellipse([x-r-1, y-r-1, x+r+1, y+r+1], fill="white")
    draw.ellipse([x-r, y-r, x+r, y+r], fill="#333333")
    f = load_font(12)
    draw.text((x, y), str(km), fill="white", font=f, anchor="mm")

st.markdown("""<style>.stApp { background-color: #ffffff; color: #000000; } .title-modern { font-size: 36px; font-weight: 900; background: linear-gradient(90deg, #ff0000 0%, #8b0000 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin-bottom: 20px; }</style>""", unsafe_allow_html=True)
st.markdown("<p class='title-modern'>GPX Share Pro</p>", unsafe_allow_html=True)

# --- UPLOADS ---
c_up1, c_up2 = st.columns(2)
with c_up1:
    up_gpx = st.file_uploader("📍 1. GPX Datei wählen")
    if up_gpx:
        new_data = up_gpx.read()
        if st.session_state.persistent_gpx != new_data:
            st.session_state.persistent_gpx = new_data
            gpx_obj = gpxpy.parse(io.BytesIO(new_data))
            if gpx_obj.time: st.session_state.tour_date = gpx_obj.time.strftime("%d.%m.%Y")
            st.session_state.tour_title = up_gpx.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
            st.rerun()

with c_up2:
    up_img = st.file_uploader("📸 2. Foto wählen (Optional)", type=["jpg", "jpeg", "png"])
    if up_img: st.session_state.persistent_img = up_img.read()

# --- OPTIONEN ---
with st.expander("⚙️ Optionen & Design", expanded=False):
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        st.write("**🖼️ Hintergrund & Marker**")
        st.selectbox("Hintergrund-Modus", ["Automatisch", "Nur Foto", "Nur Karte"], key="bg_mode")
        st.checkbox("Start/Ziel Markierungen", key="show_markers")
        st.checkbox("Km-Meilensteine anzeigen", key="show_km_steps")
        st.select_slider("Km-Intervall", options=[5, 10, 20, 50, 100], key="km_interval")
        st.slider("Hintergrund Dimmer (%)", 0, 100, key="bg_opacity")
    with col_opt2:
        st.write("**📐 Skalierung & Farbe**")
        st.slider("Titel-Größe", 0.5, 3.0, key="font_scale")
        st.slider("Vertikaler Abstand Daten", 50, 450, key="data_y_offset")
        st.color_picker("Routenfarbe", key="c_line")
        st.color_picker("Balkenfarbe", key="c_box")
    st.button("🔄 Reset", on_click=reset_parameters)

# --- INFO REITER ---
with st.expander("ℹ️ Über GPX Share Pro", expanded=False):
    st.markdown("### GPX Share Pro XXL | v2.4.4")
    st.markdown("**Copyright: Jürgen Unterweger**")
    st.markdown("📸 [Instagram](https://www.instagram.com/juergen_rocks/) | 👥 [Facebook](https://www.facebook.com/JuergenRocks/)")

st.divider()

# --- VERARBEITUNG ---
if st.session_state.persistent_gpx:
    try:
        gpx = gpxpy.parse(io.BytesIO(st.session_state.persistent_gpx))
        segments_pts, elevs = [], []
        d_total, a_gain, last, last_elev = 0.0, 0.0, None, None
        
        target_track = gpx.tracks[st.session_state.selected_track_idx]
        for seg in target_track.segments:
            current_seg = []
            for p in seg.points:
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
            w, h = 1080, 1920
            
            # Hintergrund
            canvas = Image.new('RGBA', (w, h), (255, 255, 255, 255))
            use_map = (st.session_state.bg_mode == "Nur Karte") or (st.session_state.bg_mode == "Automatisch" and not st.session_state.persistent_img)
            
            if not use_map and st.session_state.persistent_img:
                bg_img = ImageOps.exif_transpose(Image.open(io.BytesIO(st.session_state.persistent_img))).convert("RGBA")
                bg_img = ImageOps.fit(bg_img, (w, h), Image.Resampling.LANCZOS)
                canvas.paste(bg_img, (0, 0))
            else:
                m = StaticMap(w, h, url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png")
                m.add_line(MapLine(list(zip(lons, lats)), 'blue', 0))
                canvas.paste(m.render().convert("RGBA"), (0, 0))

            if st.session_state.bg_opacity < 100:
                canvas = Image.blend(Image.new('RGBA', (w, h), (255, 255, 255, 255)), canvas, st.session_state.bg_opacity / 100)

            overlay = Image.new('RGBA', (w, h), (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            rgb_box = tuple(int(st.session_state.c_box[i*2+1:i*2+3], 16) for i in range(3))
            bh_top, bh_bot = int(h * st.session_state.b_height_adj), int(h * 0.12)
            safe_rect(draw, [0, 0, w, bh_top], fill=rgb_box + (st.session_state.b_alpha,))
            safe_rect(draw, [0, h - bh_bot, w, h], fill=rgb_box + (st.session_state.b_alpha,))

            # TITEL & DATEN
            t_y = int(bh_top * 0.35)
            f_title = get_fitted_font(st.session_state.tour_title, w*0.9, int(w*0.08*st.session_state.font_scale))
            draw_text_with_shadow(draw, (w//2, t_y), st.session_state.tour_title, f_title)
            draw_text_with_shadow(draw, (w//2, t_y + st.session_state.data_y_offset), f"{d_total:.1f} km | {int(a_gain)} m", get_fitted_font("X km", w*0.7, int(w*0.05*st.session_state.data_font_scale)))

            # ROUTE TRANSFORMATION
            margin = 0.20 if st.session_state.route_autoscale else 0.5 * (1.0 - (0.4 * st.session_state.route_scale))
            rgb_route = tuple(int(st.session_state.c_line[i*2+1:i*2+3], 16) for i in range(3))
            la_eps = ma_la - mi_la if ma_la > mi_la else 0.001
            lo_eps = ma_lo - mi_lo if ma_lo > mi_lo else 0.001
            
            def transform(lat, lon):
                px = (w*margin + (lon-mi_lo)/lo_eps*w*(1-2*margin))
                py = (h*(1-margin) - (lat-mi_la)/la_eps*h*(1-2*margin))
                return (int(px), int(py))

            # Zeichne Route und sammle Kilometer-Punkte
            dist_acc = 0.0
            last_p = None
            km_marks = []
            next_km_goal = st.session_state.km_interval

            for seg in segments_pts:
                s_pts = []
                for p in seg:
                    curr_p = transform(p[0], p[1])
                    s_pts.append(curr_p)
                    if last_p:
                        # Berechne echte Welt-Distanz für Marker
                        seg_dist = calc_dist(last_raw[0], last_raw[1], p[0], p[1])
                        dist_acc += seg_dist
                        if st.session_state.show_km_steps and dist_acc >= next_km_goal:
                            km_marks.append((curr_p, int(next_km_goal)))
                            next_km_goal += st.session_state.km_interval
                    last_p = curr_p
                    last_raw = p
                if len(s_pts) > 1: draw.line(s_pts, fill=rgb_route + (st.session_state.r_alpha,), width=int(st.session_state.w_line), joint="round")

            # Km-Meilensteine zeichnen
            for pos, val in km_marks:
                draw_km_marker(draw, pos, val)

            # Start/Ziel Marker
            if st.session_state.show_markers and all_pts:
                draw_marker(draw, transform(all_pts[0][0], all_pts[0][1]), "green", "S")
                draw_marker(draw, transform(all_pts[-1][0], all_pts[-1][1]), "red", "Z")

            final = Image.alpha_composite(canvas, overlay).convert('RGB')
            st.image(final, use_container_width=True)
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), f"tour_km_v244.jpg", "image/jpeg")

    except Exception as e: st.error(f"Fehler: {e}")
