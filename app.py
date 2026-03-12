import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
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

# (Branding Killer wurde komplett entfernt)

# --- STANDARDWERTE (v3.1.2 Beta) ---
DEFAULTS = {
    "layout_style": "Classic (Dark Overlay)",
    "tour_title": "Meine Tour",
    "tour_date": "",
    "c_line": "#DA2323",
    "c_title": "#DA2323",
    "c_date": "#FFFFFF",
    "c_data": "#FFFFFF",
    "c_grid": "#FFFFFF",
    "w_line": 9,
    "show_markers": True,
    "show_speed": True,
    "show_profile": True,
    "show_logo": False,
    "show_route": True,
    "show_minibox": True,
    "logo_type": "Grafisches logo",
    "show_date": True,
    "auto_intervals": True,
    "grid_m_interval": 250,
    "grid_km_interval": 10,
    "bg_opacity": 100,
    "size_title": 1.5,
    "size_date": 1.0,
    "size_data": 1.0,
    "size_grid": 1.0,
    "size_logo": 1.0,
    "size_minibox": 1.0,
    "story_margins_active": True,
    "margin_top": 150,
    "margin_bottom": 100,
    "img_zoom": 100,          
    "img_offset_x": 0,        
    "img_offset_y": 0,
    "img_bw": False,
    "img_enhance": False,
    "custom_text": "",
    "c_custom_text": "#FFFFFF",
    "size_custom_text": 1.5,
    "pos_x_custom_text": 540,
    "pos_y_custom_text": 960,
    "show_bg_top": True,
    "show_bg_bottom": True,
    "show_bg_date": True,
    "show_bg_minibox": True,
    "show_bg_custom_text": False
}

# Initialisierung der Session State Werte
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

if "last_gpx_file" not in st.session_state:
    st.session_state.last_gpx_file = ""

# --- HOTFIX: Alte gespeicherte Session-Werte reparieren ---
if st.session_state.get("img_zoom", 100) < 10:
    st.session_state["img_zoom"] = 100

# --- HELFER FUNKTIONEN ---
def reset_parameters():
    for key, val in DEFAULTS.items():
        st.session_state[key] = val

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
    if offset > 0:
        draw.text((x+offset, y+offset), text, fill=shadow_color, font=font, anchor=anchor)
    draw.text((x, y), text, fill=fill, font=font, anchor=anchor)

def draw_marker(draw, pos, color, label=""):
    x, y = pos
    r = 14
    safe_ellipse(draw, [x-r-2, y-r-2, x+r+2, y+r+2], fill="white")
    safe_ellipse(draw, [x-r, y-r, x+r+2, y+r+2], fill=color, outline="black", width=2)
    if label:
        f = load_font(16)
        draw.text((int(x), int(y)), label, fill="white", font=f, anchor="mm")

def draw_data_icon(mode, size, color="white"):
    res = 4
    size = int(max(10, size))
    img = Image.new('RGBA', (size*res, size*res), (0,0,0,0))
    d = ImageDraw.Draw(img)
    lw = int(max(2, size*res*0.08))
    x0, y0, x1, y1 = lw, lw, size*res - lw, size*res - lw
    if mode == "dist":
        d.line([(x0, y1-lw), (x1//2, y1-lw), (x1//2, y0+lw), (x1, y0+lw)], fill=color, width=lw, joint="round")
        d.ellipse([x0-lw, y1-2*lw, x0+lw, y1], fill=color)
        d.ellipse([x1-lw, y0, x1+lw, y0+2*lw], fill=color)
    elif mode == "elev":
        d.polygon([(lw, y1), (size*res//2, y0), (x1, y1)], fill=color)
    elif mode == "speed": 
        d.arc([x0, y0, x1, y1], 150, 390, fill=color, width=lw)
        cx, cy = size*res//2, size*res//2 + lw
        d.line([cx, cy, cx + size*res*0.25, cy - size*res*0.25], fill=color, width=lw)
        d.ellipse([cx-lw, cy-lw, cx+lw, cy+lw], fill=color)
    return img.resize((size, size), Image.Resampling.LANCZOS)

def draw_graphical_logo(draw, pos, scale=1.0, color="#DA2323"):
    x, y = int(pos[0]), int(pos[1])
    icon_size = int(50 * scale)
    rgb = hex_to_rgba(color)
    safe_ellipse(draw, [x, y, x + icon_size, y + icon_size], fill=rgb, outline="white", width=max(1, int(2*scale)))
    draw.polygon([(x+icon_size*0.2, y+icon_size*0.75), (x+icon_size*0.5, y+icon_size*0.25), (x+icon_size*0.8, y+icon_size*0.75)], fill="white")
    draw_text_with_shadow(draw, (x + icon_size + int(15*scale), y + icon_size//2), "GPX Share Pro", load_font(int(32 * scale)), fill="white", shadow_color="black", offset=2, anchor="lm")

def hex_to_rgba(hex_color, alpha=255):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)

def get_logo_path():
    for name in ["logo.png", "Logo.png", "LOGO.png"]:
        if os.path.exists(name): return name
    return None

# --- APP-HEADER UI ---
st.markdown("""
<style>
.header-box {
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #111111 0%, #2a2a2a 100%);
    padding: 15px; border-radius: 15px; box-shadow: 0px 8px 16px rgba(218, 35, 35, 0.4);
    margin-bottom: 25px; border: 1px solid #333;
    margin-top: 10px;
}
.header-title {
    font-size: 34px; font-weight: 900;
    background: linear-gradient(90deg, #ff4b4b 0%, #da2323 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0; text-transform: uppercase; text-align: center;
    line-height: 1.2;
}
.header-logo {
    height: 45px; margin-right: 15px;
}
</style>
""", unsafe_allow_html=True)

logo_html = ""
app_logo_path = get_logo_path()
if app_logo_path:
    try:
        with open(app_logo_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        logo_html = f'<img src="data:image/png;base64,{encoded_string}" class="header-logo">'
    except Exception:
        pass

st.markdown(f'<div class="header-box">{logo_html}<p class="header-title">GPX Share Pro XXL</p></div>', unsafe_allow_html=True)

# --- UPLOADS ---
c_up1, c_up2 = st.columns(2)
with c_up1:
    st.markdown("### 📍 1. GPX Datei")
    up_gpx = st.file_uploader("GPX Upload", label_visibility="collapsed", key="gpx_uploader")
    if up_gpx:
        if st.session_state.last_gpx_file != up_gpx.name:
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
    up_img = st.file_uploader("Foto Upload", type=["jpg", "jpeg", "png"], label_visibility="collapsed", key="img_uploader")

# --- NEUE EINSTELLUNGEN (VERSION 3.1.2 Beta) ---
with st.expander("⚙️ Einstellungen [v3.1.2 Beta]", expanded=False): 
    tab_inhalt, tab_design, tab_bild = st.tabs(["📝 Inhalte", "🎨 Design", "🖼️ Bildanpassung"])
    
    with tab_inhalt:
        c1, c2 = st.columns(2)
        with c1:
            st.write("**📝 Tour Details**")
            st.text_input("Tour Name", key="tour_title")
            st.text_input("Datum", key="tour_date")
            st.checkbox("Datum im Bild anzeigen", key="show_date")
            st.text_input("Eigener Kommentar (z.B. Top Tour!)", key="custom_text")
        with c2:
            st.checkbox("Start/Ziel (S/Z)", key="show_markers")
            st.checkbox("Ø Geschwindigkeit", key="show_speed")
            st.checkbox("Höhenprofil", key="show_profile")
            st.checkbox("Route in Bild anzeigen", key="show_route")
            st.checkbox("Minibox (Karte)", key="show_minibox")
            st.checkbox("App Logo (Im Bild)", key="show_logo")
            st.radio("Logoart", ["Grafisches logo", "Smartes Logo"], horizontal=True, key="logo_type")

    with tab_design:
        st.write("**📱 Layout Style**")
        st.radio("Wähle dein bevorzugtes Design:", ["Classic (Dark Overlay)", "Modern (White Card)"], key="layout_style", horizontal=True)
        st.write("---")
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**🎨 Farben & Routen-Style**")
            col_c1, col_c2 = st.columns(2)
            with col_c1: st.color_picker("Routenfarbe", key="c_line")
            with col_c2: st.number_input("Routenstärke", 1, 20, key="w_line")
            st.color_picker("Farbe Titel", key="c_title")
            st.color_picker("Farbe Daten
