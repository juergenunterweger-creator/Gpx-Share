import streamlit as st
import os

# --- VERSION 2.8.20: ICON UPDATE ---

# Funktion, um zu prüfen, ob dein Logo da ist
def get_favicon():
    if os.path.exists("logo_icon.png"):
        return "logo_icon.png"
    return "🏍️" # Fallback, falls das Bild fehlt

st.set_page_config(
    page_title="GPX Share Pro XXL",
    page_icon=get_favicon(),
    layout="centered"
)

# ... (restlicher Code bleibt stabil wie in v2.8.1)
