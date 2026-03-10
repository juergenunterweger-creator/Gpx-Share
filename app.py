import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import math
import os

# --- PERSISTENTER COUNTER SETUP (v2.8.6) ---
try:
    from streamlit_gsheets import GSheetsConnection
    HAS_GSHEETS = True
except ImportError:
    HAS_GSHEETS = False

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro XXL", page_icon="🏍️", layout="centered")

# --- AGGRESSIVER BRANDING KILLER (v2.8.1 Style) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden !important;}
            footer {visibility: hidden !important;}
            header {visibility: hidden !important;}
            #stDecoration {display:none !important;}
            [data-testid="stHeader"] {display: none !important;}
            .stDeployButton {display:none !important;}
            [data-testid="stToolbar"] {display: none !important;}
            div.stActionButton {display:none !important;}
            .main .block-container {padding-top: 1rem !important;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- COUNTER FUNKTIONEN ---
def get_stats():
    """Liest den aktuellen Zählerstand aus dem Google Sheet."""
    if HAS_GSHEETS:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            # Liest das Blatt 'Stats', Caching für 1 Minute
            df = conn.read(worksheet="Stats", ttl="1m")
            return int(df.iloc[0, 0])
        except:
            return 0
    return 0

def update_stats():
    """Erhöht den Zählerstand im Google Sheet um 1."""
    if HAS_GSHEETS:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            # ttl=0 erzwingt das Lesen des neuesten Wertes vor dem Schreiben
            df = conn.read(worksheet="Stats", ttl=0)
            df.iloc[0, 0] = int(df.iloc[0, 0]) + 1
            conn.update(worksheet="Stats", data=df)
        except:
            pass

# --- STANDARDWERTE (v2.8.6) ---
DEFAULTS = {
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
    "show_route": False,
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
    "margin_bottom": 100
}

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

if "last_gpx_file" not in st.session_state:
    st.session_state.last_gpx_file = ""

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
    R = 6371; p1, p2 = math.radians(lat1), math.radians(lat2)
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
        f = load_font(16); draw.text((int(x), int(y)), label, fill="white", font=f, anchor="mm")

def draw_data_icon(mode, size, color="white"):
    res = 4; size = int(max(10, size))
    img = Image.new('RGBA', (size*res, size*res), (0,0,0,0)); d = ImageDraw.Draw(img)
    lw = int(max(2, size*res*0.08)); x0, y0, x1, y1 = lw, lw, size*res - lw, size*res - lw
    if mode == "dist":
        d.line([(x0, y1-lw), (x1//2, y1-lw), (x1//2, y0+lw), (x1, y0+lw)], fill=color, width=lw, joint="round")
        d.ellipse([x0-lw, y1-2*lw, x0+lw, y1], fill=color); d.ellipse([x1-lw, y0, x1+lw, y0+2*lw], fill=color)
    elif mode == "elev": d.polygon([(lw, y1), (size*res//2, y0), (x1, y1)], fill=color)
    elif mode == "speed": 
        d.arc([x0, y0, x1, y1], 150, 390, fill=color, width=lw); cx, cy = size*res//2, size*res//2 + lw
        d.line([cx, cy, cx + size*res*0.25, cy - size*res*0.25], fill=color, width=lw); d.ellipse([cx-lw, cy-lw, cx+lw, cy+lw], fill=color)
    return img.resize((size, size), Image.Resampling.LANCZOS)

def draw_graphical_logo(draw, pos, scale=1.0, color="#DA2323"):
    x, y = int(pos[0]), int(pos[1]); icon_size = int(50 * scale); rgb = hex_to_rgba(color)
    safe_ellipse(draw, [x, y, x + icon_size, y + icon_size], fill=rgb, outline="white", width=max(1, int(2*scale)))
    draw.polygon([(x+icon_size*0.2, y+icon_size*0.75), (x+icon_size*0.5, y+icon_size*0.25), (x+icon_size*0.8, y+icon_size*0.75)], fill="white")
    draw_text_with_shadow(draw, (x + icon_size + int(15*scale), y + icon_size//2), "GPX Share Pro", load_font(int(32 * scale)), fill="white", anchor="lm")

def hex_to_rgba(hex_color, alpha=255):
    h = hex_color.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)

def get_logo_path():
    for name in ["logo.png", "Logo.png"]:
        if os.path.exists(name): return name
    return None

# --- APP-HEADER UI ---
st.markdown("""
<style>
.stApp { background-color: #ffffff; color: #000000; } 
.header-box {
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #111111 0%, #2a2a2a 100%);
    padding: 20px; border-radius: 15px; box-shadow: 0px 10px 20px rgba(218, 35, 35, 0.4);
    margin-bottom: 30px; border: 1px solid #333;
}
.header-title {
    font-size: 38px; font-weight: 900;
    background: linear-gradient(90deg, #ff4b4b 0%, #da2323 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0; text-transform: uppercase; text-align: center;
}
</style>
<div class="header-box"><p class="header-title">GPX Share Pro XXL</p></div>
""", unsafe_allow_html=True)

# --- UPLOADS ---
c_up1, c_up2 = st.columns(2)
with c_up1:
    up_gpx = st.file_uploader("📍 1. GPX Datei wählen", label_visibility="collapsed", key="gpx_uploader")
    if up_gpx:
        if st.session_state.last_gpx_file != up_gpx.name:
            st.session_state.last_gpx_file = up_gpx.name
            st.session_state.tour_title = up_gpx.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
            st.rerun()

with c_up2:
    up_img = st.file_uploader("📸 2. Foto wählen", type=["jpg", "jpeg", "png"], label_visibility="collapsed", key="img_uploader")

# --- OPTIONEN ---
with st.expander("⚙️ Einstellungen [v2.8.6]", expanded=False): 
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        st.write("**📝 Tour & Design**")
        st.text_input("Tour Name", key="tour_title")
        st.text_input("Datum", key="tour_date")
        c_c1, c_c2 = st.columns(2)
        with c_c1: st.color_picker("Routenfarbe", key="c_line")
        with c_c2: st.number_input("Routenstärke", 1, 20, key="w_line")
        st.number_input("Hintergrund Dimmer (%)", 0, 100, key="bg_opacity")
    with col_opt2:
        st.write("**✅ Ein- / Ausblenden**")
        st.checkbox("Start/Ziel (S/Z)", key="show_markers")
        st.checkbox("Ø Geschwindigkeit", key="show_speed")
        st.checkbox("Höhenprofil", key="show_profile")
        st.checkbox("App Logo (Im Bild)", key="show_logo")
        st.checkbox("Minibox (Karte)", key="show_minibox")
        st.write("**📏 Story Ränder**")
        st.checkbox("Ränder für Storys", key="story_margins_active")
        if st.session_state.story_margins_active:
            st.number_input("Rand oben (px)", 0, 500, key="margin_top", step=10)
            st.number_input("Rand unten (px)", 0, 500, key="margin_bottom", step=10)
        st.button("🔄 Alles zurücksetzen", on_click=reset_parameters)

# --- INFO REITER MIT LIVE COUNTER ---
with st.expander("ℹ️ Über GPX Share Pro", expanded=False):
    # --- ANZEIGE DES COUNTERS ---
    aktuelle_zahl = get_stats()
    st.markdown(f"### 🔥 Es wurden bereits **{aktuelle_zahl}** Storys erstellt")
    
    if st.session_state.logo_type == "Smartes Logo":
        menu_logo = Image.new('RGBA', (400, 100), (30, 30, 30, 255))
        draw_graphical_logo(ImageDraw.Draw(menu_logo), (20, 25), scale=1.0, color=st.session_state.c_line)
        st.image(menu_logo, use_container_width=False)
    else:
        logo_file = get_logo_path()
        if logo_file: st.image(logo_file, width=250)
    
    st.markdown("---")
    st.markdown("**Copyright: Jürgen Unterweger**")
    st.markdown(f'<a href="https://www.paypal.com/donate?hosted_button_id=FF6FBUE84V7MG" target="_blank"><img src="https://www.paypalobjects.com/de_DE/i/btn/btn_donateCC_LG.gif" width="120"></a>', unsafe_allow_html=True)
    st.markdown(f'<a href="whatsapp://send?text=Schau%20dir%20mal%20diese%20App%20an!%20https://gpx-share-oh4dfakuqvfxadxmg3qhhq.streamlit.app/" style="display: block; width: 100%; padding: 10px; background-color: #25D366; color: white; text-align: center; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top:10px;">🚀 App empfehlen (WhatsApp)</a>', unsafe_allow_html=True)

st.divider()

# --- VERARBEITUNG & BILDERZEUGUNG ---
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
        w, h = 1080, 1920; canvas = Image.new('RGBA', (w, h), (30, 30, 30, 255))
        if up_img:
            bg = ImageOps.exif_transpose(Image.open(io.BytesIO(up_img.getvalue()))).convert("RGBA")
            canvas.paste(ImageOps.fit(bg, (w, h), Image.Resampling.LANCZOS), (0, 0))
        if st.session_state.bg_opacity < 100:
            canvas = Image.blend(Image.new('RGBA', (w, h), (255, 255, 255, 255)), canvas, st.session_state.bg_opacity / 100)

        overlay = Image.new('RGBA', (w, h), (0,0,0,0)); draw = ImageDraw.Draw(overlay)
        bh_t, bh_b = int(h * 0.20), int(h * 0.12)
        safe_rect(draw, [0, 0, w, bh_t], fill=(0, 0, 0, 160)); safe_rect(draw, [0, h - bh_b, w, h], fill=(0, 0, 0, 160))
        draw_text_with_shadow(draw, (w//2, bh_t*0.35), st.session_state.tour_title, load_font(int(w*0.08*st.session_state.size_title)), fill=st.session_state.c_line)
        
        final = Image.alpha_composite(canvas, overlay); st_image_display = final.convert('RGB')
        m_top, m_bot = st.session_state.margin_top, st.session_state.margin_bottom
        if st.session_state.story_margins_active and (m_top > 0 or m_bot > 0):
            new_w, new_h = final.width, final.height + m_top + m_bot
            canvas_with_margins = Image.new('RGBA', (new_w, new_h), (0, 0, 0, 0))
            canvas_with_margins.paste(final, (0, m_top)); final_download = canvas_with_margins
        else: final_download = final

        st.image(st_image_display, use_container_width=True)
        buf = io.BytesIO(); final_download.save(buf, format="PNG")
        
        # --- DOWNLOAD BUTTON TRIGGERT DEN COUNTER ---
        if st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), f"tour_final.png", "image/png"):
            update_stats()
            
    except Exception as e: st.error(f"Fehler: {e}")
