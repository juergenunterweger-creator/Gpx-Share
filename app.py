import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps
import io
import math
import os
from datetime import datetime
from staticmap import StaticMap, Line as MapLine

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro XXL", page_icon="🏍️", layout="centered")

# --- STANDARDWERTE (v2.6.0: Memory Fix & OSM Fix) ---
DEFAULTS = {
    "tour_title": "Meine Tour",
    "tour_date": "",
    "show_date": True,
    "bg_mode": "Automatisch",
    "bg_opacity": 100,
    "font_scale": 1.5,
    "title_y_offset": 0,
    "data_font_scale": 1.2,
    "data_y_offset": 150,
    "img_zoom": 1.0,
    "img_x_offset": 0,
    "img_y_offset": 0,
    "grid_font_scale": 1.0,
    "grid_m_interval": 250,
    "grid_km_interval": 10,
    "w_line": 9,
    "b_alpha": 160,
    "r_alpha": 255,
    "c_line": "#8B0000",
    "c_fill": "#8B0000",
    "c_box": "#000000",
    "b_height_adj": 0.20,
    "show_markers": True,
    "show_km_steps": True,
    "km_interval": 20,
    "show_profile": True,
    "show_grid": True,
    "fill_profile": True,
    "selected_track_idx": 0,
    "show_icons": True,
    "route_autoscale": True,
    "route_scale": 1.0
}

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

if "persistent_img" not in st.session_state: st.session_state.persistent_img = None
if "persistent_gpx" not in st.session_state: st.session_state.persistent_gpx = None

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
    x0, y0, x1, y1 = coords
    nx0, nx1 = min(x0, x1), max(x0, x1)
    ny0, ny1 = min(y0, y1), max(y0, y1)
    if nx0 == nx1: nx1 += 1
    if ny0 == ny1: ny1 += 1
    return [int(nx0), int(ny0), int(nx1), int(ny1)]

def safe_rect(draw, coords, fill=None, outline=None, width=1):
    try:
        draw.rectangle(validate_coords(coords), fill=fill, outline=outline, width=int(width))
    except: pass

def safe_ellipse(draw, coords, fill=None, outline=None, width=1):
    try:
        draw.ellipse(validate_coords(coords), fill=fill, outline=outline, width=int(width))
    except: pass

def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def get_fitted_font(text, max_width, start_size):
    size = int(max(10, start_size))
    font = load_font(size)
    try:
        d = ImageDraw.Draw(Image.new('RGB', (1,1)))
        while d.textlength(text, font=font) > max_width and size > 10:
            size -= 2
            font = load_font(size)
    except: pass
    return font

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

def draw_km_marker(draw, pos, km):
    x, y = pos
    r = 10
    safe_ellipse(draw, [x-r-1, y-r-1, x+r+1, y+r+1], fill="white")
    safe_ellipse(draw, [x-r, y-r, x+r, y+r], fill="#333333")
    f = load_font(12)
    draw.text((int(x), int(y)), str(km), fill="white", font=f, anchor="mm")

def draw_data_icon(mode, size, color="white"):
    res = 4
    size = int(max(1, size))
    img = Image.new('RGBA', (size*res, size*res), (0,0,0,0))
    d = ImageDraw.Draw(img)
    lw = max(4, int(size*res*0.08))
    if mode == "dist":
        d.arc([lw, lw, size*res-lw, size*res-lw], 140, 400, fill=color, width=lw)
        cx, cy = size*res//2, size*res//2
        d.line([cx, cy, cx + size*res*0.3, cy - size*res*0.3], fill=color, width=lw)
    elif mode == "elev":
        d.polygon([(lw, size*res-lw), (size*res//2, lw), (size*res-lw, size*res-lw)], fill=color)
    return img.resize((size, size), Image.Resampling.LANCZOS)

st.markdown("""<style>.stApp { background-color: #ffffff; color: #000000; } .title-modern { font-size: 36px; font-weight: 900; background: linear-gradient(90deg, #ff0000 0%, #8b0000 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin-bottom: 20px; } .social-btn { display: inline-block; padding: 10px 20px; border-radius: 5px; color: white !important; text-decoration: none; font-weight: bold; margin-right: 10px; text-align: center; } .fb-btn { background-color: #1877F2; } .wa-btn { background-color: #25D366; }</style>""", unsafe_allow_html=True)
st.markdown("<p class='title-modern'>GPX Share Pro</p>", unsafe_allow_html=True)

# --- UPLOADS ---
c_up1, c_up2 = st.columns(2)
with c_up1:
    # NEU: Nur GPX Dateien erlauben
    up_gpx = st.file_uploader("📍 1. GPX Datei wählen", type=["gpx"])
    if up_gpx:
        new_data = up_gpx.getvalue() # FIX: getvalue() statt read()
        if st.session_state.persistent_gpx != new_data:
            st.session_state.persistent_gpx = new_data
            gpx_obj = gpxpy.parse(io.BytesIO(new_data))
            try:
                start_time, _ = gpx_obj.get_time_bounds()
                if start_time: st.session_state.tour_date = start_time.strftime("%d.%m.%Y")
            except: pass
            st.session_state.tour_title = up_gpx.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
            st.rerun()

with c_up2:
    up_img = st.file_uploader("📸 2. Foto wählen (Optional)", type=["jpg", "jpeg", "png"])
    if up_img: 
        st.session_state.persistent_img = up_img.getvalue() # FIX: getvalue() statt read()

# --- OPTIONEN ---
with st.expander("⚙️ Einstellungen & Design", expanded=False):
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        st.write("**🖼️ Hintergrund & Foto**")
        st.selectbox("Hintergrund-Modus", ["Automatisch", "Nur Foto", "Nur Karte"], key="bg_mode")
        st.slider("Hintergrund Dimmer (%)", 0, 100, key="bg_opacity")
        if st.session_state.persistent_img:
            st.slider("Foto Zoom", 0.5, 5.0, key="img_zoom", step=0.1)
            st.slider("Foto X-Versatz", -1500, 1500, key="img_x_offset")
            st.slider("Foto Y-Versatz", -1500, 1500, key="img_y_offset")
        
        st.write("**📏 Raster-Steuerung**")
        st.checkbox("Raster anzeigen", key="show_grid")
        st.slider("Raster Schriftgröße", 0.5, 3.0, key="grid_font_scale")
        st.number_input("Meter-Intervalle (m)", 50, 5000, key="grid_m_interval", step=50)
        st.number_input("KM-Intervalle (km)", 1, 500, key="grid_km_interval", step=5)

    with col_opt2:
        st.write("**📝 Texte & Position**")
        st.text_input("Tour Name", key="tour_title")
        st.text_input("Datum", key="tour_date")
        st.slider("Titel Größe", 0.5, 4.0, key="font_scale")
        st.slider("Titel Y-Position", -300, 300, key="title_y_offset")
        st.slider("Daten Größe", 0.5, 4.0, key="data_font_scale")
        st.slider("Daten Y-Abstand", 0, 600, key="data_y_offset")
        
        st.write("**🎨 Farben & Reset**")
        st.color_picker("Routenfarbe", key="c_line")
        st.color_picker("Balkenfarbe", key="c_box")
        st.checkbox("Icons anzeigen", key="show_icons")
        st.button("🔄 Alles zurücksetzen", on_click=reset_parameters)

# --- INFO REITER ---
with st.expander("ℹ️ Über GPX Share Pro", expanded=False):
    st.markdown("### GPX Share Pro XXL | v2.6.0")
    st.markdown("**Copyright: Jürgen Unterweger**")
    st.markdown(f'<a href="https://www.paypal.com/donate?hosted_button_id=FF6FBUE84V7MG" target="_blank"><img src="https://www.paypalobjects.com/de_DE/i/btn/btn_donateCC_LG.gif" width="120"></a>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**📲 Installation:** iPhone (Teilen -> Home-Bildschirm) | Android (Menü -> Installieren)")

st.divider()

# --- VERARBEITUNG ---
if st.session_state.persistent_gpx:
    try:
        gpx = gpxpy.parse(io.BytesIO(st.session_state.persistent_gpx))
        segments_pts, elevs = [], []
        d_total, a_gain, last, last_elev = 0.0, 0.0, None, None
        
        target_track = gpx.tracks[st.session_state.selected_track_idx]
        for seg in target_track.segments:
            current_seg = []
            for p in seg.points:
                current_seg.append([p.latitude, p.longitude])
                elevs.append(p.elevation if p.elevation is not None else 0)
                if last:
                    d_total += calc_dist(last[0], last[1], p.latitude, p.longitude)
                    if p.elevation is not None and last_elev is not None:
                        diff = p.elevation - last_elev
                        if diff > 0: a_gain += diff
                last, last_elev = [p.latitude, p.longitude], p.elevation
            if current_seg: segments_pts.append(current_seg)

        if segments_pts:
            all_pts = [pt for seg in segments_pts for pt in seg]
            lats, lons = zip(*all_pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            
            # FIX FÜR OSM KARTE: Abstandshalter für extrem kurze/gerade Touren
            if (ma_la - mi_la) < 0.005:
                ma_la += 0.0025
                mi_la -= 0.0025
            if (ma_lo - mi_lo) < 0.005:
                ma_lo += 0.0025
                mi_lo -= 0.0025

            w, h = 1080, 1920
            
            # HINTERGRUND
            canvas = Image.new('RGBA', (w, h), (255, 255, 255, 255))
            use_map = (st.session_state.bg_mode == "Nur Karte") or (st.session_state.bg_mode == "Automatisch" and not st.session_state.persistent_img)
            
            if not use_map and st.session_state.persistent_img:
                bg_img = ImageOps.exif_transpose(Image.open(io.BytesIO(st.session_state.persistent_img))).convert("RGBA")
                nz_w, nz_h = int(w * st.session_state.img_zoom), int(h * st.session_state.img_zoom)
                bg_img = bg_img.resize((nz_w, nz_h), Image.Resampling.LANCZOS)
                canvas.paste(bg_img, (int(st.session_state.img_x_offset - (nz_w-w)//2), int(st.session_state.img_y_offset - (nz_h-h)//2)))
            else:
                m = StaticMap(w, h, url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png")
                # Breite auf 2 gesetzt für sicheres Bounding
                m.add_line(MapLine(list(zip(lons, lats)), 'blue', 2))
                canvas.paste(m.render().convert("RGBA"), (0, 0))

            if st.session_state.bg_opacity < 100:
                canvas = Image.blend(Image.new('RGBA', (w, h), (255, 255, 255, 255)), canvas, st.session_state.bg_opacity / 100)

            overlay = Image.new('RGBA', (w, h), (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            rgb_box = tuple(int(st.session_state.c_box[i*2+1:i*2+3], 16) for i in range(3))
            bh_top, bh_bot = int(h * st.session_state.b_height_adj), int(h * 0.12)
            safe_rect(draw, [0, 0, w, bh_top], fill=rgb_box + (st.session_state.b_alpha,))
            safe_rect(draw, [0, h - bh_bot, w, h], fill=rgb_box + (st.session_state.b_alpha,))

            # HÖHENPROFIL & RASTER
            if st.session_state.show_profile and len(elevs) > 1:
                e_min, e_max = min(elevs), max(elevs)
                e_range = (e_max - e_min) if e_max > e_min else 1
                grid_y_start = h - bh_bot
                profile_pts = [((i/len(elevs))*w, (h-bh_bot)+(bh_bot*0.85)-((ev-e_min)/e_range)*(bh_bot*0.7)) for i, ev in enumerate(elevs)]
                
                if st.session_state.show_grid:
                    f_grid = load_font(int(w * 0.025 * st.session_state.grid_font_scale))
                    for m_val in range(int(e_min // st.session_state.grid_m_interval + 1) * st.session_state.grid_m_interval, int(e_max), int(st.session_state.grid_m_interval)):
                        gy = int((h-bh_bot)+(bh_bot*0.85)-((m_val-e_min)/e_range)*(bh_bot*0.7))
                        draw.line([(0, gy), (w, gy)], fill=(255,255,255,50), width=1)
                        draw.text((int(w*0.01), int(gy-2)), f"{m_val}m", fill=(255,255,255,160), font=f_grid, anchor="ld")
                    for k in range(int(st.session_state.grid_km_interval), int(d_total), int(st.session_state.grid_km_interval)):
                        gx = int((k / d_total) * w)
                        draw.line([(gx, grid_y_start), (gx, h)], fill=(255,255,255,50), width=1)
                        draw.text((int(gx+5), int(grid_y_start+5)), f"{k}km", fill=(255,255,255,160), font=f_grid, anchor="lt")
                
                if st.session_state.fill_profile:
                    rgb_fill = tuple(int(st.session_state.c_fill[i*2+1:i*2+3], 16) for i in range(3))
                    draw.polygon(profile_pts + [(w, h), (0, h)], fill=rgb_fill + (120,))
                draw.line(profile_pts, fill=(255,255,255, 255), width=max(3, int(w*0.003)), joint="round")

            # TITEL & DATEN
            t_y = int(bh_top * 0.35) + st.session_state.title_y_offset
            f_title = get_fitted_font(st.session_state.tour_title, w*0.9, int(w*0.08*st.session_state.font_scale))
            draw_text_with_shadow(draw, (w//2, t_y), st.session_state.tour_title, f_title)
            
            txt_dist, txt_elev = f"{d_total:.1f} km", f"{int(a_gain)} m"
            f_data = get_fitted_font(txt_dist + " " + txt_elev, w*0.8, int(w*0.05*st.session_state.data_font_scale))
            icon_size = int(max(1, w * 0.05 * st.session_state.data_font_scale))
            i_gap, spacing = int(w*0.015), int(w*0.08)
            
            total_w = (icon_size if st.session_state.show_icons else 0) + i_gap + draw.textlength(txt_dist, f_data) + spacing + (icon_size if st.session_state.show_icons else 0) + i_gap + draw.textlength(txt_elev, f_data)
            curr_x, d_y = (w - total_w) // 2, t_y + st.session_state.data_y_offset
            
            for mode, txt in [("dist", txt_dist), ("elev", txt_elev)]:
                if st.session_state.show_icons:
                    overlay.paste(draw_data_icon(mode, icon_size), (int(curr_x), int(d_y-icon_size//2)), draw_data_icon(mode, icon_size))
                    curr_x += icon_size + i_gap
                tw = draw.textlength(txt, font=f_data)
                draw_text_with_shadow(draw, (curr_x+tw//2, d_y), txt, f_data)
                curr_x += tw + spacing

            # DATUMS-BOX
            if st.session_state.show_date and st.session_state.tour_date:
                f_date = load_font(int(w * 0.028 * st.session_state.font_scale))
                tw = draw.textlength(st.session_state.tour_date, font=f_date)
                bx2, by2 = int(w - 30), int(h - bh_bot - 20)
                bx1, by1 = int(bx2 - tw - 40), int(by2 - 60)
                safe_rect(draw, [bx1, by1, bx2, by2], fill=rgb_box + (st.session_state.b_alpha,), outline="white", width=2)
                draw.text(((bx1 + bx2)//2, (by1 + by2)//2 + 2), st.session_state.tour_date, fill="white", font=f_date, anchor="mm")

            # ROUTE & MARKER
            margin = 0.20 if st.session_state.route_autoscale else 0.5 * (1.0 - (0.4 * st.session_state.route_scale))
            la_eps, lo_eps = (ma_la-mi_la) or 0.001, (ma_lo-mi_lo) or 0.001
            def transform(lat, lon):
                return (int(w*margin + (lon-mi_lo)/lo_eps*w*(1-2*margin)), int(h*(1-margin) - (lat-mi_la)/la_eps*h*(1-2*margin)))

            dist_acc, last_p = 0.0, None
            km_marks, next_km_goal = [], st.session_state.km_interval
            rgb_route = tuple(int(st.session_state.c_line[i*2+1:i*2+3], 16) for i in range(3))

            for seg in segments_pts:
                s_pts = []
                for p in seg:
                    curr_p = transform(p[0], p[1])
                    s_pts.append(curr_p)
                    if last_p:
                        dist_acc += calc_dist(last_raw[0], last_raw[1], p[0], p[1])
                        if st.session_state.show_km_steps and dist_acc >= next_km_goal:
                            km_marks.append((curr_p, int(next_km_goal)))
                            next_km_goal += st.session_state.km_interval
                    last_p, last_raw = curr_p, p
                if len(s_pts) > 1: draw.line(s_pts, fill=rgb_route + (st.session_state.r_alpha,), width=int(st.session_state.w_line), joint="round")

            for pos, val in km_marks: draw_km_marker(draw, pos, val)
            if st.session_state.show_markers and all_pts:
                draw_marker(draw, transform(all_pts[0][0], all_pts[0][1]), "green", "S")
                draw_marker(draw, transform(all_pts[-1][0], all_pts[-1][1]), "red", "Z")

            final = Image.alpha_composite(canvas, overlay).convert('RGB')
            st.image(final, use_container_width=True)
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            
            # --- NEUE TEILEN SEKTION ---
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), f"tour_final.jpg", "image/jpeg")
            st.markdown("<br><strong>📲 Bild manuell teilen (zuerst speichern):</strong>", unsafe_allow_html=True)
            st.markdown("""
                <a href="https://www.facebook.com/sharer/sharer.php?u=https://deine-website.de" target="_blank" class="social-btn fb-btn">📘 Facebook URL teilen</a>
                <a href="whatsapp://send?text=Schau%20dir%20meine%20neue%20Motorrad-Tour%20an!" class="social-btn wa-btn">💬 WhatsApp öffnen</a>
                """, unsafe_allow_html=True)

    except Exception as e: st.error(f"Fehler: {e}")
