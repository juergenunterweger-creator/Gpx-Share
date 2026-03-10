import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import math
import os

# --- PERSISTENTER COUNTER SETUP ---
try:
    from streamlit_gsheets import GSheetsConnection
    HAS_GSHEETS = True
except ImportError:
    HAS_GSHEETS = False

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro XXL", page_icon="🏍️", layout="centered")

# --- BRANDING KILLER (Absolut sauber) ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    .stDeployButton {display:none !important;}
    [data-testid="stHeader"] {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    .main .block-container {padding-top: 1.5rem !important;}
    </style>
    """, unsafe_allow_html=True)

# --- COUNTER FUNKTIONEN ---
def get_stats():
    """Liest den Zählerstand aus."""
    if HAS_GSHEETS:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(worksheet="Stats", ttl="1m")
            return int(df.iloc[0, 0])
        except: return 0
    return 0

def update_stats():
    """Erhöht den Zählerstand um 1."""
    if HAS_GSHEETS:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(worksheet="Stats", ttl=0)
            df.iloc[0, 0] = int(df.iloc[0, 0]) + 1
            conn.update(worksheet="Stats", data=df)
        except: pass

# --- STANDARDWERTE (v2.8.5) ---
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

def reset_parameters():
    for key, val in DEFAULTS.items(): st.session_state[key] = val

# --- HELFER FUNKTIONEN (Fonts & Geometrie) ---
def load_font(size):
    size = max(10, int(size))
    paths = ["font.ttf", "DejaVuSans-Bold.ttf"]
    for p in paths:
        try: return ImageFont.truetype(p, size)
        except: continue
    return ImageFont.load_default()

def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371; p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def draw_text_with_shadow(draw, pos, text, font, fill="white", shadow_color="black", offset=2):
    draw.text((pos[0]+offset, pos[1]+offset), text, fill=shadow_color, font=font, anchor="mm")
    draw.text(pos, text, fill=fill, font=font, anchor="mm")

def hex_to_rgba(hex_color, alpha=255):
    h = hex_color.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)

# --- UI HEADER ---
st.markdown('<div style="text-align:center; background:linear-gradient(135deg, #111, #2a2a2a); padding:20px; border-radius:15px; border:1px solid #333; margin-bottom:20px;"><h1 style="color:#da2323; margin:0;">GPX Share Pro XXL</h1></div>', unsafe_allow_html=True)

# --- UPLOADS ---
cup1, cup2 = st.columns(2)
with cup1: up_gpx = st.file_uploader("📍 GPX Datei", key="gpx_up")
with cup2: up_img = st.file_uploader("📸 Foto", type=["jpg", "jpeg", "png"], key="img_up")

# --- OPTIONEN ---
with st.expander("⚙️ Einstellungen"):
    o1, o2 = st.columns(2)
    with o1:
        st.text_input("Tour Name", key="tour_title")
        st.color_picker("Farbe", key="c_line")
    with o2:
        st.checkbox("Ränder für Storys", key="story_margins_active")
        st.button("🔄 Zurücksetzen", on_click=reset_parameters)

# --- INFO REITER MIT COUNTER ---
with st.expander("ℹ️ Über GPX Share Pro", expanded=False):
    # LIVE COUNTER ANZEIGE
    aktuelle_zahl = get_stats()
    st.markdown(f"### 🔥 Es wurden bereits **{aktuelle_zahl}** Storys erstellt")
    st.markdown("---")
    st.markdown("**Copyright: Jürgen Unterweger**")
    st.markdown(f'<a href="https://www.paypal.com/donate?hosted_button_id=FF6FBUE84V7MG" target="_blank"><img src="https://www.paypalobjects.com/de_DE/i/btn/btn_donateCC_LG.gif" width="120"></a>', unsafe_allow_html=True)

st.divider()

# --- VERARBEITUNG & BILD ---
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
        
        overlay = Image.new('RGBA', (w, h), (0,0,0,0)); draw = ImageDraw.Draw(overlay)
        bh_t = int(h * 0.20)
        draw.rectangle([0, 0, w, bh_t], fill=(0, 0, 0, 160))
        draw_text_with_shadow(draw, (w//2, bh_t//2), st.session_state.tour_title, load_font(int(w*0.08*st.session_state.size_title)), fill=st.session_state.c_line)
        
        final = Image.alpha_composite(canvas, overlay); st_disp = final.convert('RGB')
        
        st.image(st_disp, use_container_width=True)
        buf = io.BytesIO(); final.save(buf, format="PNG")
        
        # DOWNLOAD BUTTON TRIGGERT DEN COUNTER
        if st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), "tour.png", "image/png"):
            update_stats()
            
    except Exception as e: st.error(f"Fehler: {e}")
