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
    "c_box": "#000000",import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageChops
import io
import math
import os

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro XXL", page_icon="🏍️", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #000000; }
    .title-modern {
        font-size: 36px; font-weight: 900;
        background: linear-gradient(90deg, #ff0000 0%, #8b0000 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 20px;
    }
    .stDownloadButton button {
        width: 100%; border-radius: 20px;
        background: linear-gradient(135deg, #ff0000 0%, #8b0000 100%) !important;
        color: white !important; font-weight: bold; border: none; height: 3em;
    }
    div[data-testid="stExpander"] details summary p {
        font-size: 1.2rem !important;
        font-weight: bold !important;
        color: #8b0000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# --- SEITENLEISTE (NUR LOGO) ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)

# --- HAUPTBEREICH ---
st.markdown("<p class='title-modern'>GPX Share Pro</p>", unsafe_allow_html=True)

if 'tour_name_val' not in st.session_state:
    st.session_state.tour_name_val = "Meine Tour"

# --- UPLOAD BEREICH ---
c1, c2 = st.columns(2)
with c1:
    up_gpx = st.file_uploader("📍 1. GPX Datei (Tour)")
    if up_gpx is not None:
        raw_name = up_gpx.name.rsplit('.', 1)[0]
        st.session_state.tour_name_val = raw_name.replace('_', ' ').replace('-', ' ')
with c2:
    up_img = st.file_uploader("📸 2. Foto wählen (Optional)", type=["jpg", "jpeg", "png"])

# --- OPTIONEN-BUTTON ---
with st.expander("⚙️ Optionen", expanded=False):
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        tour_title = st.text_input("Tour Name", value=st.session_state.tour_name_val)
        map_style = st.selectbox("Karten-Stil (wenn kein Foto)", ["OSM Standard", "Dark Mode", "Satellit", "Light Mode"])
        show_logo = st.checkbox("Zeige eigenes Logo auf Foto/Karte", value=False)
        show_grid = st.checkbox("Raster im Höhenprofil", value=True)
        show_icons = st.checkbox("Icons in Infobox", value=True)
        show_units = st.checkbox("Einheiten anzeigen (km/m)", value=True)
        logo_radius = st.slider("Logo-Ecken abrunden (Radius)", 0, 100, 20)
    with col_opt2:
        font_scale = st.slider("Schrift-Skalierung", 0.5, 3.0, 1.5)
        b_height_adj = st.slider("Balken Dicke", 0.05, 0.40, 0.15)
        w_line = st.slider("Linienstärke Route", 1, 100, 9)
        b_alpha = st.slider("Balken Deckkraft", 0, 255, 160)
        r_alpha = st.slider("Routen-Transparenz", 0, 255, 255)
        bg_alpha = st.slider("Hintergrund Transparenz", 0, 255, 255)
        c_line = st.color_picker("Routenfarbe", "#8B0000")

with st.expander("ℹ️ Über GPX Share", expanded=False):
    st.markdown("### Willkommen bei GPX Share Pro! 🏍️\nLade einfach eine `.gpx` Datei hoch.")

st.divider()

if up_gpx:
    try:
        up_gpx.seek(0)
        gpx = gpxpy.parse(up_gpx.read().decode("utf-8", errors="ignore"))
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
            draw_line_manually = False
            if up_img:
                src_img = Image.open(up_img).convert("RGB")
                w, h = src_img.size
                draw_line_manually = True
            else:
                from staticmap import StaticMap, Line, CircleMarker
                w, h = 1080, 1920 
                tile_urls = {
                    "OSM Standard": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                    "Satellit": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                    "Dark Mode": "https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png",
                    "Light Mode": "https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png"
                }
                m = StaticMap(w, h, url_template=tile_urls[map_style])
                m.add_line(Line(list(zip(lons, lats)), c_line, w_line))
                src_img = m.render().convert("RGB")

            # Hintergrund Transparenz
            base_img = Image.new('RGB', (w, h), "white")
            src_img_rgba = src_img.convert("RGBA")
            alpha_band = src_img_rgba.split()[3].point(lambda p: int(p * bg_alpha / 255))
            src_img_rgba.putalpha(alpha_band)
            base_img.paste(src_img_rgba, (0, 0), src_img_rgba)

            auto_f_title = int(w * 0.10 * font_scale)
            auto_f_data = int(w * 0.07 * font_scale) 
            overlay = Image.new('RGBA', base_img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            rgb = tuple(int(c_line[1:3], 16) if i==0 else int(c_line[3:5], 16) if i==1 else int(c_line[5:7], 16) for i in range(3))

            bh_top = int(h * b_height_adj)
            bh_bot = int(h * (b_height_adj + 0.02))
            draw.rectangle([0, 0, w, bh_top], fill=(0, 0, 0, b_alpha))
            draw.rectangle([0, h - bh_bot, w, h], fill=(0, 0, 0, b_alpha))

            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            try:
                font_t = ImageFont.truetype(font_path, auto_f_title)
                font_d = ImageFont.truetype(font_path, auto_f_data)
                font_grid = ImageFont.truetype(font_path, max(14, int(w * 0.025 * font_scale))) 
            except:
                font_t = font_d = font_grid = ImageFont.load_default()

            if len(elevs) > 1:
                e_min, e_max = min(elevs), max(elevs)
                e_range = e_max - e_min if e_max > e_min else 1
                grid_y_start = h - bh_bot
                if show_grid:
                    grid_color, grid_text_color = (255, 255, 255, 45), (255, 255, 255, 160) 
                    for i in range(1, 4):
                        gy = grid_y_start + i * (bh_bot / 4)
                        draw.line([(0, gy), (w, gy)], fill=grid_color, width=max(1, int(w*0.001)))
                        ev_val = e_min + ((grid_y_start + bh_bot*0.85 - gy) / (bh_bot*0.7)) * e_range
                        draw.text((w * 0.01, gy - 2), f"{int(ev_val)}m", fill=grid_text_color, font=font_grid, anchor="ld")
                    for i in range(1, 8):
                        gx = i * (w / 8)
                        draw.line([(gx, grid_y_start), (gx, h)], fill=grid_color, width=max(1, int(w*0.001)))
                        draw.text((gx + 4, grid_y_start + 4), f"{int((i/8)*d_total)}km", fill=grid_text_color, font=font_grid, anchor="lt")

                profile_pts = [((i/len(elevs))*w, (h-bh_bot)+(bh_bot*0.85)-((ev-e_min)/e_range)*(bh_bot*0.7)) for i, ev in enumerate(elevs)]
                draw.polygon(profile_pts + [(w, h), (0, h)], fill=rgb + (int(r_alpha * 0.5),))
                draw.line(profile_pts, fill=(255,255,255, r_alpha), width=max(3, int(w*0.003)), joint="round")

            draw.text((w//2, bh_top//2), tour_title, fill="white", font=font_t, anchor="mm")
            
            # --- TACHO ICON GENERIEREN ---
            icon_size = int(w * 0.07 * 1.3 * font_scale)
            lw = max(3, int(icon_size * 0.08))
            img_dist = Image.new('RGBA', (icon_size, icon_size), (0,0,0,0))
            d_dist = ImageDraw.Draw(img_dist)
            d_dist.arc([lw, lw, icon_size-lw, icon_size-lw], start=150, end=390, fill="white", width=lw)
            center = icon_size // 2
            zeiger_len = icon_size * 0.35
            angle = math.radians(240)
            d_dist.line([(center, center), (center + math.cos(angle)*zeiger_len, center + math.sin(angle)*zeiger_len)], fill="white", width=lw)
            d_dist.ellipse([center-lw, center-lw, center+lw, center+lw], fill="white")
            
            img_elev = Image.new('RGBA', (icon_size, icon_size), (0,0,0,0))
            d_elev = ImageDraw.Draw(img_elev)
            d_elev.polygon([(0, icon_size*0.9), (icon_size*0.4, icon_size*0.2), (icon_size*0.8, icon_size*0.9)], fill="white")
            d_elev.line([(icon_size*0.9, icon_size*0.8), (icon_size*0.9, icon_size*0.1)], fill="white", width=lw)
            d_elev.polygon([(icon_size*0.9, 0), (icon_size*0.8, icon_size*0.2), (icon_size, icon_size*0.2)], fill="white")

            # --- TEXTE & ZENTRIERUNG ---
            txt_dist = f"{d_total:.1f}" + (" km" if show_units else "")
            txt_elev = f"{int(a_gain)}" + (" m" if show_units else "")
            w_dist = draw.textlength(txt_dist, font=font_d)
            w_elev = draw.textlength(txt_elev, font=font_d)
            spacing, icon_gap = int(w * 0.15), int(w * 0.02) if show_icons else 0
            curr_icon_w = icon_size if show_icons else 0
            total_w = (curr_icon_w + icon_gap + w_dist) + spacing + (curr_icon_w + icon_gap + w_elev)
            start_x, y_pos = (w - total_w) // 2, h - int(bh_bot * 0.35) 
            
            if show_icons: overlay.paste(img_dist, (int(start_x), int(y_pos - icon_size // 2)), img_dist)
            draw.text((start_x + curr_icon_w + icon_gap, y_pos), txt_dist, fill="white", font=font_d, anchor="lm")
            x_elev = start_x + curr_icon_w + icon_gap + w_dist + spacing
            if show_icons: overlay.paste(img_elev, (int(x_elev), int(y_pos - icon_size // 2)), img_elev)
            draw.text((x_elev + curr_icon_w + icon_gap, y_pos), txt_elev, fill="white", font=font_d, anchor="lm")
            
            if draw_line_manually:
                mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
                margin = 0.20
                scaled_pts = [(w*margin + (lon-mi_lo)/(ma_lo-mi_lo)*w*(1-2*margin), h*(1-margin) - (lat-mi_la)/(ma_la-mi_la)*h*(1-2*margin)) for lat, lon in pts]
                draw.line(scaled_pts, fill=rgb + (r_alpha,), width=w_line, joint="round")
                if len(scaled_pts) > 1:
                    p_s = max(6, int(w * 0.008)) 
                    draw.ellipse([scaled_pts[0][0]-p_s, scaled_pts[0][1]-p_s, scaled_pts[0][0]+p_s, scaled_pts[0][1]+p_s], fill=(255,255,255, r_alpha))
                    draw.ellipse([scaled_pts[-1][0]-p_s, scaled_pts[-1][1]-p_s, scaled_pts[-1][0]+p_s, scaled_pts[-1][1]+p_s], fill=rgb + (r_alpha,))

            final = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
            st.image(final, use_container_width=True)
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), "ride_pro_final.jpg", "image/jpeg")
    except Exception as e:
        st.error(f"Fehler: {e}")
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
