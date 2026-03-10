import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import math
import os
import base64

# --- APP KONFIGURATION ---
def get_fav_icon():
    if os.path.exists("logo_icon.png"):
        return "logo_icon.png"
    return "🏍️"

st.set_page_config(
    page_title="GPX Share Pro XXL", 
    page_icon=get_fav_icon(), 
    layout="centered"
)

# --- AGGRESSIVER BRANDING KILLER & HEADER-STYLING ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    #stDecoration {display:none !important;}
    [data-testid="stHeader"] {display: none !important;}
    .stDeployButton {display:none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    div.stActionButton {display:none !important;}
    .main .block-container {padding-top: 0.5rem !important;}
    
    .header-container {
        display: flex; 
        align-items: center; 
        justify-content: center;
        background: linear-gradient(135deg, #111111 0%, #2a2a2a 100%);
        padding: 10px 15px; 
        border-radius: 12px; 
        border-bottom: 3px solid #da2323;
        margin-bottom: 15px;
    }
    .header-text {
        font-size: 26px; 
        font-weight: 900;
        color: #ff4b4b;
        margin: 0; 
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .header-logo {
        height: 35px;
        margin-right: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOGO & HEADER LOGIK ---
def get_logo_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

logo_b64 = get_logo_base64("logo.png")
if logo_b64:
    header_html = f"""
    <div class="header-container">
        <img src="data:image/png;base64,{logo_b64}" class="header-logo">
        <p class="header-text">GPX Share Pro</p>
    </div>
    """
else:
    header_html = '<div class="header-container"><p class="header-text">GPX Share Pro XXL</p></div>'

st.markdown(header_html, unsafe_allow_html=True)

# --- STANDARDWERTE (v4.3.0) ---
DEFAULTS = {
    "tour_title": "Meine Tour", "tour_date": "", "c_line": "#DA2323", "c_title": "#DA2323",
    "c_date": "#FFFFFF", "c_data": "#FFFFFF", "c_grid": "#FFFFFF", "w_line": 9,
    "show_markers": True, "show_speed": True, "show_profile": True, "show_logo": False,
    "show_route": False, "show_minibox": True, "logo_type": "Grafisches logo",
    "show_date": True, "auto_intervals": True, "grid_m_interval": 250, "grid_km_interval": 10,
    "bg_opacity": 100, "size_title": 1.5, "size_date": 1.0, "size_data": 1.0,
    "size_grid": 1.0, "size_logo": 1.0, "size_minibox": 1.0,
    "story_margins_active": True, "margin_top": 150, "margin_bottom": 100
}

for key, val in DEFAULTS.items():
    if key not in st.session_state: st.session_state[key] = val

if "last_gpx_file" not in st.session_state: st.session_state.last_gpx_file = ""

# --- HELFER FUNKTIONEN ---
def reset_parameters():
    for key, val in DEFAULTS.items(): st.session_state[key] = val

def load_font(size):
    size = max(10, int(size))
    paths = ["font.ttf", "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for p in paths:
        try: return ImageFont.truetype(p, size)
        except: continue
    return ImageFont.load_default()

def validate_coords(coords):
    return [min(coords[0], coords[2]), min(coords[1], coords[3]), max(coords[0], coords[2]) + 1, max(coords[1], coords[3]) + 1]

def safe_rect(draw, coords, fill=None, outline=None, width=1):
    try: draw.rectangle(validate_coords(coords), fill=fill, outline=outline, width=int(width))
    except: pass

def safe_ellipse(draw, coords, fill=None, outline=None, width=1):
    try: draw.ellipse(validate_coords(coords), fill=fill, outline=outline, width=int(width))
    except: pass

def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def draw_text_with_shadow(draw, pos, text, font, fill="white", shadow_color="black", offset=2, anchor="mm"):
    x, y = int(pos[0]), int(pos[1])
    draw.text((x+offset, y+offset), text, fill=shadow_color, font=font, anchor=anchor)
    draw.text((x, y), text, fill=fill, font=font, anchor=anchor)

def draw_marker(draw, pos, color, label=""):
    x, y = pos; r = 14
    safe_ellipse(draw, [x-r-2, y-r-2, x+r+2, y+r+2], fill="white")
    safe_ellipse(draw, [x-r, y-r, x+r, y+r], fill=color, outline="black", width=2)
    if label:
        f = load_font(16)
        draw.text((int(x), int(y)), label, fill="white", font=f, anchor="mm")

def draw_data_icon(mode, size, color="white"):
    res = 4; size = int(max(10, size))
    img = Image.new('RGBA', (size*res, size*res), (0,0,0,0)); d = ImageDraw.Draw(img)
    lw = int(max(2, size*res*0.08)); x0, y0, x1, y1 = lw, lw, size*res - lw, size*res - lw
    if mode == "dist":
        d.line([(x0, y1-lw), (x1//2, y1-lw), (x1//2, y0+lw), (x1, y0+lw)], fill=color, width=lw, joint="round")
        d.ellipse([x0-lw, y1-2*lw, x0+lw, y1], fill=color); d.ellipse([x1-lw, y0, x1+lw, y0+2*lw], fill=color)
    elif mode == "elev": d.polygon([(lw, y1), (size*res//2, y0), (x1, y1)], fill=color)
    elif mode == "speed": 
        d.arc([x0, y0, x1, y1], 150, 390, fill=color, width=lw)
        cx, cy = size*res//2, size*res//2 + lw
        d.line([cx, cy, cx + size*res*0.25, cy - size*res*0.25], fill=color, width=lw)
        d.ellipse([cx-lw, cy-lw, cx+lw, cy+lw], fill=color)
    return img.resize((size, size), Image.Resampling.LANCZOS)

def hex_to_rgba(hex_color, alpha=255):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)

# --- UPLOADS ---
c_up1, c_up2 = st.columns(2)
with c_up1:
    st.markdown("### 📍 1. GPX Datei")
    up_gpx = st.file_uploader("GPX", label_visibility="collapsed", key="gpx_uploader")
    if up_gpx and st.session_state.last_gpx_file != up_gpx.name:
        st.session_state.last_gpx_file = up_gpx.name
        st.session_state.tour_title = up_gpx.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
        try:
            g = gpxpy.parse(io.BytesIO(up_gpx.getvalue()))
            d = g.time.strftime("%d.%m.%Y") if g.time else ""
            if not d:
                for p in [p for t in g.tracks for s in t.segments for p in s.points if p.time]:
                    d = p.time.strftime("%d.%m.%Y"); break
            if d: st.session_state.tour_date = d
        except: pass
        st.rerun()

with c_up2:
    st.markdown("### 📸 2. Foto")
    up_img = st.file_uploader("Foto", type=["jpg", "jpeg", "png"], label_visibility="collapsed", key="img_uploader")

# --- OPTIONEN ---
with st.expander("⚙️ Einstellungen [v4.3.0]", expanded=False): 
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        st.text_input("Tour Name", key="tour_title")
        st.text_input("Datum", key="tour_date")
        st.color_picker("Routenfarbe", key="c_line")
        st.number_input("Routenstärke", 1, 20, key="w_line")
    with col_opt2:
        st.checkbox("Start/Ziel anzeigen", key="show_markers")
        st.checkbox("Ø Geschwindigkeit", key="show_speed")
        st.checkbox("Höhenprofil", key="show_profile")
        st.checkbox("Minibox (Karte)", key="show_minibox")
        st.button("🔄 Zurücksetzen", on_click=reset_parameters)

# --- APP INSTALLIEREN ---
with st.expander("📲 App installieren (Safari, Chrome, Firefox)", expanded=False):
    st.markdown("### Hol dir GPX Share Pro auf dein Handy!")
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown("**🍎 iPhone (Safari)**\n1. Teilen 📤\n2. 'Zum Home-Bildschirm'")
    with c2: st.markdown("**🤖 Android (Chrome)**\n1. Menü ⋮\n2. 'App installieren'")
    with c3: st.markdown("**🦊 Firefox (Android)**\n1. Menü ⋮\n2. 'Installieren'")

# --- INFO REITER ---
with st.expander("ℹ️ Über GPX Share Pro", expanded=False):
    st.markdown("### 📜 Changelog v4.3.0")
    st.info("- Counter komplett entfernt (maximale Stabilität).\n- Schlanker Header mit Logo-Support.\n- Favicon aktiv.")
    st.markdown(f'<a href="https://www.paypal.com/donate?hosted_button_id=FF6FBUE84V7MG" target="_blank"><img src="https://www.paypalobjects.com/de_DE/i/btn/btn_donateCC_LG.gif" width="120"></a>', unsafe_allow_html=True)

st.divider()

# --- VERARBEITUNG ---
if up_gpx:
    try:
        gpx = gpxpy.parse(io.BytesIO(up_gpx.getvalue()))
        pts, elevs = [], []; d_total, a_gain, total_time = 0.0, 0.0, 0.0; l_p, l_e, l_t = None, None, None
        for seg in gpx.tracks[0].segments:
            s_pts = []
            for p in seg.points:
                s_pts.append([p.latitude, p.longitude]); elevs.append(p.elevation or 0)
                if l_p:
                    d_total += calc_dist(l_p[0], l_p[1], p.latitude, p.longitude)
                    if p.elevation and l_e and p.elevation > l_e: a_gain += (p.elevation - l_e)
                    if p.time and l_t:
                        dt = (p.time - l_t).total_seconds()
                        if 0 < dt < 1800: total_time += dt
                l_p, l_e, l_t = [p.latitude, p.longitude], p.elevation, p.time
            if s_pts: pts.append(s_pts)
        
        avg_s = d_total / (total_time / 3600.0) if total_time > 0 else 0.0
        w, h = 1080, 1920
        canvas = Image.new('RGBA', (w, h), (30, 30, 30, 255))
        if up_img:
            bg = ImageOps.exif_transpose(Image.open(io.BytesIO(up_img.getvalue()))).convert("RGBA")
            canvas.paste(ImageOps.fit(bg, (w, h), Image.Resampling.LANCZOS), (0, 0))
        
        overlay = Image.new('RGBA', (w, h), (0,0,0,0)); draw = ImageDraw.Draw(overlay)
        bh_t, bh_b = int(h * 0.20), int(h * 0.12)
        safe_rect(draw, [0, 0, w, bh_t], fill=(0, 0, 0, 160))
        safe_rect(draw, [0, h - bh_b, w, h], fill=(0, 0, 0, 160))
        
        if st.session_state.show_profile and len(elevs) > 1:
            e_min, e_max = min(elevs), max(elevs); e_r = (e_max - e_min) or 1
            profile_pts = [(10 + (i/max(1, len(elevs)-1))*(w-20), (h-bh_b)+(bh_b*0.85)-((ev-e_min)/e_r)*(bh_b*0.7)) for i, ev in enumerate(elevs)]
            rgb = hex_to_rgba(st.session_state.c_line)
            draw.polygon(profile_pts + [(w-10, h), (10, h)], fill=rgb[:3] + (120,))
            draw.line(profile_pts, fill=(255,255,255,255), width=4)
            
        draw_text_with_shadow(draw, (w//2, bh_t*0.35), st.session_state.tour_title, load_font(int(w*0.08*st.session_state.size_title)), fill=st.session_state.c_title)
        items = [("dist", f"{d_total:.1f} km"), ("speed", f"{avg_s:.1f} km/h"), ("elev", f"{int(a_gain)} m")]
        f_d, i_s = load_font(int(w*0.05*st.session_state.size_data)), int(w*0.05*st.session_state.size_data)
        cx, dy = (w - (len(items)*300)) // 2, bh_t*0.35 + 150
        for m, t in items:
            overlay.paste(draw_data_icon(m, i_s, st.session_state.c_data), (int(cx), int(dy-i_s//2)), draw_data_icon(m, i_s, st.session_state.c_data))
            draw_text_with_shadow(draw, (cx + 150, dy), t, f_d, fill=st.session_state.c_data); cx += 300
            
        final = Image.alpha_composite(canvas, overlay).convert('RGB')
        st.image(final, use_container_width=True)
        buf = io.BytesIO(); final.save(buf, format="JPEG", quality=95)
        st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), f"tour_v430.jpg", "image/jpeg")
            
    except Exception as e: st.error(f"Fehler: {e}")
