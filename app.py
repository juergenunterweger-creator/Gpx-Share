import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageChops
import io
import math
import os
from datetime import datetime

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro XXL", page_icon="🏍️", layout="centered")

# --- STANDARDWERTE ---
DEFAULTS = {
    "tour_title": "Meine Tour",
    "tour_date": "",
    "show_date": True,
    "weather": "Sonne",
    "bg_opacity": 100,
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

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

if "persistent_img" not in st.session_state: st.session_state.persistent_img = None
if "persistent_gpx" not in st.session_state: st.session_state.persistent_gpx = None

def reset_parameters():
    for key, val in DEFAULTS.items():
        st.session_state[key] = val
    st.rerun()

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

def draw_smooth_icon(mode, size, color="white"):
    res = 4
    img = Image.new('RGBA', (size*res, size*res), (0,0,0,0))
    d = ImageDraw.Draw(img)
    lw = max(4, int(size*res*0.07))
    if mode == "dist":
        d.arc([lw, lw, size*res-lw, size*res-lw], 140, 400, fill=color, width=lw)
        cx, cy = size*res//2, size*res//2
        ex, ey = cx + math.cos(math.radians(300))*(cx*0.7), cy + math.sin(math.radians(300))*(cy*0.7)
        d.line([cx, cy, ex, ey], fill=color, width=lw)
        d.ellipse([cx-lw, cy-lw, cx+lw, cy+lw], fill=color)
    elif mode == "elev":
        d.polygon([(lw, size*res-lw), (size*res*0.5, lw*2), (size*res*0.9, size*res-lw)], fill=color)
    elif mode == "Sonne":
        d.ellipse([size*res*0.3, size*res*0.3, size*res*0.7, size*res*0.7], fill=color)
        for i in range(0, 360, 45):
            rad = math.radians(i)
            d.line([size*res*0.5+math.cos(rad)*size*res*0.25, size*res*0.5+math.sin(rad)*size*res*0.25,
                    size*res*0.5+math.cos(rad)*size*res*0.45, size*res*0.5+math.sin(rad)*size*res*0.45], fill=color, width=lw)
    return img.resize((size, size), Image.Resampling.LANCZOS)

st.markdown("<p class='title-modern'>GPX Share Pro</p>", unsafe_allow_html=True)

# --- UPLOADS ---
c_up1, c_up2 = st.columns(2)
with c_up1:
    up_gpx = st.file_uploader("📍 1. GPX Datei wählen")
    if up_gpx:
        new_gpx_data = up_gpx.read()
        if st.session_state.persistent_gpx != new_gpx_data:
            st.session_state.persistent_gpx = new_gpx_data
            gpx_obj = gpxpy.parse(io.BytesIO(new_gpx_data))
            if gpx_obj.time: st.session_state.tour_date = gpx_obj.time.strftime("%d.%m.%Y")
            st.session_state.tour_title = up_gpx.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
            st.rerun()

with c_up2:
    up_img = st.file_uploader("📸 2. Foto wählen", type=["jpg", "jpeg", "png"])
    if up_img: st.session_state.persistent_img = up_img.read()

# --- OPTIONEN ---
with st.expander("⚙️ Optionen", expanded=False):
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        st.write("**📝 Texte & Stimmung**")
        new_title = st.text_input("Name", value=st.session_state.tour_title)
        new_date = st.text_input("Datum", value=st.session_state.tour_date)
        if st.button("✅ Übernehmen"):
            st.session_state.tour_title, st.session_state.tour_date = new_title, new_date
            st.rerun()
        st.selectbox("Wetter", ["Sonne", "Wolken", "Regen", "Schnee"], key="weather")
        st.slider("Hintergrund Sichtbarkeit (%)", 0, 100, key="bg_opacity")
        st.checkbox("Datum & Wetter anzeigen", key="show_date")
        st.checkbox("Höhenprofil anzeigen", key="show_profile")

    with col_opt2:
        st.write("**📐 Skalierung & Farbe**")
        st.slider("Titel-Größe", 0.5, 3.0, key="font_scale")
        st.slider("Daten-Abstand", 50, 400, key="data_y_offset")
        st.checkbox("Route Auto-Skalierung", key="route_autoscale")
        st.color_picker("Routenfarbe", key="c_line")
        st.color_picker("Balkenfarbe", key="c_box")
    st.button("🔄 Einstellungen zurücksetzen", on_click=reset_parameters)

# --- VERARBEITUNG ---
if st.session_state.persistent_gpx:
    try:
        gpx = gpxpy.parse(io.BytesIO(st.session_state.persistent_gpx))
        segments_pts, elevs = [], []
        d_total, a_gain, last, last_elev = 0.0, 0.0, None, None
        
        idx = min(st.session_state.selected_track_idx, len(gpx.tracks)-1)
        target_track = gpx.tracks[idx]
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
            if st.session_state.persistent_img:
                bg_img = Image.open(io.BytesIO(st.session_state.persistent_img)).convert("RGBA")
                bg_img = bg_img.resize((int(bg_img.width * (w/bg_img.width)), int(bg_img.height * (w/bg_img.width))), Image.Resampling.LANCZOS)
                canvas.paste(bg_img, (0, 0))
            else:
                from staticmap import StaticMap, Line
                m = StaticMap(w, h, url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png")
                m.add_line(Line(list(zip(lons, lats)), st.session_state.c_line, 0))
                canvas.paste(m.render().convert("RGBA"), (0, 0))

            if st.session_state.bg_opacity < 100:
                canvas = Image.blend(Image.new('RGBA', (w, h), (255, 255, 255, 255)), canvas, st.session_state.bg_opacity / 100)

            overlay = Image.new('RGBA', (w, h), (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            rgb_box = tuple(int(st.session_state.c_box[i*2+1:i*2+3], 16) for i in range(3))
            bh_top, bh_bot = int(h * st.session_state.b_height_adj), int(h * 0.12)
            draw.rectangle([0, 0, w, bh_top], fill=rgb_box + (st.session_state.b_alpha,))
            draw.rectangle([0, h - bh_bot, w, h], fill=rgb_box + (st.session_state.b_alpha,))

            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            
            # Titel & Daten
            title_y = int(bh_top * 0.35)
            f_t = get_fitted_font(draw, st.session_state.tour_title, w*0.9, int(w*0.08*st.session_state.font_scale), font_path)
            draw.text((w//2, title_y), st.session_state.tour_title, fill="white", font=f_t, anchor="mm")
            draw.text((w//2, title_y + st.session_state.data_y_offset), f"{d_total:.1f} km | {int(a_gain)} m", fill="white", font=get_fitted_font(draw, "X km", w*0.7, int(w*0.05*st.session_state.data_font_scale), font_path), anchor="mm")

            # Wetter & Datum Badge
            if st.session_state.show_date and st.session_state.tour_date:
                f_date = ImageFont.truetype(font_path, int(w*0.03*st.session_state.font_scale))
                tw = draw.textlength(st.session_state.tour_date, font=f_date)
                bx2, by2 = w - 25, h - bh_bot - 20
                draw.rectangle([bx2 - tw - 80, by2 - 60, bx2, by2], fill=rgb_box + (st.session_state.b_alpha,), outline="white")
                draw.text((bx2 - 15, by2 - 30), st.session_state.tour_date, fill="white", font=f_date, anchor="rm")
                w_icon = draw_smooth_icon(st.session_state.weather, 40)
                overlay.paste(w_icon, (int(bx2 - tw - 70), int(by2 - 50)), w_icon)

            # Route & Profil
            margin = 0.20 if st.session_state.route_autoscale else 0.5 * (1.0 - (0.4 * st.session_state.route_scale))
            rgb_route = tuple(int(st.session_state.c_line[i*2+1:i*2+3], 16) for i in range(3))
            for seg in segments_pts:
                s_pts = [((w*margin + (lon-mi_lo)/(ma_lo-mi_lo)*w*(1-2*margin)), (h*(1-margin) - (lat-mi_la)/(ma_la-mi_la)*h*(1-2*margin))) for lat, lon in seg]
                if len(s_pts) > 1: draw.line(s_pts, fill=rgb_route + (st.session_state.r_alpha,), width=st.session_state.w_line, joint="round")

            final = Image.alpha_composite(canvas, overlay).convert('RGB')
            st.image(final, use_container_width=True)
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), f"tour_{datetime.now().strftime('%H%M')}.jpg", "image/jpeg")
    except Exception as e: st.error(f"Fehler: {e}")
