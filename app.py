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
        text-align: center; margin-bottom: 30px;
    }
    .stDownloadButton button {
        width: 100%; border-radius: 20px;
        background: linear-gradient(135deg, #ff0000 0%, #8b0000 100%) !important;
        color: white !important; font-weight: bold; border: none; height: 3em;
    }
    </style>
    """, unsafe_allow_html=True)

def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# --- SIDEBAR ---
with st.sidebar:
    # --- APP LOGO INTEGRATION ---
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("<h1 style='color: #ff0000;'>⚙️ Design-Setup</h1>", unsafe_allow_html=True)
    tour_title = st.text_input("Tour Name", value="Meine Tour")
    st.divider()
    
    # HIER IST DIE ÄNDERUNG: value=False gesetzt
    show_logo = st.checkbox("Zeige eigenes Logo auf Foto", value=False)
    logo_radius = st.slider("Logo-Ecken abrunden (Radius)", 0, 100, 20)
    st.divider()

    font_scale = st.slider("Schrift-Skalierung", 0.5, 3.0, 1.2)
    b_height_adj = st.slider("Balken Dicke", 0.05, 0.40, 0.15)
    st.divider()
    c_line = st.color_picker("Routenfarbe", "#8B0000")
    w_line = st.slider("Linienstärke Route", 1, 100, 9)
    b_alpha = st.slider("Balken Deckkraft", 0, 255, 210)

# --- HAUPTBEREICH ---
st.markdown("<p class='title-modern'>GPX Share Pro</p>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    up_img = st.file_uploader("📸 1. Foto wählen", type=["jpg", "jpeg", "png"])
with c2:
    up_gpx = st.file_uploader("📍 2. GPX Datei (Tour)")

if up_img and up_gpx:
    try:
        base_img = Image.open(up_img).convert("RGB")
        w, h = base_img.size
        
        auto_f_title = int(w * 0.08 * font_scale)
        auto_f_data = int(w * 0.045 * font_scale)

        up_gpx.seek(0)
        gpx = gpxpy.parse(up_gpx.read().decode("utf-8", errors="ignore"))
        
        pts, elevs = [], []
        d_total, a_gain = 0.0, 0.0
        last = None
        last_elev = None
        
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
            overlay = Image.new('RGBA', base_img.size, (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            rgb = tuple(int(c_line[1:3], 16) if i==0 else int(c_line[3:5], 16) if i==1 else int(c_line[5:7], 16) for i in range(3))

            bh_top = int(h * b_height_adj)
            bh_bot = int(h * (b_height_adj + 0.02))
            draw.rectangle([0, 0, w, bh_top], fill=(0, 0, 0, b_alpha))
            draw.rectangle([0, h - bh_bot, w, h], fill=(0, 0, 0, b_alpha))

            font_path = "font.ttf" if os.path.exists("font.ttf") else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            try:
                font_t = ImageFont.truetype(font_path, auto_f_title)
                font_d = ImageFont.truetype(font_path, auto_f_data)
                font_grid = ImageFont.truetype(font_path, max(10, int(auto_f_data * 0.35))) 
            except:
                font_t = font_d = font_grid = ImageFont.load_default()

            if len(elevs) > 1:
                e_min, e_max = min(elevs), max(elevs)
                e_range = e_max - e_min if e_max > e_min else 1
                grid_color = (255, 255, 255, 40) 
                grid_text_color = (255, 255, 255, 140) 
                grid_y_start = h - bh_bot
                for i in range(1, 4):
                    gy = grid_y_start + i * (bh_bot / 4)
                    draw.line([(0, gy), (w, gy)], fill=grid_color, width=max(1, int(w*0.001)))
                    ev_val = e_min + ((h - bh_bot + bh_bot*0.85 - gy) / (bh_bot*0.7)) * e_range
                    draw.text((w * 0.005, gy - 2), f"{int(ev_val)} m", fill=grid_text_color, font=font_grid, anchor="ld")
                for i in range(1, 8):
                    gx = i * (w / 8)
                    draw.line([(gx, grid_y_start), (gx, h)], fill=grid_color, width=max(1, int(w*0.001)))
                    dist_val = (i / 8.0) * d_total
                    draw.text((gx + 4, grid_y_start + 4), f"{dist_val:.1f} km", fill=grid_text_color, font=font_grid, anchor="lt")
                profile_pts = [((i/len(elevs))*w, (h-bh_bot)+(bh_bot*0.85)-((ev-e_min)/e_range)*(bh_bot*0.7)) for i, ev in enumerate(elevs)]
                draw.polygon(profile_pts + [(w, h), (0, h)], fill=rgb + (160,))
                draw.line(profile_pts, fill="white", width=max(3, int(w*0.003)), joint="round")

            icon_size = int(auto_f_data * 1.5)
            lw = max(3, int(icon_size * 0.08)) 
            img_dist = Image.new('RGBA', (icon_size, icon_size), (0,0,0,0))
            d_dist = ImageDraw.Draw(img_dist)
            ry = icon_size * 0.85
            d_dist.line([(0, ry), (icon_size, ry)], fill="white", width=lw) 
            for i in range(5):
                x = i * (icon_size / 4)
                d_dist.line([(x, ry), (x, ry - icon_size*0.15)], fill="white", width=lw) 
            cx, cy = icon_size * 0.5, icon_size * 0.65
            d_dist.line([(cx, cy), (cx, icon_size*0.15)], fill="white", width=lw) 
            d_dist.polygon([(cx, 0), (cx-icon_size*0.15, icon_size*0.2), (cx+icon_size*0.15, icon_size*0.2)], fill="white")
            d_dist.line([(cx, cy), (icon_size*0.2, icon_size*0.4)], fill="white", width=lw) 
            d_dist.polygon([(0, icon_size*0.4), (icon_size*0.2, icon_size*0.25), (icon_size*0.25, icon_size*0.5)], fill="white")
            d_dist.line([(cx, cy), (icon_size*0.8, icon_size*0.4)], fill="white", width=lw) 
            d_dist.polygon([(icon_size, icon_size*0.4), (icon_size*0.8, icon_size*0.25), (icon_size*0.75, icon_size*0.5)], fill="white")
            
            img_elev = Image.new('RGBA', (icon_size, icon_size), (0,0,0,0))
            d_elev = ImageDraw.Draw(img_elev)
            d_elev.polygon([(0, icon_size*0.85), (icon_size*0.35, icon_size*0.2), (icon_size*0.7, icon_size*0.85)], fill="white") 
            d_elev.polygon([(icon_size*0.4, icon_size*0.85), (icon_size*0.65, icon_size*0.4), (icon_size*0.9, icon_size*0.85)], fill="white") 
            ax = icon_size * 0.9
            d_elev.line([(ax, icon_size*0.8), (ax, icon_size*0.1)], fill="white", width=lw) 
            d_elev.polygon([(ax, 0), (ax-icon_size*0.15, icon_size*0.2), (ax+icon_size*0.15, icon_size*0.2)], fill="white")
            
            draw.text((w//2, bh_top//2), tour_title, fill="white", font=font_t, anchor="mm")
            txt_dist = f"{d_total:.1f} km"
            txt_elev = f"{int(a_gain)} m"
            w_dist = draw.textlength(txt_dist, font=font_d)
            w_elev = draw.textlength(txt_elev, font=font_d)
            spacing = int(w * 0.1) 
            total_w = icon_size + 20 + w_dist + spacing + icon_size + 20 + w_elev
            start_x = (w - total_w) // 2
            y_pos = h - bh_bot // 2
            
            overlay.paste(img_dist, (int(start_x), int(y_pos - icon_size // 2)), img_dist)
            draw.text((start_x + icon_size + 20, y_pos), txt_dist, fill="white", font=font_d, anchor="lm")
            x_elev = start_x + icon_size + 20 + w_dist + spacing
            overlay.paste(img_elev, (int(x_elev), int(y_pos - icon_size // 2)), img_elev)
            draw.text((x_elev + icon_size + 20, y_pos), txt_elev, fill="white", font=font_d, anchor="lm")
            
            lats, lons = zip(*pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            margin = 0.20
            scaled_pts = [(w*margin + (lon-mi_lo)/(ma_lo-mi_lo)*w*(1-2*margin), 
                           h*(1-margin) - (lat-mi_la)/(ma_la-mi_la)*h*(1-2*margin)) for lat, lon in pts]
            draw.line(scaled_pts, fill=rgb + (255,), width=w_line, joint="round")
            
            if len(scaled_pts) > 1:
                point_size = max(6, int(w * 0.008)) 
                start = scaled_pts[0]
                draw.ellipse([start[0]-point_size, start[1]-point_size, start[0]+point_size, start[1]+point_size], fill="white")
                end = scaled_pts[-1]
                draw.ellipse([end[0]-point_size, end[1]-point_size, end[0]+point_size, end[1]+point_size], fill=c_line)

            # --- EIGENES LOGO SAUBER ABRUNDEN (FÜR DAS FOTO) ---
            if show_logo and os.path.exists("logo.png"):
                try:
                    user_logo = Image.open("logo.png").convert("RGBA")
                    max_logo_h = int(h * 0.10)
                    l_w, l_h = user_logo.size
                    ratio = max_logo_h / l_h
                    new_size = (int(l_w * ratio), int(l_h * ratio))
                    user_logo = user_logo.resize(new_size, Image.LANCZOS)
                    
                    radius = int(new_size[1] * (logo_radius / 200)) 
                    if radius > 0:
                        mask = Image.new('L', new_size, 0)
                        d_mask = ImageDraw.Draw(mask)
                        d_mask.rounded_rectangle([0, 0, new_size[0], new_size[1]], fill=255, radius=radius)
                        
                        if 'A' in user_logo.getbands():
                            alpha = user_logo.split()[3]
                            mask = ImageChops.darker(mask, alpha)
                        user_logo.putalpha(mask)

                    padding = int(w * 0.02)
                    logo_x = w - new_size[0] - padding
                    logo_y = (h - bh_bot) - new_size[1] - padding
                    
                    overlay.paste(user_logo, (logo_x, logo_y), user_logo)
                except Exception as e:
                    st.warning(f"Konnte Logo im Bild nicht einfügen: {e}")

            final = Image.alpha_composite(base_img.convert('RGBA'), overlay).convert('RGB')
            st.image(final, use_container_width=True)
            
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), "ride_pro_final.jpg", "image/jpeg")

    except Exception as e:
        st.error(f"Fehler: {e}")
