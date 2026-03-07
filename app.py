import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageChops
import io
import math
import os

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro XXL", page_icon="🏍️", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #000000; }
    .title-modern {
        font-size: 36px; font-weight: 900;
        background: linear-gradient(90deg, #ff0000 0%, #8b0000 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 20px;
    }
    .stDownloadButton button {
        width: 100%; border-radius: 20px;
        background: linear-gradient(135deg, #ff0000 0%, #8b0000 100%) !important;
        color: white !important; font-weight: bold; border: none; height: 3em;
    }
    div[data-testid="stExpander"] details summary p {
        font-size: 1.2rem !important; font-weight: bold !important; color: #8b0000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# --- SEITENLEISTE (NUR LOGO) ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)

st.markdown("<p class='title-modern'>GPX Share Pro</p>", unsafe_allow_html=True)

if 'tour_name_val' not in st.session_state:
    st.session_state.tour_name_val = "Meine Tour"

# --- UPLOAD BEREICH ---
c1, c2 = st.columns(2)
with c1:
    up_gpx = st.file_uploader("📍 1. GPX Datei (Tour)")
    if up_gpx is not None:
        raw_name = up_gpx.name.rsplit('.', 1)[0]
        st.session_state.tour_name_val = raw_name.replace('_', ' ').replace('-', ' ')
with c2:
    up_img = st.file_uploader("📸 2. Foto wählen (Optional)", type=["jpg", "jpeg", "png"])

# --- OPTIONEN ---
with st.expander("⚙️ Optionen", expanded=False):
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        tour_title = st.text_input("Tour Name", value=st.session_state.tour_name_val)
        map_style = st.selectbox("Karten-Stil (wenn kein Foto)", ["OSM Standard", "Dark Mode", "Satellit", "Light Mode"])
        show_logo = st.checkbox("Zeige eigenes Logo", value=False)
        show_grid = st.checkbox("Raster im Höhenprofil", value=True)
        show_icons = st.checkbox("Icons in Infobox", value=True)
        logo_radius = st.slider("Logo-Ecken Radius", 0, 100, 20)
    with col_opt2:
        font_scale = st.slider("Schrift-Skalierung", 0.5, 3.0, 1.2)
        b_height_adj = st.slider("Balken Dicke", 0.05, 0.40, 0.15)
        w_line = st.slider("Linienstärke Route", 1, 100, 9)
        b_alpha = st.slider("Balken Deckkraft", 0, 255, 160)
        r_alpha = st.slider("Routen-Transparenz", 0, 255, 255)
        bg_alpha = st.slider("Hintergrund Transparenz", 0, 255, 255)
        c_line = st.color_picker("Routenfarbe", "#8B0000")

st.divider()

if up_gpx:
    try:
        up_gpx.seek(0)
        gpx = gpxpy.parse(up_gpx.read().decode("utf-8", errors="ignore"))
        pts, elevs = [], []
        d_total, a_gain = 0.0, 0.0
        last, last_elev = None, None
        for tr in gpx.tracks:
            for seg in tr.segments:
                for p in seg.points:
                    pts.append([p.latitude, p.longitude])
                    elevs.append(p.elevation if p.elevation is not None else 0)
                    if last:
                        d_total += calc_dist(last[0], last[1], p.latitude, p.longitude)
                        if p.elevation is not None and last_elev is not None:
                            diff = p.elevation - last_elev
                            if diff > 0: a_gain += diff
                    last, last_elev = [p.latitude, p.longitude], p.elevation

        if pts:
            lats, lons = zip(*pts)
            draw_line_manually = False
            
            if up_img:
                src_img = Image.open(up_img).convert("RGB")
                w, h = src_img.size
                draw_line_manually = True
            else:
                # KARTEN MODUS
                from staticmap import StaticMap, Line, CircleMarker
                w, h = 1080, 1920 
                tile_urls = {
                    "OSM Standard": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                    "Satellit": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                    "Dark Mode": "https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png",
                    "Light Mode": "https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png"
                }
                m = StaticMap(w, h, url_template=tile_urls[map_style])
                
                # ZUERST DATEN HINZUFÜGEN (WICHTIG!)
                line_pts = list(zip(lons, lats))
                m.add_line(Line(line_pts, c_line, w_line))
                
                # Padding Marker (unsichtbar) für Zoom
                mi_la, ma_la = min(lats), max(lats)
                pad = (ma_la - mi_la) * 0.3
                m.add_marker(CircleMarker((lons[0], ma_la + pad), '#00000000', 1))
                m.add_marker(CircleMarker((lons[0], mi_la - pad), '#00000000', 1))
                
                # Start/Ziel Marker
                m.add_marker(CircleMarker((lons[0], lats[0]), '#FFFFFF', 12))
                m.add_marker(CircleMarker((lons[-1], lats[-1]), c_line, 12))
                
                # ERST JETZT RENDERN
                src_img = m.render().convert("RGB")

            # Hintergrund Transparenz
            base_img = Image.new('RGB', (w, h), "white")
            src_img_rgba = src_img.convert("RGBA")
            alpha_band = src_img_rgba.split()[3].point(lambda p: int(p * bg_alpha / 255))
            src_img_rgba.putalpha(alpha_band)
            base_img.paste(src_img_rgba, (0, 0), src_img_rgba)

            # UI Layer
            overlay = Image.new('RGBA', (w, h), (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            rgb_route = tuple(int(c_line[i*2+1:i*2+3], 16) for i in range(3))

            bh_top, bh_bot = int(h * b_height_adj), int(h * (b_height_adj + 0.02))
            draw.rectangle([0, 0, w, bh_top], fill=(0, 0, 0, b_alpha))
            draw.rectangle([0, h - bh_bot, w, h], fill=(0, 0, 0, b_alpha))

            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" # Pfad ggf. anpassen
            try:
                font_t = ImageFont.truetype(font_path, int(w * 0.08 * font_scale))
                font_d = ImageFont.truetype(font_path, int(w * 0.06 * font_scale))
                font_grid = ImageFont.truetype(font_path, int(w * 0.02 * font_scale))
            except: font_t = font_d = font_grid = ImageFont.load_default()

            if len(elevs) > 1:
                e_min, e_max = min(elevs), max(elevs)
                e_range = e_max - e_min if e_max > e_min else 1
                grid_y_start = h - bh_bot
                if show_grid:
                    for i in range(1, 4):
                        gy = grid_y_start + i * (bh_bot / 4)
                        draw.line([(0, gy), (w, gy)], fill=(255, 255, 255, 45))
                        draw.text((w*0.01, gy-2), f"{int(e_min + ((grid_y_start+bh_bot*0.85-gy)/(bh_bot*0.7))*e_range)}m", fill=(255,255,255,160), font=font_grid, anchor="ld")

                profile_pts = [((i/len(elevs))*w, (h-bh_bot)+(bh_bot*0.85)-((ev-e_min)/e_range)*(bh_bot*0.7)) for i, ev in enumerate(elevs)]
                draw.polygon(profile_pts + [(w, h), (0, h)], fill=rgb_route + (int(r_alpha * 0.5),))
                draw.line(profile_pts, fill=(255,255,255, r_alpha), width=max(3, int(w*0.003)))

            draw.text((w//2, bh_top//2), tour_title, fill="white", font=font_t, anchor="mm")
            
            # Icons
            icon_size = int(w * 0.06 * 1.3 * font_scale)
            # TACHO ICON
            img_dist = Image.new('RGBA', (icon_size, icon_size), (0,0,0,0))
            d_i = ImageDraw.Draw(img_dist)
            d_i.arc([2, 2, icon_size-2, icon_size-2], start=150, end=390, fill="white", width=max(2, icon_size//15))
            d_i.line([icon_size//2, icon_size//2, icon_size*0.8, icon_size*0.3], fill="white", width=max(2, icon_size//15))
            
            # BERG ICON
            img_elev = Image.new('RGBA', (icon_size, icon_size), (0,0,0,0))
            d_e = ImageDraw.Draw(img_elev)
            d_e.polygon([(0, icon_size*0.9), (icon_size*0.4, icon_size*0.2), (icon_size*0.8, icon_size*0.9)], fill="white")
            d_e.line([(icon_size*0.9, icon_size*0.8), (icon_size*0.9, icon_size*0.1)], fill="white", width=max(2, icon_size//15))

            txt_d, txt_e = f"{d_total:.1f} km", f"{int(a_gain)} m"
            w_d, w_e = draw.textlength(txt_d, font=font_d), draw.textlength(txt_e, font=font_d)
            i_w = icon_size if show_icons else 0
            gap = int(w*0.02) if show_icons else 0
            total_w = (i_w + gap + w_d) + int(w*0.12) + (i_w + gap + w_e)
            sx, y_p = (w - total_w) // 2, h - int(bh_bot * 0.35) 

            if show_icons: overlay.paste(img_dist, (int(sx), int(y_p - icon_size // 2)), img_dist)
            draw.text((sx + i_w + gap, y_p), txt_d, fill="white", font=font_d, anchor="lm")
            xe = sx + i_w + gap + w_d + int(w*0.12)
            if show_icons: overlay.paste(img_elev, (int(xe), int(y_p - icon_size // 2)), img_elev)
            draw.text((xe + i_w + gap, y_p), txt_e, fill="white", font=font_d, anchor="lm")

            if draw_line_manually:
                mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
                margin = 0.20
                scaled = [(w*margin + (lon-mi_lo)/(ma_lo-mi_lo)*w*(1-2*margin), h*(1-margin) - (lat-mi_la)/(ma_la-mi_la)*h*(1-2*margin)) for lat, lon in pts]
                draw.line(scaled, fill=rgb_route + (r_alpha,), width=w_line, joint="round")

            final = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
            st.image(final, use_container_width=True)
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), "ride_pro_final.jpg", "image/jpeg")
    except Exception as e: st.error(f"Fehler: {e}")
