import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont
import numpy as np

st.title("GPX Share")

# Upload-Bereich
uploaded_image = st.file_uploader("1. Wähle dein Hintergrundfoto", type=["jpg", "jpeg", "png"])
uploaded_gpx = st.file_uploader("2. Wähle deine GPX-Datei", type=["gpx"])

if uploaded_image and uploaded_gpx:
   # Bild laden
   img = Image.open(uploaded_image).convert("RGB")
   draw = ImageDraw.Draw(img)
   width, height = img.size

   # GPX Daten auslesen
   gpx = gpxpy.parse(uploaded_gpx)
   points = []
   for track in gpx.tracks:
       for segment in track.segments:
           for point in segment.points:
               points.append((point.latitude, point.longitude))

   if points:
       # Route auf Bildgröße skalieren
       lats, lons = zip(*points)
       min_lat, max_lat = min(lats), max(lats)
       min_lon, max_lon = min(lons), max(lons)

       # Mapping der Koordinaten auf die Bildpunkte (mit Randabstand)
       margin = 100
       scaled_points = []
       for lat, lon in points:
           x = margin + (lon - min_lon) / (max_lon - min_lon) * (width - 2 * margin)
           y = height - (margin + (lat - min_lat) / (max_lat - min_lat) * (height - 2 * margin))
           scaled_points.append((x, y))

       # Route zeichnen (Cyan-Linie wie im Beispiel)
       draw.line(scaled_points, fill=(0, 255, 255), width=int(width/150))

       # Tour-Daten Text (Einfaches Overlay)
       st.image(img, caption="Vorschau deiner Tour", use_column_width=True)

       # Download Button
       st.download_button("Bild herunterladen", data=uploaded_image, file_name="tour_fertig.jpg")
