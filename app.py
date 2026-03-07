import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageChops
import io
import math
import os

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro XXL", page_icon="🏍️", layout="centered")

# PWA Meta-Tags für iOS und Android
st.markdown("""
    <head>
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="GPX Share">
    </head>
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
    .install-box {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ff0000;
        margin-top: 10px;
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

# --- UPLOAD ---
c_up1, c_up2 = st.columns(2)
with c_up1:
    up_gpx = st.file_uploader("📍 1. GPX Datei (Tour)")
    if up_gpx is not None:
        raw_name = up_gpx.name.rsplit('.', 1)[0]
        st.session_state.tour_name_val = raw_name.replace('_', ' ').replace('-', ' ')
with c_up2:
    up_img = st.file_uploader("📸 2. Foto wählen (Optional)", type=["jpg", "jpeg", "png"])

# --- OPTIONEN ---
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
        font_scale = st.slider("Titel-Skalierung", 0.5, 3.0, 1.5)
        data_font_scale = st.slider("Daten-Skalierung", 0.5, 3.0, 1.2)
        data_y_offset = st.slider("Vertikaler Abstand Daten", 0, 300, 160)
        # NEU: Slider für den vertikalen Versatz der Route
        route_y_offset = st.slider("Vertikaler Versatz Route", -500, 500, 0)
        b_height_adj = st.slider("Balken Dicke", 0.05, 0.50, 0.20)
        w_line = st.slider("Linienstärke Route", 1, 100, 9)
        b_alpha = st.slider("Balken Deckkraft", 0, 255, 160)
        r_alpha = st.slider("Routen-Transparenz", 0, 255, 255)
        bg_alpha = st.slider("Hintergrund Transparenz", 0, 255, 255)
        c_line = st.color_picker("Routenfarbe", "#8B0000")
        c_fill = st.color_picker("Farbe Profilfüllung", "#8B0000")
        c_box = st.color_picker("Farbe Infoboxen", "#000000")

# --- ÜBER REITER ---
with st.expander("ℹ️ Über GPX Share Pro", expanded=False):
    c_logo, c_meta = st.columns([1, 3])
    with c_logo:
        if os.path.exists("logo.png"): st.image("logo.png", width=100)
    with c_meta:
        st.markdown("### GPX Share Pro XXL\n**Copyright: Jürgen Unterweger**\n**Version: 1.0**")
        paypal_url = "https://www.paypal.com/donate?hosted_button_id=FF6FBUE84V7MG"
        st.markdown(f'<a href="{paypal_url}" target="_blank"><img src="https://www.paypalobjects.com/de_DE/i/btn/btn_donateCC_LG.gif" alt="PayPal" style="width:120px; margin-top:10px;"></a>', unsafe_allow_html=True)
        st.markdown(f'<a href="{paypal_url}" target="_blank" style="text-decoration:none; color:#8b0000; font-weight:bold;">meine Arbeit unterstützen</a>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**Folge mir auf meinen Kanälen:**")
    col_ig, col_fb = st.columns(2)
    with col_ig: st.markdown(f"📸 [Instagram: juergen_rocks](https://www.instagram.com/juergen_rocks/)")
    with col_fb: st.markdown(f"👥 [Facebook: JuergenRocks](https://www.facebook.com/JuergenRocks/)")
    st.markdown("---")
    st.markdown("**App teilen:**")
    app_url = "https://gpx-share-oh4dfakuqvfxadxmg3qhhq.streamlit.app/"
    col_qr, col_link = st.columns([1, 2])
    with col_qr:
        st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={app_url}", width=120)
    with col_link: st.code(app_url, language=None)

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
            if up_img:
                src_img = Image.open(up_img).convert("RGB")
                w, h = src_img.size
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
            rgb_box = tuple(int(c_box[1:3], 16) if i==0 else int(c_box[3:5], 16) if i==1 else int(c_box[5:7], 16) for i in range(3))
            
            bh_top, bh_bot = int(h * b_height_adj), int(h * 0.12)
            draw.rectangle([0, 0, w, bh_top], fill=rgb_box + (b_alpha,))
            draw.rectangle([0, h - bh_bot, w, h], fill=rgb_box + (b_alpha,))

            font_path = "font.ttf" if os.path.exists("font.ttf") else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            
            # --- EIGENES LOGO ---
            if show_logo and os.path.exists("logo.png"):
                logo_img = Image.open("logo.png").convert("RGBA")
                l_w = int(w * 0.12)
                l_h = int(logo_img.height * (l_w / logo_img.width))
                logo_img = logo_img.resize((l_w, l_h), Image.Resampling.LANCZOS)
                overlay.paste(logo_img, (w - l_w - int(w*0.03), int(bh_top*0.1)), logo_img)

            # --- HÖHENPROFIL ---
            if show_profile and len(elevs) > 1:
                e_min, e_max = min(elevs), max(elevs)
                e_range = e_max - e_min if e_max > e_min else 1
                grid_y_start = h - bh_bot
                profile_pts = [((i/len(elevs))*w, (h-bh_bot)+(bh_bot*0.85)-((ev-e_min)/e_range)*(bh_bot*0.7)) for i, ev in enumerate(elevs)]
                if fill_profile: draw.polygon(profile_pts + [(w, h), (0, h)], fill=rgb_fill + (int(r_alpha * 0.5),))
                if show_grid:
                    try: font_grid = ImageFont.truetype(font_path, max(12, int(w * 0.018 * font_scale)))
                    except: font_grid = ImageFont.load_default()
                    grid_color = (255, 255, 255, 45)
                    for i in range(1, 4):
                        gy = grid_y_start + i * (bh_bot / 4)
                        draw.line([(0, gy), (w, gy)], fill=grid_color, width=max(1, int(w*0.001)))
                        ev_val = e_min + ((grid_y_start + bh_bot*0.85 - gy) / (bh_bot*0.7)) * e_range
                        draw.text((w * 0.005, gy - 2), f"{int(ev_val)}m", fill=(255,255,255,140), font=font_grid, anchor="ld")
                    for i in range(1, 8):
                        gx = i * (w / 8)
                        draw.line([(gx, grid_y_start), (gx, h)], fill=grid_color, width=max(1, int(w*0.001)))
                        draw.text((gx + 4, grid_y_start + 4), f"{int((i/8)*d_total)}km", fill=(255,255,255,140), font=font_grid, anchor="lt")
                draw.line(profile_pts, fill=(255,255,255, r_alpha), width=max(3, int(w*0.003)), joint="round")

            # --- ROUTE (MIT VERTIAKLER POSITIONIERUNG) ---
            if pts:
                mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
                margin = 0.20
                scaled = [(w*margin + (lon-mi_lo)/(ma_lo-mi_lo)*w*(1-2*margin), 
                           (h*(1-margin) - (lat-mi_la)/(ma_la-mi_la)*h*(1-2*margin)) + route_y_offset) # Offset angewendet
                          for lat, lon in pts]
                draw.line(scaled, fill=rgb_route + (r_alpha,), width=w_line, joint="round")

            title_y = int(bh_top * 0.35)
            font_t = get_fitted_font(draw, tour_title, w * 0.9, int(w * 0.085 * font_scale), font_path)
            draw.text((w//2, title_y), tour_title, fill="white", font=font_t, anchor="mm")
            txt_dist = f"{d_total:.1f}" + (" km" if show_units else "")
            txt_elev = f"{int(a_gain)}" + (" m" if show_units else "")
            icon_size = int(w * 0.055 * 1.3 * data_font_scale) 
            font_d = get_fitted_font(draw, txt_dist + " " + txt_elev, w * 0.7, int(w * 0.055 * data_font_scale), font_path)
            w_d, w_e = draw.textlength(txt_dist, font=font_d), draw.textlength(txt_elev, font=font_d)
            spacing, i_gap = int(w * 0.15), int(w * 0.02) if show_icons else 0
            total_w = (icon_size if show_icons else 0) + i_gap + w_d + spacing + (icon_size if show_icons else 0) + i_gap + w_e
            sx, data_y = (w - total_w) // 2, title_y + data_y_offset 
            
            if show_icons:
                i_y = int(data_y - icon_size // 2)
                draw.arc([sx, i_y, sx+icon_size, i_y+icon_size], 150, 390, fill="white", width=max(2, int(icon_size*0.08)))
                draw.text((sx + icon_size + i_gap, data_y), txt_dist, fill="white", font=font_d, anchor="lm")
                ex = sx + icon_size + i_gap + w_d + spacing
                draw.polygon([(ex, i_y+icon_size*0.9), (ex+icon_size*0.4, i_y+icon_size*0.2), (ex+icon_size*0.8, i_y+icon_size*0.9)], fill="white")
                draw.text((ex + icon_size + i_gap, data_y), txt_elev, fill="white", font=font_d, anchor="lm")
            else:
                draw.text((sx, data_y), txt_dist, fill="white", font=font_d, anchor="lm")
                draw.text((sx + w_d + spacing, data_y), txt_elev, fill="white", font=font_d, anchor="lm")

            final = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
            st.image(final, use_container_width=True)
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), "ride_pro_final.jpg", "image/jpeg")
    except Exception as e: st.error(f"Fehler: {e}")
