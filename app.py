import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageChops
import io
import math
import os

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

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

if "persistent_img" not in st.session_state:
    st.session_state.persistent_img = None
if "persistent_gpx" not in st.session_state:
    st.session_state.persistent_gpx = None

def reset_parameters():
    for key, val in DEFAULTS.items():
        st.session_state[key] = val

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
        d.polygon([(size*res*0.4, size*res-lw), (size*res*0.75, size*res*0.4), (size*res-lw, size*res-lw)], fill=color, outline="black")
    return img.resize((size, size), Image.Resampling.LANCZOS)

st.markdown("<p class='title-modern'>GPX Share Pro</p>", unsafe_allow_html=True)

# --- UPLOADS ---
c_up1, c_up2 = st.columns(2)
with c_up1:
    up_gpx = st.file_uploader("📍 1. GPX Datei wählen")
    if up_gpx:
        # Falls eine neue Datei kommt: Spur-Index zurücksetzen
        new_gpx_data = up_gpx.read()
        if st.session_state.persistent_gpx != new_gpx_data:
            st.session_state.selected_track_idx = 0
            st.session_state.persistent_gpx = new_gpx_data
            st.session_state.tour_title = up_gpx.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
with c_up2:
    up_img = st.file_uploader("📸 2. Foto wählen", type=["jpg", "jpeg", "png"])
    if up_img: st.session_state.persistent_img = up_img.read()

# --- OPTIONEN ---
with st.expander("⚙️ Optionen", expanded=False):
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        new_title = st.text_input("Tour Name eingeben", value=st.session_state.tour_title)
        if st.button("✅ Name übernehmen"):
            st.session_state.tour_title = new_title
            st.rerun()
            
        st.selectbox("Karten-Stil", ["OSM Standard", "Dark Mode", "Satellit", "Light Mode"], key="map_style")
        
        if st.session_state.persistent_gpx:
            try:
                temp_gpx = gpxpy.parse(io.BytesIO(st.session_state.persistent_gpx))
                if len(temp_gpx.tracks) > 1:
                    track_names = [f"{t.name if t.name else 'Spur ' + str(i+1)}" for i, t in enumerate(temp_gpx.tracks)]
                    st.selectbox("📍 Gewünschte Spur wählen", range(len(track_names)), 
                                 format_func=lambda x: track_names[x], key="selected_track_idx")
            except: pass
        
        st.checkbox("Zeige eigenes Logo", key="show_logo")
        st.checkbox("Höhenprofil anzeigen", key="show_profile")
        st.checkbox("Raster im Höhenprofil", key="show_grid")
        st.checkbox("Icons in Infobox", key="show_icons")
        st.checkbox("Einheiten anzeigen", key="show_units")
        st.checkbox("Füllung Höhenprofil", key="fill_profile")
    with col_opt2:
        st.slider("Titel-Skalierung", 0.5, 3.0, key="font_scale")
        st.slider("Daten-Skalierung", 0.5, 3.0, key="data_font_scale")
        st.slider("Vertikaler Abstand Daten", 0, 300, key="data_y_offset")
        st.write("**Position Route:**")
        st.checkbox("Route automatisch skalieren", key="route_autoscale")
        st.slider("Horizontaler Versatz Route", -500, 500, key="route_x_offset")
        st.slider("Vertikaler Versatz Route", -500, 500, key="route_y_offset")
        st.slider("Manuelle Route Skalierung", 0.1, 2.0, key="route_scale", disabled=st.session_state.route_autoscale)
        if st.session_state.persistent_img:
            st.write("**Foto Einstellungen:**")
            st.slider("Horizontaler Versatz Foto", -2000, 2000, key="img_x_offset")
            st.slider("Vertikaler Versatz Foto", -2000, 2000, key="img_y_offset")
            st.slider("Foto Zoom", 0.1, 5.0, key="img_zoom")
        st.slider("Balken Dicke", 0.05, 0.50, key="b_height_adj")
        st.slider("Linienstärke Route", 1, 100, key="w_line")
        st.slider("Balken Deckkraft", 0, 255, key="b_alpha")
        st.color_picker("Routenfarbe", key="c_line")
        st.color_picker("Farbe Profilfüllung", key="c_fill")
        st.color_picker("Farbe Infoboxen", key="c_box")
    st.button("🔄 Einstellungen zurücksetzen", on_click=reset_parameters)

# --- ÜBER REITER ---
with st.expander("ℹ️ Über GPX Share Pro", expanded=False):
    st.markdown("### GPX Share Pro XXL")
    st.markdown("**Copyright: Jürgen Unterweger** | **Version: 1.5**")
    paypal_url = "https://www.paypal.com/donate?hosted_button_id=FF6FBUE84V7MG"
    st.markdown(f'<a href="{paypal_url}" target="_blank"><img src="https://www.paypalobjects.com/de_DE/i/btn/btn_donateCC_LG.gif" width="120"></a>', unsafe_allow_html=True)
    st.markdown("---")
    col_ig, col_fb = st.columns(2)
    with col_ig: st.markdown(f"📸 [Instagram](https://www.instagram.com/juergen_rocks/)")
    with col_fb: st.markdown(f"👥 [Facebook](https://www.facebook.com/JuergenRocks/)")
    st.code("https://gpx-share-oh4dfakuqvfxadxmg3qhhq.streamlit.app/", language=None)

st.divider()

# --- VERARBEITUNG ---
if st.session_state.persistent_gpx:
    try:
        gpx = gpxpy.parse(io.BytesIO(st.session_state.persistent_gpx))
        segments_pts = [] # Liste von Listen für echte Segmente
        elevs = []
        d_total, a_gain = 0.0, 0.0
        last, last_elev = None, None
        
        if len(gpx.tracks) > 0:
            target_track = gpx.tracks[min(st.session_state.selected_track_idx, len(gpx.tracks)-1)]
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
                if current_seg:
                    segments_pts.append(current_seg)

        if segments_pts:
            # Alle Punkte sammeln für Bounding-Box Berechnung
            all_pts = [pt for seg in segments_pts for pt in seg]
            lats, lons = zip(*all_pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            
            if st.session_state.persistent_img:
                src_img = Image.open(io.BytesIO(st.session_state.persistent_img)).convert("RGBA")
                w_orig, h_orig = src_img.size
                src_img = src_img.resize((int(w_orig * st.session_state.img_zoom), int(h_orig * st.session_state.img_zoom)), Image.Resampling.LANCZOS)
                w, h = w_orig, h_orig
            else:
                from staticmap import StaticMap, Line
                w, h = 1080, 1920
                m = StaticMap(w, h, url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png")
                # Für die Karte nutzen wir alle Punkte als eine Linie
                m.add_line(Line(list(zip(lons, lats)), st.session_state.c_line, st.session_state.w_line))
                src_img = m.render().convert("RGBA")

            base_img = Image.new('RGBA', (w, h), (255, 255, 255, 255))
            base_img.paste(src_img, (st.session_state.img_x_offset if st.session_state.persistent_img else 0, st.session_state.img_y_offset if st.session_state.persistent_img else 0), src_img)

            overlay = Image.new('RGBA', base_img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            rgb_box = tuple(int(st.session_state.c_box[i*2+1:i*2+3], 16) for i in range(3))
            bh_top, bh_bot = int(h * st.session_state.b_height_adj), int(h * 0.12)
            draw.rectangle([0, 0, w, bh_top], fill=rgb_box + (st.session_state.b_alpha,))
            draw.rectangle([0, h - bh_bot, w, h], fill=rgb_box + (st.session_state.b_alpha,))

            font_path = "font.ttf" if os.path.exists("font.ttf") else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            
            # --- HÖHENPROFIL ---
            if st.session_state.show_profile and len(elevs) > 1:
                e_min, e_max = min(elevs), max(elevs)
                e_range = (e_max - e_min) if e_max > e_min else 1
                grid_y_start = h - bh_bot
                profile_pts = [((i/len(elevs))*w, (h-bh_bot)+(bh_bot*0.85)-((ev-e_min)/e_range)*(bh_bot*0.7)) for i, ev in enumerate(elevs)]
                rgb_fill = tuple(int(st.session_state.c_fill[i*2+1:i*2+3], 16) for i in range(3))
                if st.session_state.fill_profile:
                    draw.polygon(profile_pts + [(w, h), (0, h)], fill=rgb_fill + (int(st.session_state.r_alpha * 0.5),))
                if st.session_state.show_grid:
                    font_grid = get_fitted_font(draw, "0m", int(w*0.02), int(w*0.02), font_path)
                    for i in range(1, 4):
                        gy = grid_y_start + i * (bh_bot / 4)
                        draw.line([(0, gy), (w, gy)], fill=(255,255,255,45), width=max(1, int(w*0.001)))
                        draw.text((w*0.005, gy-2), f"{int(e_min + ((grid_y_start+bh_bot*0.85-gy)/(bh_bot*0.7))*e_range)}m", fill=(255,255,255,140), font=font_grid, anchor="ld")
                    for i in range(1, 8):
                        gx = i * (w / 8)
                        draw.line([(gx, grid_y_start), (gx, h)], fill=(255,255,255,45), width=max(1, int(w*0.001)))
                        draw.text((gx + 4, grid_y_start + 4), f"{int((i/8)*d_total)}km", fill=(255,255,255,140), font=font_grid, anchor="lt")
                draw.line(profile_pts, fill=(255,255,255, st.session_state.r_alpha), width=max(3, int(w*0.003)), joint="round")

            # --- ROUTE (SEGMENT FÜR SEGMENT) ---
            base_margin = 0.20 if st.session_state.route_autoscale else 0.5 * (1.0 - (0.6 * st.session_state.route_scale))
            rgb_route = tuple(int(st.session_state.c_line[i*2+1:i*2+3], 16) for i in range(3))
            
            for seg in segments_pts:
                scaled_seg = [((w*base_margin + (lon-mi_lo)/(ma_lo-mi_lo)*w*(1-2*base_margin)) + st.session_state.route_x_offset, 
                               (h*(1-base_margin) - (lat-mi_la)/(ma_la-mi_la)*h*(1-2*base_margin)) + st.session_state.route_y_offset) for lat, lon in seg]
                if len(scaled_seg) > 1:
                    draw.line(scaled_seg, fill=rgb_route + (st.session_state.r_alpha,), width=st.session_state.w_line, joint="round")

            font_t = get_fitted_font(draw, st.session_state.tour_title, w * 0.9, int(w * 0.085 * st.session_state.font_scale), font_path)
            draw.text((w//2, int(bh_top * 0.35)), st.session_state.tour_title, fill="white", font=font_t, anchor="mm")
            txt_dist, txt_elev = f"{d_total:.1f}" + (" km" if st.session_state.show_units else ""), f"{int(a_gain)}" + (" m" if st.session_state.show_units else "")
            icon_size = int(w * 0.055 * 1.3 * st.session_state.data_font_scale)
            font_d = get_fitted_font(draw, txt_dist + " " + txt_elev, w * 0.7, int(w * 0.055 * st.session_state.data_font_scale), font_path)
            w_d, w_e, i_gap = draw.textlength(txt_dist, font=font_d), draw.textlength(txt_elev, font=font_d), int(w * 0.02)
            total_w = (icon_size if st.session_state.show_icons else 0)*2 + i_gap*2 + w_d + w_e + int(w * 0.15)
            sx, data_y = (w - total_w) // 2, int(bh_top * 0.35) + st.session_state.data_y_offset
            if st.session_state.show_icons:
                ic_dist = draw_smooth_icon("dist", icon_size)
                overlay.paste(ic_dist, (int(sx), int(data_y - icon_size//2)), ic_dist)
                draw.text((sx + icon_size + i_gap, data_y), txt_dist, fill="white", font=font_d, anchor="lm")
                ex = sx + icon_size + i_gap + w_d + int(w * 0.15)
                ic_elev = draw_smooth_icon("elev", icon_size)
                overlay.paste(ic_elev, (int(ex), int(data_y - icon_size//2)), ic_elev)
                draw.text((ex + icon_size + i_gap, data_y), txt_elev, fill="white", font=font_d, anchor="lm")

            final = Image.alpha_composite(base_img, overlay).convert('RGB')
            st.image(final, use_container_width=True)
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), "ride_pro_final.jpg", "image/jpeg")
    except Exception as e: st.error(f"Fehler: {e}")
