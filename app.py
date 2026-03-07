import streamlit as st
import gpxpy
from PIL import Image, ImageDraw

st.set_page_config(page_title="Tour Designer", layout="centered")
st.title("🏍️ GPX Share")

# Erlaubt auch XML und TXT, damit das iPhone die Datei nicht ausgraut
uploaded_image = st.file_uploader("1. Hintergrundfoto wählen", type=["jpg", "jpeg", "png"])
uploaded_gpx = st.file_uploader("2. GPX-Datei wählen", type=["gpx", "xml", "txt"])

if uploaded_image and uploaded_gpx:
    # Bild laden
    img = Image.open(uploaded_image).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    try:
        # GPX einlesen
        gpx_content = uploaded_gpx.read().decode("utf-8")
        gpx = gpxpy.parse(gpx_content)
        points = []
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    points.append((point.latitude, point.longitude))
        
        if points:
            lats, lons = zip(*points)
            min_lat, max_lat = min(lats), max(lats)
            min_lon, max_lon = min(lons), max(lons)
            
            # Die Route wird mit 15% Randabstand auf das Bild gerechnet
            margin = 0.15 
            draw_w = w * (1 - 2 * margin)
            draw_h = h * (1 - 2 * margin)
            
            scaled_points = []
            for lat, lon in points:
                # Koordinaten umrechnen (Invertiert für Bild-Koordinaten)
                x = w * margin + (lon - min_lon) / (max_lon - min_lon) * draw_w
                y = h * (1 - margin) - (lat - min_lat) / (max_lat - min_lat) * draw_h
                scaled_points.append((x, y))
            
            # Linie zeichnen (Cyan-Blau, 1% der Bildbreite dick)
            line_width = max(5, int(w / 100))
            draw.line(scaled_points, fill=(0, 255, 255), width=line_width, joint="round")
            
            # Ergebnis anzeigen
            st.image(img, caption="Dein fertiges Touren-Bild", use_container_width=True)
            
            # Speichern-Option
            import io
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=95)
            st.download_button("📸 Bild auf iPhone speichern", buf.getvalue(), "mein_tourbild.jpg", "image/jpeg")
            
    except Exception as e:
        st.error(f"Fehler beim Lesen der GPX-Datei: {e}")
