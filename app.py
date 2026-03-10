import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import math
import os

# --- NEU: SICHERER IMPORT FÜR TRACKING ---
try:
    from streamlit_gsheets import GSheetsConnection
    HAS_GSHEETS = True
except ImportError:
    HAS_GSHEETS = False

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro XXL", page_icon="🏍️", layout="centered")

# --- ADMIN & TRACKING LOGIK ---
is_admin = st.query_params.get("admin") == "true"

def count_usage():
    if HAS_GSHEETS and not is_admin:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(worksheet="Stats", ttl=0) # ttl=0 erzwingt frische Daten
            current_count = int(df.iloc[0, 0])
            df.iloc[0, 0] = current_count + 1
            conn.update(worksheet="Stats", data=df)
        except Exception as e:
            # Wir verschlucken den Fehler heimlich, damit der User nichts merkt
            pass
