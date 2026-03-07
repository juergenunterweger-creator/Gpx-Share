import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps
import io
import math
import os
from datetime import datetime

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro XXL", page_icon="🏍️", layout="centered")

# --- STANDARDWERTE (Basis v1.7) ---
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

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

if "persistent_img" not in st.session_state: st.session_state.persistent_img = None
if "persistent_gpx" not in st.session_state: st.session_state.persistent_gpx = None

def reset_parameters():
    for key, val in DEFAULTS.items():
        st.session_state[key] = val

def safe_rect(draw, coords, fill=None, outline=None, width=1):
    """Sicherheitsfunktion gegen Geometrie-Fehler"""
    x0, y0, x1, y1 = coords
    draw.rectangle([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], 
                   fill=fill, outline=outline, width=width)

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
    return img.resize((size, size), Image.Resampling.LANCZOS)

st.markdown("<p class='title-modern'>GPX Share Pro</p>", unsafe_allow_html=True)

# --- UPLOADS ---
c_up1, c_up2 = st.columns(2)
with c_up1:
    up_gpx = st.file_uploader("📍 1. GPX Datei wählen")
    if up_gpx:
        new_gpx = up_gpx.read()
        if st.session_state.persistent_gpx != new_gpx:
            st.session_state.persistent_gpx = new_gpx
            st.session_state.selected_track_idx = 0
            st.session_state.tour_title = up_gpx.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
            st.rerun()

with c_up2:
    up_img = st.file_uploader("📸 2. Foto wählen", type=["jpg", "jpeg", "png"])
    if up_img: st.session_state.persistent_img = up_img.read()

# --- OPTIONEN ---
with st.expander("⚙️ Optionen", expanded=False):
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        new_title = st.text_input("Name", value=st.session_state.tour_title)
        if st.button("✅ Name übernehmen"):
            st.session_state.tour_title = new_title
            st.rerun()
        
        if st.session_state.persistent_gpx:
            try:
                temp_gpx = gpxpy.parse(io.BytesIO(st.session_state.persistent_gpx))
                if len(temp_gpx.tracks) > 1:
                    track_names = [f"{t.name if t.name else 'Spur ' + str(i+1)}" for i, t in enumerate(temp_gpx.tracks)]
                    st.selectbox("📍 Spur wählen", range(len(track_names)), format_func=lambda x: track_names[x], key="selected_track_idx")
            except: pass
        
        st.checkbox("Höhenprofil anzeigen", key="show_profile")
        st.checkbox("Raster im Profil", key="show_grid")
        st.checkbox("Icons anzeigen", key="show_icons")
        st.checkbox("Einheiten anzeigen", key="show_units")
    with col_opt2:
        st.slider("Titel-Größe", 0.5, 3.0, key="font_scale")
        st.slider("Daten-Abstand", 50, 400, key="data_y_offset")
        st.checkbox("Route Auto-Skalieren", key="route_autoscale")
        st.color_picker("Routenfarbe", key="c_line")
        st.color_picker("Infobox-Farbe", key="c_box")
    st.button("🔄 Einstellungen zurücksetzen", on_click=reset_parameters)

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
            if st.session_state.persistent_img:
                bg_img = ImageOps.exif_transpose(Image.open(io.BytesIO(st.session_state.persistent_img))).convert("RGBA")
                bg_img = ImageOps.fit(bg_img, (w, h), Image.Resampling.LANCZOS)
                canvas.paste(bg_img, (0, 0))
            else:
                from staticmap import StaticMap, Line
                m = StaticMap(w, h, url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png")
                m.add_line(Line(list(zip(lons, lats)), st.session_state.c_line, 0))
                canvas.paste(m.render().convert("RGBA"), (0, 0))

            overlay = Image.new('RGBA', (w, h), (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            rgb_box = tuple(int(st.session_state.c_box[i*2+1:i*2+3], 16) for i in range(3))
            bh_top, bh_bot = int(h * st.session_state.b_height_adj), int(h * 0.12)
            
            safe_rect(draw, [0, 0, w, bh_top], fill=rgb_box + (st.session_state.b_alpha,))
            safe_rect(draw, [0, h - bh_bot, w, h], fill=rgb_box + (st.session_state.b_alpha,))

            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            
            # Profil & Raster
            if st.session_state.show_profile and len(elevs) > 1:
                e_min, e_max = min(elevs), max(elevs)
                e_range = (e_max - e_min) if e_max > e_min else 1
                grid_y_start = h - bh_bot
                profile_pts = [((i/len(elevs))*w, (h-bh_bot)+(bh_bot*0.85)-((ev-e_min)/e_range)*(bh_bot*0.7)) for i, ev in enumerate(elevs)]
                if st.session_state.show_grid:
                    f_grid = get_fitted_font(draw, "000m", int(w*0.02), int(w*0.02), font_path)
                    for i in range(1, 4):
                        gy = grid_y_start + i * (bh_bot / 4)
                        draw.line([(0, gy), (w, gy)], fill=(255,255,255,45), width=1)
                    for i in range(1, 8):
                        gx = i * (w / 8)
                        draw.line([(gx, grid_y_start), (gx, h)], fill=(255,255,255,45), width=1)
                
                rgb_fill = tuple(int(st.session_state.c_fill[i*2+1:i*2+3], 16) for i in range(3))
                if st.session_state.fill_profile:
                    draw.polygon(profile_pts + [(w, h), (0, h)], fill=rgb_fill + (int(st.session_state.r_alpha * 0.5),))
                draw.line(profile_pts, fill=(255,255,255, st.session_state.r_alpha), width=max(3, int(w*0.003)), joint="round")

            # Titel & Daten
            t_y = int(bh_top * 0.35)
            draw.text((w//2, t_y), st.session_state.tour_title, fill="white", font=get_fitted_font(draw, st.session_state.tour_title, w*0.9, int(w*0.085*st.session_state.font_scale), font_path), anchor="mm")
            
            txt_d = f"{d_total:.1f}" + (" km" if st.session_state.show_units else "")
            txt_e = f"{int(a_gain)}" + (" m" if st.session_state.show_units else "")
            f_d = get_fitted_font(draw, txt_d + " " + txt_e, w*0.7, int(w*0.055*st.session_state.data_font_scale), font_path)
            
            draw.text((w//2, t_y + st.session_state.data_y_offset), f"{txt_d} | {txt_e}", fill="white", font=f_d, anchor="mm")

            # Route (Segment-Treu)
            margin = 0.20 if st.session_state.route_autoscale else 0.5 * (1.0 - (0.6 * st.session_state.route_scale))
            rgb_route = tuple(int(st.session_state.c_line[i*2+1:i*2+3], 16) for i in range(3))
            for seg in segments_pts:
                s_pts = [((w*margin + (lon-mi_lo)/(ma_lo-mi_lo)*w*(1-2*margin)) + st.session_state.route_x_offset, (h*(1-margin) - (lat-mi_la)/(ma_la-mi_la)*h*(1-2*margin)) + st.session_state.route_y_offset) for lat, lon in seg]
                if len(s_pts) > 1: draw.line(s_pts, fill=rgb_route + (st.session_state.r_alpha,), width=st.session_state.w_line, joint="round")

            final = Image.alpha_composite(canvas, overlay).convert('RGB')
            st.image(final, use_container_width=True)
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), f"tour_basis_{datetime.now().strftime('%H%M')}.jpg", "image/jpeg")

    except Exception as e: st.error(f"Fehler: {e}")
