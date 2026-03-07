import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps
import io
import math
import os
from datetime import datetime

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro XXL", page_icon="🏍️", layout="centered")

# CSS Styling für modernere UI
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
    div[data-testid="stExpander"] details summary p {
        font-size: 1.2rem !important; font-weight: bold !important; color: #8b0000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- HILFSFUNKTIONEN ---
def safe_rect(draw, coords, fill=None, outline=None, width=1):
    """Sicherheitsfunktion: Sortiert x0,y0,x1,y1 um Abstürze zu vermeiden."""
    x0, y0, x1, y1 = coords
    draw.rectangle([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], fill=fill, outline=outline, width=width)

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

# Sidebar Logo
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

st.markdown("<p class='title-modern'>GPX Share Pro</p>", unsafe_allow_html=True)

if 'tour_name_val' not in st.session_state:
    st.session_state.tour_name_val = "Meine Tour"

# --- UPLOADS ---
c1, c2 = st.columns(2)
with c1:
    up_gpx = st.file_uploader("📍 1. GPX Datei (Tour)")
    if up_gpx is not None:
        raw_name = up_gpx.name.rsplit('.', 1)[0]
        st.session_state.tour_name_val = raw_name.replace('_', ' ').replace('-', ' ')
with c2:
    up_img = st.file_uploader("📸 2. Foto wählen (Optional)", type=["jpg", "jpeg", "png"])

# --- OPTIONEN ---
with st.expander("⚙️ Optionen", expanded=False):
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        tour_title = st.text_input("Tour Name", value=st.session_state.tour_name_val)
        map_style = st.selectbox("Karten-Stil", ["OSM Standard", "Dark Mode", "Satellit", "Light Mode"])
        show_logo = st.checkbox("Logo auf Bild", value=False)
        show_grid = st.checkbox("Raster im Höhenprofil", value=True)
        show_icons = st.checkbox("Icons in Infobox", value=True)
        show_units = st.checkbox("Einheiten anzeigen", value=True)
        fill_profile = st.checkbox("Füllung Höhenprofil", value=True)
    with col_opt2:
        font_scale = st.slider("Schrift-Skalierung", 0.5, 3.0, 1.5)
        b_height_adj = st.slider("Balken Dicke", 0.05, 0.40, 0.15)
        w_line = st.slider("Linienstärke Route", 1, 100, 9)
        b_alpha = st.slider("Balken Deckkraft", 0, 255, 160)
        r_alpha = st.slider("Routen-Transparenz", 0, 255, 255)
        bg_alpha = st.slider("Hintergrund Transparenz", 0, 255, 255)
        c_line = st.color_picker("Routenfarbe", "#8B0000")
        c_fill = st.color_picker("Farbe Profilfüllung", "#8B0000")

st.divider()

# --- VERARBEITUNG ---
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
            if up_img:
                src_img = ImageOps.exif_transpose(Image.open(up_img)).convert("RGB")
                w, h = src_img.size
            else:
                from staticmap import StaticMap, Line
                w, h = 1080, 1920 
                m = StaticMap(w, h, url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png")
                m.add_line(Line(list(zip(lons, lats)), c_line, w_line))
                src_img = m.render().convert("RGB")

            base_img = Image.new('RGB', (w, h), "white")
            src_img_rgba = src_img.convert("RGBA")
            alpha_band = src_img_rgba.split()[3].point(lambda p: int(p * bg_alpha / 255))
            src_img_rgba.putalpha(alpha_band)
            base_img.paste(src_img_rgba, (0, 0), src_img_rgba)

            overlay = Image.new('RGBA', base_img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            
            # Farben
            rgb_route = tuple(int(c_line[1:3], 16) if i==0 else int(c_line[3:5], 16) if i==1 else int(c_line[5:7], 16) for i in range(3))
            rgb_fill = tuple(int(c_fill[1:3], 16) if i==0 else int(c_fill[3:5], 16) if i==1 else int(c_fill[5:7], 16) for i in range(3))
            
            bh_top, bh_bot = int(h * b_height_adj), int(h * (b_height_adj + 0.02))
            safe_rect(draw, [0, 0, w, bh_top], fill=(0, 0, 0, b_alpha))
            safe_rect(draw, [0, h - bh_bot, w, h], fill=(0, 0, 0, b_alpha))

            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            
            # Höhenprofil
            if len(elevs) > 1:
                e_min, e_max = min(elevs), max(elevs)
                e_range = e_max - e_min if e_max > e_min else 1
                grid_y_start = h - bh_bot
                profile_pts = [((i/len(elevs))*w, (h-bh_bot)+(bh_bot*0.85)-((ev-e_min)/e_range)*(bh_bot*0.7)) for i, ev in enumerate(elevs)]
                
                if fill_profile:
                    draw.polygon(profile_pts + [(w, h), (0, h)], fill=rgb_fill + (int(r_alpha * 0.5),))
                draw.line(profile_pts, fill=(255,255,255, r_alpha), width=max(3, int(w*0.003)), joint="round")

            # Texte
            font_t = get_fitted_font(draw, tour_title, w * 0.9, int(w * 0.10 * font_scale), font_path)
            draw.text((w//2, bh_top//2), tour_title, fill="white", font=font_t, anchor="mm")

            txt_dist = f"{d_total:.1f}" + (" km" if show_units else "")
            txt_elev = f"{int(a_gain)}" + (" m" if show_units else "")
            font_d = get_fitted_font(draw, txt_dist + " " + txt_elev, w * 0.6, int(w * 0.07 * font_scale), font_path)
            draw.text((w//2, h - int(bh_bot * 0.5)), f"{txt_dist} | {txt_elev}", fill="white", font=font_d, anchor="mm")

            # Route auf Foto
            if up_img:
                mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
                margin = 0.20
                scaled = [(w*margin + (lon-mi_lo)/(ma_lo-mi_lo)*w*(1-2*margin), h*(1-margin) - (lat-mi_la)/(ma_la-mi_la)*h*(1-2*margin)) for lat, lon in pts]
                draw.line(scaled, fill=rgb_route + (r_alpha,), width=w_line, joint="round")

            final = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
            st.image(final, use_container_width=True)
            
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), f"tour_{datetime.now().strftime('%H%M')}.jpg", "image/jpeg")
    except Exception as e: st.error(f"Fehler: {e}")
