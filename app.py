import streamlit as st
import gpxpy
import gpxpy.gpx
from PIL import Image, ImageDraw, ImageFont
import io
import math

# Hilfsfunktion für die Distanzberechnung
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Erdradius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

st.set_page_config(page_title="Tour Designer Pro", layout="centered")
st.title("🏍️ Jürgens Touren-Designer")

uploaded_image = st.file_uploader("1. Hintergrundfoto wählen", type=["jpg", "jpeg", "png"])
uploaded_gpx = st.file_uploader("2. GPX-Datei wählen", type=["gpx", "xml", "txt"])

if uploaded_image and uploaded_gpx:
    img = Image.open(uploaded_image).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    try:
        gpx_content = uploaded_gpx.read().decode("utf-8")
        gpx = gpxpy.parse(gpx_content)
        
        points = []
        total_dist = 0.0
        alt_gain = 0.0
        last_point = None
        
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    points.append((point.latitude, point.longitude))
                    if last_point:
                        # Distanz aufsummieren
                        total_dist += haversine(last_point.latitude, last_point.longitude, point.latitude, point.longitude)
                        # Höhenmeter aufsummieren
                        if point.elevation and last_point.elevation:
                            if point.elevation > last_point.elevation:
                                alt_gain += (point.elevation - last_point.elevation)
                    last_point = point
        
        if points:
            # 1. ROUTE ZEICHNEN
            lats, lons = zip(*points)
            min_lat, max_lat = min(lats), max(lats)
            min_lon, max_lon = min(lons), max(lons)
            margin = 0.15
            scaled_points = []
            for lat, lon in points:
                x = w * margin + (lon - min_lon) / (max_lon - min_lon) * w * (1 - 2*margin)
                y = h * (1 - margin) - (lat - min_lat) / (max_lat - min_lat) * h * (1 - 2*margin)
                scaled_points.append((x, y))
            
            line_width = max(5, int(w / 80))
            draw.line(scaled_points, fill=(0, 255, 255), width=line_width, joint="round")

            # 2. INFO-BOX ZEICHNEN (Oben Links)
            box_w, box_h = int(w * 0.35), int(h * 0.18)
            overlay = Image.new('RGBA', img.size, (0,0,0,0))
            overlay_draw = ImageDraw.Draw(overlay)
            # Halbtransparenter Hintergrund
            overlay_draw.rectangle([40, 40, 40 + box_w, 40 + box_h], fill=(0, 0, 0, 160))
            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            draw = ImageDraw.Draw(img)

            # Text schreiben (Größe dynamisch zur Bildbreite)
            font_size = max(20, int(w / 40))
            # Hinweis: Ohne spezielle .ttf Datei nutzt PIL den default font
            try:
                # Versuch eine Standardschrift zu laden (funktioniert oft lokal, bei Streamlit ggf. Default)
                text_font = ImageFont.load_default()
            except:
                text_font = ImageFont.load_default()

            tour_name = "Tour: Ranna Stausee"
            stats_text = f"Distanz: {total_dist:.1f} km\nHöhenmeter: {int(alt_gain)} m"
            
            draw.text((60, 60), tour_name, fill=(255, 255, 255))
            draw.text((60, 60 + font_size*2), stats_text, fill=(255, 255, 255))

            st.image(img, caption="Vorschau", use_container_width=True)
            
            # Download
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            st.download_button("📸 Bild speichern", buf.getvalue(), "tour_bild.jpg", "image/jpeg")
            
    except Exception as e:
        st.error(f"Fehler: {e}")
