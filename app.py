import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import math
import os

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro XXL", page_icon="🏍️", layout="centered")

# --- STANDARDWERTE (v2.7.35: Distinct Distance Icon Fix) ---
DEFAULTS = {
    "tour_title": "Meine Tour",
    "tour_date": "",
    "c_line": "#8B0000",
    "c_title": "#FFFFFF",
    "c_date": "#FFFFFF",
    "c_data": "#FFFFFF",
    "c_grid": "#FFFFFF",
    "w_line": 9,
    "show_markers": True,
    "show_speed": True,
    "show_profile": True,
    "show_logo": False,
    "show_route": False,
    "show_minibox": True,
    "logo_type": "Grafik",
    "show_date": True,
    "auto_intervals": True,
    "grid_m_interval": 250,
    "grid_km_interval": 10,
    "bg_opacity": 100,
    "size_title": 1.5,
    "size_date": 1.0,
    "size_data": 1.0,
    "size_grid": 1.0,
    "size_logo": 1.0,
    "size_minibox": 1.0
}

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

if "last_gpx_file" not in st.session_state:
    st.session_state.last_gpx_file = ""

# --- HELFER FUNKTIONEN ---
def reset_parameters():
    for key, val in DEFAULTS.items():
        st.session_state[key] = val

def load_font(size):
    size = max(10, int(size))
    paths = ["font.ttf", "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for p in paths:
        try: return ImageFont.truetype(p, size)
        except: continue
    return ImageFont.load_default()

def validate_coords(coords):
    return [min(coords[0], coords[2]), min(coords[1], coords[3]), max(coords[0], coords[2]) + 1, max(coords[1], coords[3]) + 1]

def safe_rect(draw, coords, fill=None, outline=None, width=1):
    try: draw.rectangle(validate_coords(coords), fill=fill, outline=outline, width=int(width))
    except: pass

def safe_ellipse(draw, coords, fill=None, outline=None, width=1):
    try: draw.ellipse(validate_coords(coords), fill=fill, outline=outline, width=int(width))
    except: pass

def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def draw_text_with_shadow(draw, pos, text, font, fill="white", shadow_color="black", offset=2, anchor="mm"):
    x, y = int(pos[0]), int(pos[1])
    draw.text((x+offset, y+offset), text, fill=shadow_color, font=font, anchor=anchor)
    draw.text((x, y), text, fill=fill, font=font, anchor=anchor)

def draw_marker(draw, pos, color, label=""):
    x, y = pos
    r = 14
    safe_ellipse(draw, [x-r-2, y-r-2, x+r+2, y+r+2], fill="white")
    safe_ellipse(draw, [x-r, y-r, x+r, y+r], fill=color, outline="black", width=2)
    if label:
        f = load_font(16)
        draw.text((int(x), int(y)), label, fill="white", font=f, anchor="mm")

# --- ICON ZEICHNEN FIX ---
def draw_data_icon(mode, size, color="white"):
    res = 4
    size = int(max(10, size))
    img = Image.new('RGBA', (size*res, size*res), (0,0,0,0))
    d = ImageDraw.Draw(img)
    lw = int(max(2, size*res*0.08))
    x0, y0, x1, y1 = lw, lw, size*res - lw, size*res - lw
    
    if mode == "dist":
        # NEU: Distanz Icon als Pfad/Wegstrecke
        d.line([(x0, y1-lw), (x1//2, y1-lw), (x1//2, y0+lw), (x1, y0+lw)], fill=color, width=lw, joint="round")
        d.ellipse([x0-lw, y1-2*lw, x0+lw, y1], fill=color) # Startpunkt
        d.ellipse([x1-lw, y0, x1+lw, y0+2*lw], fill=color) # Zielpunkt
    elif mode == "elev":
        d.polygon([(lw, y1), (size*res//2, y0), (x1, y1)], fill=color)
    elif mode == "speed": 
        # Bleibt Tacho für Geschwindigkeit
        d.arc([x0, y0, x1, y1], 150, 390, fill=color, width=lw)
        cx, cy = size*res//2, size*res//2 + lw
        d.line([cx, cy, cx + size*res*0.25, cy - size*res*0.25], fill=color, width=lw)
        d.ellipse([cx-lw, cy-lw, cx+lw, cy+lw], fill=color)
    return img.resize((size, size), Image.Resampling.LANCZOS)

def draw_graphical_logo(draw, pos, scale=1.0, color="#8B0000"):
    x, y = int(pos[0]), int(pos[1])
    icon_size = int(50 * scale)
    rgb = hex_to_rgba(color)
    safe_ellipse(draw, [x, y, x + icon_size, y + icon_size], fill=rgb, outline="white", width=max(1, int(2*scale)))
    draw.polygon([(x+icon_size*0.2, y+icon_size*0.75), (x+icon_size*0.5, y+icon_size*0.25), (x+icon_size*0.8, y+icon_size*0.75)], fill="white")
    draw_text_with_shadow(draw, (x + icon_size + int(15*scale), y + icon_size//2), "GPX Share Pro", load_font(int(32 * scale)), fill="white", anchor="lm")

def hex_to_rgba(hex_color, alpha=255):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)

def get_logo_path():
    for name in ["logo.png", "Logo.png", "LOGO.png"]:
        if os.path.exists(name): return name
    return None

# --- APP-HEADER UI ---
st.markdown("""
<style>
.stApp { background-color: #ffffff; color: #000000; } 
.header-box {
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #111111 0%, #2a2a2a 100%);
    padding: 20px; border-radius: 15px; box-shadow: 0px 10px 20px rgba(139, 0, 0, 0.4);
    margin-bottom: 30px; border: 1px solid #333;
}
.header-title {
    font-size: 38px; font-weight: 900;
    background: linear-gradient(90deg, #ff4b4b 0%, #8b0000 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0; text-transform: uppercase; text-align: center;
}
.social-btn { display: inline-block; padding: 10px 20px; border-radius: 5px; color: white !important; text-decoration: none; font-weight: bold; text-align: center; } 
.wa-btn { background-color: #25D366; }
</style>
<div class="header-box"><p class="header-title">GPX Share Pro XXL</p></div>
""", unsafe_allow_html=True)

# --- UPLOADS ---
c_up1, c_up2 = st.columns(2)
with c_up1:
    st.markdown("### 📍 1. GPX Datei wählen")
    up_gpx = st.file_uploader("GPX Upload", label_visibility="collapsed", key="gpx_uploader")
    if up_gpx:
        if st.session_state.last_gpx_file != up_gpx.name:
            st.session_state.last_gpx_file = up_gpx.name
            st.session_state.tour_title = up_gpx.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
            try:
                g = gpxpy.parse(io.BytesIO(up_gpx.getvalue()))
                d = g.time.strftime("%d.%m.%Y") if g.time else ""
                if not d:
                    for p in [p for t in g.tracks for s in t.segments for p in s.points if p.time]:
                        d = p.time.strftime("%d.%m.%Y"); break
                if d: st.session_state.tour_date = d
            except: pass
            st.rerun()

with c_up2:
    st.markdown("### 📸 2. Foto wählen")
    up_img = st.file_uploader("Foto Upload", type=["jpg", "jpeg", "png"], label_visibility="collapsed", key="img_uploader")

# --- OPTIONEN ---
with st.expander("⚙️ Einstellungen [v2.7.35]", expanded=False): 
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        st.write("**📝 Tour & Design**")
        st.text_input("2. Tour Name", key="tour_title")
        st.text_input("3. Datum", key="tour_date")
        c_c1, c_c2 = st.columns(2)
        with c_c1: st.color_picker("1a. Routenfarbe", key="c_line")
        with c_c2: st.number_input("1b. Routenstärke", 1, 20, key="w_line")
        st.number_input("8. Hintergrund Dimmer (%)", 0, 100, key="bg_opacity")
        st.write("**🔠 Texte & Größen**")
        cs, cc = st.columns(2)
        with cs:
            st.number_input("Größe Titel", 0.5, 4.0, key="size_title", step=0.1)
            st.number_input("Größe Daten", 0.5, 4.0, key="size_data", step=0.1)
            st.number_input("Größe Logo", 0.5, 3.0, key="size_logo", step=0.1)
            st.number_input("Größe Minibox", 0.5, 2.0, key="size_minibox", step=0.1)
        with cc:
            st.color_picker("Farbe Titel", key="c_title")
            st.color_picker("Farbe Daten", key="c_data")
            st.color_picker("Farbe Datum", key="c_date")
            st.color_picker("Farbe Raster", key="c_grid")

    with col_opt2:
        st.write("**✅ Ein- / Ausblenden**")
        st.checkbox("4. Start/Ziel (S/Z)", key="show_markers")
        st.checkbox("5. Ø Geschwindigkeit", key="show_speed")
        st.checkbox("6. Höhenprofil", key="show_profile")
        st.checkbox("7. App Logo (Im Bild)", key="show_logo")
        st.checkbox("8. Route in Bild anzeigen", key="show_route")
        st.checkbox("9. Minibox (Karte)", key="show_minibox")
        st.checkbox("Datum anzeigen", key="show_date")
        
        st.write("**📏 Raster & Intervalle**")
        st.checkbox("Auto-Intervalle nutzen", key="auto_intervals")
        if not st.session_state.auto_intervals:
            st.number_input("Meter-Intervalle (m)", 50, 5000, key="grid_m_interval", step=50)
            st.number_input("KM-Intervalle (km)", 1, 500, key="grid_km_interval", step=5)
            
        st.button("🔄 Alles zurücksetzen", on_click=reset_parameters)

# --- INFO REITER ---
with st.expander("ℹ️ Über GPX Share Pro", expanded=False):
    if st.session_state.logo_type == "Grafik":
        menu_logo = Image.new('RGBA', (400, 100), (30, 30, 30, 255))
        draw_graphical_logo(ImageDraw.Draw(menu_logo), (20, 25), scale=1.0, color=st.session_state.c_line)
        st.image(menu_logo, use_container_width=False)
    else:
        logo_file = get_logo_path()
        if logo_file: st.image(logo_file, width=250)
        else: st.warning("⚠️ 'logo.png' nicht gefunden.")
    
    st.markdown("### 📜 Changelog")
    st.info("**v2.7.35 (Aktuell):**\n- Distanz-Icon korrigiert (eigenes Pfad-Symbol).\n- Durchschnittsgeschwindigkeit behält Tacho-Icon.")
    
    st.markdown("---")
    st.markdown("**Copyright: Jürgen Unterweger**")
    st.markdown(f'<a href="https://www.paypal.com/donate?hosted_button_id=FF6FBUE84V7MG" target="_blank"><img src="https://www.paypalobjects.com/de_DE/i/btn/btn_donateCC_LG.gif" width="120"></a>', unsafe_allow_html=True)
    
    app_url = "https://gpx-share-oh4dfakuqvfxadxmg3qhhq.streamlit.app/"
    raw_msg = f"Hey! Schau dir mal diese geniale App zum teilen deiner Motorrad-Touren an: {app_url}"
    share_link = "whatsapp://send?text=" + raw_msg.replace(" ", "%20")
    st.markdown(f'<a href="{share_link}" class="social-btn wa-btn" style="display: block; width: 100%; margin-top: 15px;">🚀 App empfehlen (WhatsApp)</a>', unsafe_allow_html=True)

st.divider()

# --- VERARBEITUNG & BILDERZEUGUNG ---
if up_gpx:
    try:
        gpx = gpxpy.parse(io.BytesIO(up_gpx.getvalue()))
        pts, elevs = [], []
        d_total, a_gain, total_time = 0.0, 0.0, 0.0
        l_p, l_e, l_t = None, None, None
        for seg in gpx.tracks[0].segments:
            s_pts = []
            for p in seg.points:
                s_pts.append([p.latitude, p.longitude])
                elevs.append(p.elevation or 0)
                if l_p:
                    d_total += calc_dist(l_p[0], l_p[1], p.latitude, p.longitude)
                    if p.elevation and l_e and p.elevation > l_e: a_gain += (p.elevation - l_e)
                    if p.time and l_t:
                        dt = (p.time - l_t).total_seconds()
                        if 0 < dt < 1800: total_time += dt
                l_p, l_e, l_t = [p.latitude, p.longitude], p.elevation, p.time
            if s_pts: pts.append(s_pts)

        avg_s = d_total / (total_time / 3600.0) if total_time > 0 else 0.0
        w, h = 1080, 1920
        canvas = Image.new('RGBA', (w, h), (30, 30, 30, 255))
        if up_img:
            bg = ImageOps.exif_transpose(Image.open(io.BytesIO(up_img.getvalue()))).convert("RGBA")
            canvas.paste(ImageOps.fit(bg, (w, h), Image.Resampling.LANCZOS), (0, 0))
        if st.session_state.bg_opacity < 100:
            canvas = Image.blend(Image.new('RGBA', (w, h), (255, 255, 255, 255)), canvas, st.session_state.bg_opacity / 100)

        overlay = Image.new('RGBA', (w, h), (0,0,0,0))
        draw = ImageDraw.Draw(overlay)
        bh_t, bh_b = int(h * 0.20), int(h * 0.12)
        safe_rect(draw, [0, 0, w, bh_t], fill=(0, 0, 0, 160))
        safe_rect(draw, [0, h - bh_b, w, h], fill=(0, 0, 0, 160))

        if st.session_state.show_profile and len(elevs) > 1:
            e_min, e_max = min(elevs), max(elevs)
            e_r = (e_max - e_min) or 1
            px_m, p_w = 10, w - 20 
            grid_y_start = h - bh_b
            
            if st.session_state.auto_intervals:
                step_km = 1 if d_total < 10 else 5 if d_total < 50 else 10 if d_total < 100 else 20 if d_total < 250 else 50
                step_m = 50 if e_r < 200 else 100 if e_r < 500 else 250 if e_r < 1500 else 500
            else:
                step_km = st.session_state.grid_km_interval
                step_m = st.session_state.grid_m_interval
            
            f_grid = load_font(int(w * 0.025 * st.session_state.size_grid))
            c_grid_transp = hex_to_rgba(st.session_state.c_grid, 160)
            c_grid_lines = hex_to_rgba(st.session_state.c_grid, 50)
            
            for m_val in range(int(e_min // step_m + 1) * step_m, int(e_max), step_m):
                gy = int((h-bh_b)+(bh_b*0.85)-((m_val-e_min)/e_r)*(bh_b*0.7))
                draw.line([(px_m, gy), (w - px_m, gy)], fill=c_grid_lines, width=1)
                
            last_text_end = -100 
            for k in range(step_km, int(d_total), step_km):
                gx = int(px_m + (k / d_total) * p_w if d_total > 0 else 0)
                draw.line([(gx, grid_y_start), (gx, h)], fill=c_grid_lines, width=1)
                text_str = f"{k}km"
                tw = draw.textlength(text_str, font=f_grid)
                if gx - tw/2 > last_text_end + 20:
                    draw.text((int(gx), int(grid_y_start+5)), text_str, fill=c_grid_transp, font=f_grid, anchor="mt")
                    last_text_end = gx + tw/2

            profile_pts = [(px_m + (i/max(1, len(elevs)-1))*p_w, (h-bh_b)+(bh_b*0.85)-((ev-e_min)/e_r)*(bh_b*0.7)) for i, ev in enumerate(elevs)]
            rgb = hex_to_rgba(st.session_state.c_line)
            draw.polygon(profile_pts + [(w-px_m, h), (px_m, h)], fill=rgb[:3] + (120,))
            draw.line(profile_pts, fill=(255,255,255,255), width=4)

        draw_text_with_shadow(draw, (w//2, bh_t*0.35), st.session_state.tour_title, load_font(int(w*0.08*st.session_state.size_title)), fill=st.session_state.c_title)
        items = [("dist", f"{d_total:.1f} km"), ("speed", f"{avg_s:.1f} km/h"), ("elev", f"{int(a_gain)} m")]
        f_d, i_s = load_font(int(w*0.05*st.session_state.size_data)), int(w*0.05*st.session_state.size_data)
        tw_tot = sum([i_s + 15 + draw.textlength(txt, f_d) for _, txt in items]) + (w*0.08)*2
        cx, dy = (w - tw_tot) // 2, bh_t*0.35 + 150
        for m, t in items:
            overlay.paste(draw_data_icon(m, i_s, st.session_state.c_data), (int(cx), int(dy-i_s//2)), draw_data_icon(m, i_s, st.session_state.c_data))
            cx += i_s + 15
            draw_text_with_shadow(draw, (cx + draw.textlength(t, f_d)//2, dy), t, f_d, fill=st.session_state.c_data)
            cx += draw.textlength(t, f_d) + w*0.08

        if st.session_state.show_date and st.session_state.tour_date:
            f_date = load_font(int(w * 0.028 * st.session_state.size_date))
            tw = draw.textlength(st.session_state.tour_date, font=f_date)
            bx1, by1 = 30, int(h - bh_b - 80)
            bx2, by2 = int(30 + tw + 40), int(h - bh_b - 20)
            safe_rect(draw, [bx1, by1, bx2, by2], fill=(0,0,0,160), outline=st.session_state.c_date, width=2)
            draw.text(((bx1+bx2)//2, (by1+by2)//2 + 2), st.session_state.tour_date, fill=st.session_state.c_date, font=f_date, anchor="mm")

        all_pts = [p for s in pts for p in s]
        if all_pts:
            lats, lons = zip(*all_pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            la_e, lo_e = (ma_la-mi_la) or 0.001, (ma_lo-mi_lo) or 0.001
            if st.session_state.show_route:
                ssf = 3
                ro = Image.new('RGBA', (w*ssf, h*ssf), (0,0,0,0))
                rd = ImageDraw.Draw(ro)
                rgb = hex_to_rgba(st.session_state.c_line)
                for s in pts:
                    s_pts = [(int((0.15*w + (p[1]-mi_lo)/lo_e*w*0.7) * ssf), int((h*0.75 - (p[0]-mi_la)/la_e*h*0.5) * ssf)) for p in s]
                    if len(s_pts)>1: rd.line(s_pts, fill=rgb[:3]+(255,), width=st.session_state.w_line*ssf, joint="round")
                overlay.paste(ro.resize((w, h), Image.Resampling.LANCZOS), (0,0), ro.resize((w, h), Image.Resampling.LANCZOS))
                if st.session_state.show_markers:
                    def tr(la, lo): return (int(0.15*w + (lo-mi_lo)/lo_e*w*0.7), int(h*0.75 - (la-mi_la)/la_e*h*0.5))
                    draw_marker(draw, tr(all_pts[0][0], all_pts[0][1]), "green", "S")
                    draw_marker(draw, tr(all_pts[-1][0], all_pts[-1][1]), "red", "Z")

        if st.session_state.show_minibox and all_pts:
            base_size = 280
            mb_w = int(base_size * st.session_state.size_minibox)
            mb_h = mb_w
            mb_x, mb_y = w - mb_w - 30, h - bh_b - mb_h - 30
            safe_rect(draw, [mb_x, mb_y, mb_x+mb_w, mb_y+mb_h], fill=(0,0,0,180), outline="white", width=2)
            m_m, m_la_e, m_lo_e = int(20 * st.session_state.size_minibox), (ma_la-mi_la) or 0.001, (ma_lo-mi_lo) or 0.001
            aspect = m_la_e / m_lo_e
            if aspect > 1: drw_h = mb_h - 2*m_m; drw_w = drw_h / aspect
            else: drw_w = mb_w - 2*m_m; drw_h = drw_w * aspect
            off_x, off_y = mb_x + (mb_w - drw_w)//2, mb_y + (mb_h - drw_h)//2
            rgb = hex_to_rgba(st.session_state.c_line)
            for s in pts:
                m_pts = [(int(off_x + (p[1]-mi_lo)/m_lo_e*drw_w), int(off_y + drw_h - (p[0]-mi_la)/m_la_e*drw_h)) for p in s]
                if len(m_pts)>1: draw.line(m_pts, fill=rgb[:3]+(255,), width=max(2, int(4*st.session_state.size_minibox)), joint="round")
            ms_p = (int(off_x + (all_pts[0][1]-mi_lo)/m_lo_e*drw_w), int(off_y + drw_h - (all_pts[0][0]-mi_la)/m_la_e*drw_h))
            me_p = (int(off_x + (all_pts[-1][1]-mi_lo)/m_lo_e*drw_w), int(off_y + drw_h - (all_pts[-1][0]-mi_la)/m_la_e*drw_h))
            m_r = max(3, int(6 * st.session_state.size_minibox))
            safe_ellipse(draw, [ms_p[0]-m_r, ms_p[1]-m_r, ms_p[0]+m_r, ms_p[1]+m_r], fill="green")
            safe_ellipse(draw, [me_p[0]-m_r, me_p[1]-m_r, me_p[0]+m_r, me_p[1]+m_r], fill="red")

        if st.session_state.show_logo:
            lp = (30, bh_t + 30)
            if st.session_state.logo_type == "Grafik": draw_graphical_logo(draw, lp, st.session_state.size_logo, st.session_state.c_line)
            else:
                p = get_logo_path()
                if p:
                    ml = Image.open(p).convert("RGBA")
                    tw = int(w*0.15*st.session_state.size_logo); th = int(tw * (ml.height/ml.width))
                    overlay.paste(ml.resize((tw, th), Image.Resampling.LANCZOS), lp, ml.resize((tw, th), Image.Resampling.LANCZOS))

        final = Image.alpha_composite(canvas, overlay).convert('RGB')
        st.image(final, use_container_width=True)
        buf = io.BytesIO(); final.save(buf, format="JPEG", quality=95)
        st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), f"tour_final.jpg", "image/jpeg")
    except Exception as e: st.error(f"Fehler: {e}")
