import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import math
import os

# --- PERSISTENTER COUNTER SETUP (v2.8.2 Beta) ---
# Wir versuchen die Verbindung zu laden, aber ohne die App zu killen
try:
    from streamlit_gsheets import GSheetsConnection
    HAS_GSHEETS = True
except ImportError:
    HAS_GSHEETS = False

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

# --- AGGRESSIVER BRANDING KILLER ---
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
            .main .block-container {padding-top: 1rem !important;}
            </style>
            """, unsafe_allow_html=True)

# --- COUNTER LOGIK (Safe Mode) ---
def get_counter_value():
    if not HAS_GSHEETS: return "Aktiv"
    try:
        # Verbindung nur aufbauen, wenn wir nicht im Admin-Modus sind
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Stats", ttl="1m")
        return str(int(df.iloc[0, 0]))
    except:
        return "Online" # Fallback, damit die Seite nicht weiß wird

def increment_counter():
    if HAS_GSHEETS:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(worksheet="Stats", ttl=0)
            df.iloc[0, 0] = int(df.iloc[0, 0]) + 1
            conn.update(worksheet="Stats", data=df)
        except:
            pass

# --- STANDARDWERTE (v2.8.1 Basis) ---
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

# (Helfer-Funktionen wie reset_parameters, load_font, etc. hier einfügen...)
# [Da der restliche Code identisch mit v2.8.1 ist, kürze ich hier ab]

# --- INFO REITER MIT COUNTER ---
with st.expander("ℹ️ Über GPX Share Pro", expanded=False):
    # Hier wird der Counter angezeigt
    st.markdown(f"### 🔥 Schon **{get_counter_value()}** Storys erstellt!")
    st.markdown("---")
    st.markdown("**Copyright: Jürgen Unterweger**")
    st.markdown(f'<a href="https://www.paypal.com/donate?hosted_button_id=FF6FBUE84V7MG" target="_blank"><img src="https://www.paypalobjects.com/de_DE/i/btn/btn_donateCC_LG.gif" width="120"></a>', unsafe_allow_html=True)

# (Bildverarbeitungs-Logik...)

# --- DOWNLOAD BUTTON TRIGGERT COUNTER ---
if up_gpx:
    # ... (Bilderstellung) ...
    buf = io.BytesIO()
    # final_download.save(buf, format="PNG")
    
    if st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), "tour.png", "image/png"):
        increment_counter()
