# --- TRACKING & DATABASE SETUP (v2.7.50) ---
from streamlit_gsheets import GSheetsConnection

# 1. Verbindung zum Google Sheet herstellen
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Check: Bist du es? (Exklusion via URL-Parameter)
# Nutze den Link: https://deine-app.streamlit.app/?admin=true
is_admin = st.query_params.get("admin") == "true"

def count_usage():
    if not is_admin:
        try:
            # Aktuellen Wert lesen, erhöhen und zurückschreiben
            df = conn.read(worksheet="Stats")
            current_count = df.iloc[0, 0]
            df.iloc[0, 0] = current_count + 1
            conn.update(worksheet="Stats", data=df)
        except:
            pass # Verhindert Absturz, falls das Sheet mal nicht erreichbar ist

# --- LOGIK BEIM SPEICHERN ---
# Diesen Aufruf packen wir in den Download-Button:
if st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), "tour.png", "image/png"):
    count_usage()
