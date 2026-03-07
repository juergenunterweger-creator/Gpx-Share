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

def get_fitted_font(draw, text, max_width, start_size, font_path):
    size = int(start_size)
    try:
        font = ImageFont.truetype(font_path, size)
    except:
        font = ImageFont.load_default()
    while draw.textlength(text, font=font) > max_width and size > 10:
        size -= 2
        try:
            font = ImageFont.truetype(font_path, size)
        except:
            break
    return font

with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)

st.markdown("<p class='title-modern'>GPX Share Pro</p>", unsafe_allow_html=True)

if 'tour_name_val' not in st.session_state:
    st.session_state.tour_name_val = "Meine Tour"

c1, c2 = st.columns(2)
with c1:
    up_gpx = st.file_uploader("📍 1. GPX Datei (Tour)")
    if up_gpx is not None:
        raw_name = up_gpx.name.rsplit('.', 1)[0]
        st.session_state.tour_name_val = raw_name.replace('_', ' ').replace('-', ' ')
with c2:
    up_img = st.file_uploader("📸 2. Foto wählen (Optional)", type=["jpg", "jpeg", "png"])

with st.expander("⚙️ Optionen", expanded=False):
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        tour_title = st.text_input("Tour Name", value=st.session_state.tour_name_val)
        map_style = st.selectbox("Karten-Stil", ["OSM Standard", "Dark Mode", "Satellit", "Light Mode"])
        show_logo = st.checkbox("Zeige eigenes Logo", value=False)
        show_profile = st.checkbox("Höhenprofil anzeigen", value=True)
        show_grid = st.checkbox("Raster im Höhenprofil", value=True)
        show_icons = st.checkbox("Icons in Infobox", value=True)
        show_units = st.checkbox("Einheiten anzeigen", value=True)
        fill_profile = st.checkbox("Füllung Höhenprofil", value=True)
    with col_opt2:
        font_scale = st.slider("Schrift-Skalierung", 0.5, 3.0, 1.5)
        b_height_adj = st.slider("Balken Dicke", 0.05, 0.40, 0.15)
        w_line = st.slider("Linienstärke Route", 1, 100, 9)
        b_alpha = st.slider("Balken Deckkraft", 0, 255, 160)
        r_alpha = st.slider("Routen-Transparenz", 0, 255, 255)
        bg_alpha = st.slider("Hintergrund Transparenz", 0, 255, 255)
        c_line = st.color_picker("Routenfarbe", "#8B0000")
        c_fill = st.color_picker("Farbe Profilfüllung", "#8B0000")

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
                from staticmap import StaticMap, Line
                w, h = 1080, 1920 
                m = StaticMap(w, h, url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png")
                m.add_line(Line(list(zip(lons, lats)), c_line, w_line))
                src_img = m.render().convert("RGB")

            base_img = Image.new('RGB', (w, h), "white")
            src_img_rgba = src_img.convert("RGBA")
            alpha_band = src_img_rgba.split()[3].point(lambda p: int(p * bg_alpha / 255))
            src_img_rgba.putalpha(alpha_band)
            base_img.paste(src_img_rgba, (0, 0), src_img_rgba)

            overlay = Image.new('RGBA', base_img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            
            rgb_route = tuple(int(c_line[1:3], 16) if i==0 else int(c_line[3:5], 16) if i==1 else int(c_line[5:7], 16) for i in range(3))
            rgb_fill = tuple(int(c_fill[1:3], 16) if i==0 else int(c_fill[3:5], 16) if i==1 else int(c_fill[5:7], 16) for i in range(3))
            
            bh_top, bh_bot = int(h * b_height_adj), int(h * (b_height_adj + 0.02))
            draw.rectangle([0, 0, w, bh_top], fill=(0, 0, 0, b_alpha))
            draw.rectangle([0, h - bh_bot, w, h], fill=(0, 0, 0, b_alpha))

            font_path = "font.ttf" if os.path.exists("font.ttf") else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            
            # --- HÖHENPROFIL (JETZT VOLLE BREITE) ---
            if show_profile and len(elevs) > 1:
                e_min, e_max = min(elevs), max(elevs)
                e_range = e_max - e_min if e_max > e_min else 1
                grid_y_start = h - bh_bot
                
                # Profil-Punkte über die gesamte Breite (w)
                profile_pts = [((i/len(elevs))*w, (h-bh_bot)+(bh_bot*0.85)-((ev-e_min)/e_range)*(bh_bot*0.7)) for i, ev in enumerate(elevs)]
                
                # 1. Raster (Hintergrund, kleinere Schrift)
                if show_grid:
                    # NEU: Rasterbeschriftung kleiner (0.018 statt 0.025)
                    try:
                        font_grid = ImageFont.truetype(font_path, max(12, int(w * 0.018 * font_scale)))
                    except: font_grid = ImageFont.load_default()
                    grid_color, grid_text_color = (255, 255, 255, 45), (255, 255, 255, 140)
                    
                    for i in range(1, 4):
                        gy = grid_y_start + i * (bh_bot / 4)
                        draw.line([(0, gy), (w, gy)], fill=grid_color, width=max(1, int(w*0.001)))
                        ev_val = e_min + ((grid_y_start + bh_bot*0.85 - gy) / (bh_bot*0.7)) * e_range
                        draw.text((w * 0.005, gy - 2), f"{int(ev_val)}m", fill=grid_text_color, font=font_grid, anchor="ld")
                    
                    for i in range(1, 8):
                        gx = i * (w / 8)
                        draw.line([(gx, grid_y_start), (gx, h)], fill=grid_color, width=max(1, int(w*0.001)))
                        draw.text((gx + 4, grid_y_start + 4), f"{int((i/8)*d_total)}km", fill=grid_text_color, font=font_grid, anchor="lt")

                # 2. Füllung
                if fill_profile:
                    draw.polygon(profile_pts + [(w, h), (0, h)], fill=rgb_fill + (int(r_alpha * 0.5),))
                
                # 3. Weiße Oberkante
                draw.line(profile_pts, fill=(255,255,255, r_alpha), width=max(3, int(w*0.003)), joint="round")

            # --- TEXTE & ICONS ---
            font_t = get_fitted_font(draw, tour_title, w * 0.9, int(w * 0.10 * font_scale), font_path)
            draw.text((w//2, bh_top//2), tour_title, fill="white", font=font_t, anchor="mm")

            txt_dist = f"{d_total:.1f}" + (" km" if show_units else "")
            txt_elev = f"{int(a_gain)}" + (" m" if show_units else "")
            
            icon_size = int(w * 0.055 * 1.3 * font_scale) 
            lw = max(3, int(icon_size * 0.08))
            curr_icon_w = icon_size if show_icons else 0
            
            font_d = get_fitted_font(draw, txt_dist + " " + txt_elev, (w * 0.85) - (2 * curr_icon_w) - (int(w * 0.15)), int(w * 0.055 * font_scale), font_path)
            
            w_d, w_e = draw.textlength(txt_dist, font=font_d), draw.textlength(txt_elev, font=font_d)
            spacing, i_gap = int(w * 0.15), int(w * 0.02) if show_icons else 0
            total_w = (curr_icon_w + i_gap + w_d) + spacing + (curr_icon_w + i_gap + w_e)
            sx, y_p = (w - total_w) // 2, h - int(bh_bot * 0.35)

            if show_icons:
                img_dist = Image.new('RGBA', (icon_size, icon_size), (0,0,0,0))
                d_i = ImageDraw.Draw(img_dist)
                d_i.arc([lw, lw, icon_size-lw, icon_size-lw], start=150, end=390, fill="white", width=lw)
                d_i.line([icon_size//2, icon_size//2, icon_size//2 + math.cos(math.radians(240))*icon_size*0.35, icon_size//2 + math.sin(math.radians(240))*icon_size*0.35], fill="white", width=lw)
                overlay.paste(img_dist, (int(sx), int(y_p - icon_size // 2)), img_dist)
                
                img_elev = Image.new('RGBA', (icon_size, icon_size), (0,0,0,0))
                d_e = ImageDraw.Draw(img_elev)
                d_e.polygon([(0, icon_size*0.9), (icon_size*0.4, icon_size*0.2), (icon_size*0.8, icon_size*0.9)], fill="white")
                d_e.line([(icon_size*0.9, icon_size*0.8), (icon_size*0.9, icon_size*0.1)], fill="white", width=lw)
                overlay.paste(img_elev, (int(sx + curr_icon_w + i_gap + w_d + spacing), int(y_p - icon_size // 2)), img_elev)

            draw.text((sx + curr_icon_w + i_gap, y_p), txt_dist, fill="white", font=font_d, anchor="lm")
            draw.text((sx + total_w - w_e, y_p), txt_elev, fill="white", font=font_d, anchor="lm")

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
