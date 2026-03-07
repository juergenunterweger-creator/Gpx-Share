import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont
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
    "font_scale": 1.5,
    "data_font_scale": 1.2,
    "grid_font_scale": 1.5,
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
    "fill_profile": True
}

# Initialisierung Session State
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
    st.rerun()

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
    .install-box {
        background-color: #f0f2f6; padding: 15px; border-radius: 10px;
        border-left: 5px solid #ff0000; margin-top: 10px; margin-bottom: 10px;
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
    up_img = st.file_uploader("📸 2. Foto wählen", type=["jpg", "jpeg", "png"])
    if up_img: st.session_state.persistent_img = up_img.read()

# --- OPTIONEN (RESTAURIERT & ERWEITERT) ---
with st.expander("⚙️ Optionen & Skalierung", expanded=False):
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        st.write("**📝 Texte & Info**")
        new_title = st.text_input("Tour Name", value=st.session_state.tour_title)
        new_date = st.text_input("Datum", value=st.session_state.tour_date)
        if st.button("✅ Daten übernehmen"):
            st.session_state.tour_title = new_title
            st.session_state.tour_date = new_date
            st.rerun()
        st.checkbox("Datum anzeigen", key="show_date")
        st.checkbox("Höhenprofil anzeigen", key="show_profile")
        st.checkbox("Raster anzeigen", key="show_grid")
        st.slider("Titel-Größe", 0.5, 3.0, key="font_scale")
        st.slider("Daten-Größe", 0.5, 3.0, key="data_font_scale")
        st.slider("Daten-Abstand Y", 0, 400, key="data_y_offset")

    with col_opt2:
        st.write("**📐 Route & Bild**")
        st.checkbox("Route Auto-Skalierung", key="route_autoscale")
        if not st.session_state.route_autoscale:
            st.slider("Manuelle Route-Größe", 0.1, 2.0, key="route_scale")
        st.slider("Route Horizontal (X)", -600, 600, key="route_x_offset")
        st.slider("Route Vertikal (Y)", -600, 600, key="route_y_offset")
        
        if st.session_state.persistent_img:
            st.write("---")
            st.slider("Bild-Zoom", 0.1, 5.0, key="img_zoom")
            st.slider("Bild Horizontal (X)", -2000, 2000, key="img_x_offset")
            st.slider("Bild Vertikal (Y)", -2000, 2000, key="img_y_offset")
        
        st.write("---")
        st.color_picker("Routenfarbe", key="c_line")
        st.color_picker("Balken-Farbe", key="c_box")
    
    st.divider()
    st.button("🔄 Einstellungen zurücksetzen", on_click=reset_parameters)

# --- ÜBER REITER ---
with st.expander("ℹ️ Über GPX Share Pro", expanded=False):
    st.markdown("### GPX Share Pro XXL")
    st.markdown("**Copyright: Jürgen Unterweger** | **Version: 1.2.10**")
    paypal_url = "https://www.paypal.com/donate?hosted_button_id=FF6FBUE84V7MG"
    st.markdown(f'<a href="{paypal_url}" target="_blank"><img src="https://www.paypalobjects.com/de_DE/i/btn/btn_donateCC_LG.gif" width="120"></a>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**📲 Als App installieren:**")
    st.markdown('<div class="install-box"><strong>iPhone (Safari):</strong> Teilen -> "Zum Home-Bildschirm"</div>', unsafe_allow_html=True)
    col_ig, col_fb = st.columns(2)
    with col_ig: st.markdown("📸 [Instagram](https://www.instagram.com/juergen_rocks/)")
    with col_fb: st.markdown("👥 [Facebook](https://www.facebook.com/JuergenRocks/)")

st.divider()

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
            
            # BILD-VERARBEITUNG
            if st.session_state.persistent_img:
                src_img = Image.open(io.BytesIO(st.session_state.persistent_img)).convert("RGBA")
                w_orig, h_orig = src_img.size
                # Zoom anwenden
                new_w, new_h = int(w_orig * st.session_state.img_zoom), int(h_orig * st.session_state.img_zoom)
                src_img = src_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                w, h = w_orig, h_orig # Basis-Leinwand bleibt Originalgröße
            else:
                w, h = 1080, 1920
                src_img = Image.new('RGBA', (w, h), (200, 200, 200, 255))

            base_img = Image.new('RGBA', (w, h), (255, 255, 255, 255))
            base_img.paste(src_img, (st.session_state.img_x_offset, st.session_state.img_y_offset), src_img)

            overlay = Image.new('RGBA', base_img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            rgb_box = tuple(int(st.session_state.c_box[i*2+1:i*2+3], 16) for i in range(3))
            bh_top, bh_bot = int(h * st.session_state.b_height_adj), int(h * 0.12)
            draw.rectangle([0, 0, w, bh_top], fill=rgb_box + (st.session_state.b_alpha,))
            draw.rectangle([0, h - bh_bot, w, h], fill=rgb_box + (st.session_state.b_alpha,))

            font_path = "font.ttf" if os.path.exists("font.ttf") else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            
            # TITEL
            font_t = get_fitted_font(draw, st.session_state.tour_title, w * 0.9, int(w * 0.085 * st.session_state.font_scale), font_path)
            draw.text((w//2, int(bh_top * 0.35)), st.session_state.tour_title, fill="white", font=font_t, anchor="mm")
            
            # DATUM BOX
            if st.session_state.show_date and st.session_state.tour_date:
                date_font_size = int(w * 0.028 * st.session_state.font_scale)
                try: font_date = ImageFont.truetype(font_path, date_font_size)
                except: font_date = ImageFont.load_default()
                date_text = st.session_state.tour_date
                tw = draw.textlength(date_text, font=font_date)
                pad, margin = int(w * 0.015), int(w * 0.02)
                bx1, by1 = w - tw - pad*2 - margin, h - bh_bot - margin - date_font_size - pad*2
                bx2, by2 = w - margin, h - bh_bot - margin 
                draw.rectangle([bx1, by1, bx2, by2], fill=rgb_box + (st.session_state.b_alpha,), outline="white", width=1)
                draw.text((bx1 + pad, by1 + pad), date_text, fill="white", font=font_date)
            
            # ROUTE ZEICHNEN
            r_scale = 0.20 if st.session_state.route_autoscale else 0.5 * (1.0 - (0.4 * st.session_state.route_scale))
            rgb_route = tuple(int(st.session_state.c_line[i*2+1:i*2+3], 16) for i in range(3))
            scaled = [((w*r_scale + (lon-mi_lo)/(ma_lo-mi_lo)*w*(1-2*r_scale)) + st.session_state.route_x_offset, 
                       (h*(1-r_scale) - (lat-mi_la)/(ma_la-mi_la)*h*(1-2*r_scale)) + st.session_state.route_y_offset) for lat, lon in pts]
            draw.line(scaled, fill=rgb_route + (st.session_state.r_alpha,), width=st.session_state.w_line, joint="round")

            # INFO TEXT
            txt_data = f"{d_total:.1f} km   |   {int(a_gain)} m"
            font_d = get_fitted_font(draw, txt_data, w * 0.7, int(w * 0.055 * st.session_state.data_font_scale), font_path)
            draw.text((w//2, int(bh_top * 0.35) + st.session_state.data_y_offset), txt_data, fill="white", font=font_d, anchor="mm")

            final = Image.alpha_composite(base_img, overlay).convert('RGB')
            st.image(final, use_container_width=True)
            
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), f"tour_skaliert_{datetime.now().strftime('%H%M%S')}.jpg", "image/jpeg")
    except Exception as e: st.error(f"Fehler: {e}")
