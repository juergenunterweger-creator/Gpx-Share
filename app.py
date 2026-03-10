import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import math
import os

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

# --- AGGRESSIVER BRANDING KILLER & HEADER-STYLING (Schmälerer Header) ---
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
            
            # Ich habe das padding-top hier auf 0.5rem reduziert, um den Header zu schmälern.
            .main .block-container {padding-top: 0.5rem !important;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# ... (restlicher Code bleibt stabil wie in v2.8.1)
