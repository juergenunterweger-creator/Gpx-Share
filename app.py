import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import math

# --- APP KONFIGURATION ---
st.set_page_config(page_title="GPX Share Pro XXL", page_icon="🏍️", layout="centered")

# --- STANDARDWERTE (v2.7.6: Ultra Clean Edition) ---
DEFAULTS = {
    "tour_title": "Meine Tour",
    "tour_date": "",
    "c_line": "#8B0000",
    "w_line": 9,
    "show_markers": True,
    "show_speed": True,
    "show_profile": True,
    "auto_intervals": True,
    "grid_m_interval": 250,
    "grid_km_interval": 10,
    "bg_opacity": 100,
    "size_title": 1.5,
    "size_date": 1.0,
    "size_data": 1.2,
    "size_grid": 1.0
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

# SICHERHEIT: Absoluter Schutz vor "x1 must be greater than x0" Fehlern
def validate_coords(coords):
    x0, y0, x1, y1 = coords
    nx0, nx1 = min(x0, x1), max(x0, x1)
    ny0, ny1 = min(y0, y1), max(y0, y1)
    return [nx0, ny0, nx1 + 1, ny1 + 1]

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

def draw_data_icon(mode, size, color="white"):
    res = 4
    size = int(max(10, size))
    img = Image.new('RGBA', (size*res, size*res), (0,0,0,0))
    d = ImageDraw.Draw(img)
    lw = int(max(2, size*res*0.08))
    
    # Schutz vor 0-Pixel Berechnungen
    x0, y0 = lw, lw
    x1 = max(x0 + 2, size*res - lw) 
    y1 = max(y0 + 2, size*res - lw)
    
    if mode == "dist":
        d.arc([x0, y0, x1, y1], 140, 400, fill=color, width=lw)
        cx, cy = size*res//2, size*res//2
        d.line([cx, cy, cx + size*res*0.3, cy - size*res*0.3], fill=color, width=lw)
    elif mode == "elev":
        d.polygon([(lw, y1), (size*res//2, y0), (x1, y1)], fill=color)
    elif mode == "speed": 
        d.arc([x0, y0, x1, y1], 150, 390, fill=color, width=lw)
        cx, cy = size*res//2, size*res//2 + lw
        d.line([cx, cy, cx + size*res*0.25, cy - size*res*0.25], fill=color, width=lw)
        rad = max(1, lw)
        d.ellipse([cx-rad, cy-rad, cx+rad+1, cy+rad+1], fill=color)
        
    return img.resize((size, size), Image.Resampling.LANCZOS)

st.markdown("""<style>.stApp { background-color: #ffffff; color: #000000; } .title-modern { font-size: 36px; font-weight: 900; background: linear-gradient(90deg, #ff0000 0%, #8b0000 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin-bottom: 20px; } .social-btn { display: inline-block; padding: 10px 20px; border-radius: 5px; color: white !important; text-decoration: none; font-weight: bold; margin-right: 10px; text-align: center; } .fb-btn { background-color: #1877F2; } .wa-btn { background-color: #25D366; }</style>""", unsafe_allow_html=True)
st.markdown("<p class='title-modern'>GPX Share Pro</p>", unsafe_allow_html=True)

# --- UPLOADS ---
c_up1, c_up2 = st.columns(2)

with c_up1:
    up_gpx = st.file_uploader("📍 1. GPX Datei wählen", key="gpx_uploader")
    if up_gpx is not None:
        if st.session_state.last_gpx_file != up_gpx.name:
            st.session_state.last_gpx_file = up_gpx.name
            st.session_state.tour_title = up_gpx.name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
            
            try:
                gpx_obj = gpxpy.parse(io.BytesIO(up_gpx.getvalue()))
                parsed_date = ""
                if gpx_obj.time:
                    parsed_date = gpx_obj.time.strftime("%d.%m.%Y")
                else:
                    for track in gpx_obj.tracks:
                        for seg in track.segments:
                            for pt in seg.points:
                                if pt.time:
                                    parsed_date = pt.time.strftime("%d.%m.%Y")
                                    break
                            if parsed_date: break
                        if parsed_date: break
                if parsed_date:
                    st.session_state.tour_date = parsed_date
            except: pass
            
            # Seite SOFORT neu laden, damit die Felder ausgefüllt werden!
            st.rerun()

with c_up2:
    up_img = st.file_uploader("📸 2. Foto wählen (Optional)", type=["jpg", "jpeg", "png"], key="img_uploader")

# --- OPTIONEN (DEINE 9 PUNKTE) ---
with st.expander("⚙️ Einstellungen (Aufgeräumt)", expanded=True):
    col_opt1, col_opt2 = st.columns(2)
    
    with col_opt1:
        st.write("**📝 Tour & Design**")
        st.text_input("2. Tour Name", key="tour_title")
        st.text_input("3. Datum", key="tour_date")
        
        st.color_picker("1a. Routenfarbe", key="c_line")
        st.slider("1b. Routenstärke", 1, 20, key="w_line")
        st.slider("8. Hintergrund Dimmer (%)", 0, 100, key="bg_opacity")
        
        st.write("**🔠 9. Textgrößen separat**")
        st.slider("Größe Titel", 0.5, 4.0, key="size_title", step=0.1)
        st.slider("Größe Datum", 0.5, 4.0, key="size_date", step=0.1)
        st.slider("Größe Daten (KM/H/Höhe)", 0.5, 4.0, key="size_data", step=0.1)
        st.slider("Größe Raster", 0.5, 3.0, key="size_grid", step=0.1)

    with col_opt2:
        st.write("**✅ Ein- / Ausblenden**")
        st.checkbox("4. Start/Ziel (S/Z)", key="show_markers")
        st.checkbox("5. Ø Geschwindigkeit", key="show_speed")
        st.checkbox("6. Höhenprofil", key="show_profile")
        
        st.write("**📏 7. Raster & Intervalle**")
        st.checkbox("Auto-Intervalle nutzen", key="auto_intervals")
        if not st.session_state.auto_intervals:
            st.number_input("Meter-Intervalle (m)", 50, 5000, key="grid_m_interval", step=50)
            st.number_input("KM-Intervalle (km)", 1, 500, key="grid_km_interval", step=5)
            
        st.button("🔄 Alles zurücksetzen", on_click=reset_parameters)

# --- INFO REITER ---
with st.expander("ℹ️ Über GPX Share Pro", expanded=False):
    st.markdown("### GPX Share Pro XXL | v2.7.6")
    st.markdown("**Copyright: Jürgen Unterweger**")
    st.markdown(f'<a href="https://www.paypal.com/donate?hosted_button_id=FF6FBUE84V7MG" target="_blank"><img src="https://www.paypalobjects.com/de_DE/i/btn/btn_donateCC_LG.gif" width="120"></a>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**📲 Installation:** iPhone (Teilen -> Home-Bildschirm) | Android (Menü -> Installieren)")

st.divider()

# --- VERARBEITUNG ---
if up_gpx is not None:
    try:
        gpx = gpxpy.parse(io.BytesIO(up_gpx.getvalue()))
        segments_pts, elevs = [], []
        d_total, a_gain = 0.0, 0.0
        last, last_elev, last_time = None, None, None
        total_time_s = 0.0 
        
        target_track = gpx.tracks[0] # Immer den ersten Track nehmen
        for seg in target_track.segments:
            current_seg = []
            for p in seg.points:
                current_seg.append([p.latitude, p.longitude])
                elevs.append(p.elevation if p.elevation is not None else 0)
                if last:
                    d_total += calc_dist(last[0], last[1], p.latitude, p.longitude)
                    if p.elevation is not None and last_elev is not None:
                        diff_e = p.elevation - last_elev
                        if diff_e > 0: a_gain += diff_e
                    if p.time and last_time:
                        diff_t = (p.time - last_time).total_seconds()
                        if 0 < diff_t < 1800: # Pausen über 30 Min ignorieren
                            total_time_s += diff_t
                            
                last, last_elev, last_time = [p.latitude, p.longitude], p.elevation, p.time
            if current_seg: segments_pts.append(current_seg)

        avg_speed = 0.0
        if total_time_s > 0:
            avg_speed = d_total / (total_time_s / 3600.0)

        if segments_pts:
            all_pts = [pt for seg in segments_pts for pt in seg]
            lats, lons = zip(*all_pts)
            mi_la, ma_la, mi_lo, ma_lo = min(lats), max(lats), min(lons), max(lons)
            w, h = 1080, 1920
            
            # Verhindern von Abstürzen bei sehr kurzen Touren
            if (ma_la - mi_la) < 0.005:
                ma_la += 0.005
                mi_la -= 0.005
            if (ma_lo - mi_lo) < 0.005:
                ma_lo += 0.005
                mi_lo -= 0.005
            
            if st.session_state.auto_intervals:
                step_km = 1 if d_total < 10 else 5 if d_total < 50 else 10 if d_total < 100 else 20 if d_total < 250 else 50
                e_range_raw = max(elevs) - min(elevs) if len(elevs) > 1 else 0
                step_m = 50 if e_range_raw < 200 else 100 if e_range_raw < 500 else 250 if e_range_raw < 1500 else 500
            else:
                step_km = st.session_state.grid_km_interval
                step_m = st.session_state.grid_m_interval

            # BILD-HINTERGRUND ERSTELLEN
            canvas = Image.new('RGBA', (w, h), (30, 30, 30, 255)) 
            
            if up_img is not None:
                bg_img = ImageOps.exif_transpose(Image.open(io.BytesIO(up_img.getvalue()))).convert("RGBA")
                # Auto-Fit: Passt das Bild perfekt ins 1080x1920 Format ohne Verzerrung an!
                bg_img = ImageOps.fit(bg_img, (w, h), Image.Resampling.LANCZOS)
                canvas.paste(bg_img, (0, 0))

            if st.session_state.bg_opacity < 100:
                canvas = Image.blend(Image.new('RGBA', (w, h), (255, 255, 255, 255)), canvas, st.session_state.bg_opacity / 100)

            overlay = Image.new('RGBA', (w, h), (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            
            # Schwarze Info-Balken oben und unten
            bh_top, bh_bot = int(h * 0.20), int(h * 0.12)
            safe_rect(draw, [0, 0, w, bh_top], fill=(0, 0, 0, 160))
            safe_rect(draw, [0, h - bh_bot, w, h], fill=(0, 0, 0, 160))

            # HÖHENPROFIL & RASTER
            if st.session_state.show_profile and len(elevs) > 1:
                e_min, e_max = min(elevs), max(elevs)
                e_range = (e_max - e_min) if e_max > e_min else 1
                grid_y_start = h - bh_bot
                profile_pts = [((i/len(elevs))*w, (h-bh_bot)+(bh_bot*0.85)-((ev-e_min)/e_range)*(bh_bot*0.7)) for i, ev in enumerate(elevs)]
                
                f_grid = load_font(int(w * 0.025 * st.session_state.size_grid))
                if step_m > 0 and step_km > 0:
                    for m_val in range(int(e_min // step_m + 1) * step_m, int(e_max), step_m):
                        gy = int((h-bh_bot)+(bh_bot*0.85)-((m_val-e_min)/e_range)*(bh_bot*0.7))
                        draw.line([(0, gy), (w, gy)], fill=(255,255,255,50), width=1)
                        draw.text((int(w*0.01), int(gy-2)), f"{m_val}m", fill=(255,255,255,160), font=f_grid, anchor="ld")
                    for k in range(step_km, int(d_total), step_km):
                        gx = int((k / d_total) * w)
                        draw.line([(gx, grid_y_start), (gx, h)], fill=(255,255,255,50), width=1)
                        draw.text((int(gx+5), int(grid_y_start+5)), f"{k}km", fill=(255,255,255,160), font=f_grid, anchor="lt")
                
                rgb_fill = tuple(int("#8B0000"[i*2+1:i*2+3], 16) for i in range(3))
                draw.polygon(profile_pts + [(w, h), (0, h)], fill=rgb_fill + (120,))
                draw.line(profile_pts, fill=(255,255,255, 255), width=max(3, int(w*0.003)), joint="round")

            # TITEL & DATEN
            t_y = int(bh_top * 0.35)
            f_title = load_font(int(w * 0.08 * st.session_state.size_title))
            draw_text_with_shadow(draw, (w//2, t_y), st.session_state.tour_title, f_title, offset=2)
            
            data_items = [("dist", f"{d_total:.1f} km")]
            if st.session_state.show_speed and avg_speed > 0:
                data_items.append(("speed", f"{avg_speed:.1f} km/h"))
            data_items.append(("elev", f"{int(a_gain)} m"))
            
            f_data = load_font(int(w * 0.05 * st.session_state.size_data))
            icon_size = int(max(1, w * 0.05 * st.session_state.size_data))
            i_gap, spacing = int(w*0.015), int(w*0.08)
            
            total_w = sum([icon_size + i_gap + draw.textlength(txt, f_data) for _, txt in data_items]) + spacing * (len(data_items) - 1)
            curr_x, d_y = (w - total_w) // 2, t_y + 150
            
            for mode, txt in data_items:
                overlay.paste(draw_data_icon(mode, icon_size), (int(curr_x), int(d_y-icon_size//2)), draw_data_icon(mode, icon_size))
                curr_x += icon_size + i_gap
                tw = draw.textlength(txt, font=f_data)
                draw_text_with_shadow(draw, (curr_x+tw//2, d_y), txt, f_data, offset=2)
                curr_x += tw + spacing

            # DATUMS-BOX
            if st.session_state.tour_date:
                f_date = load_font(int(w * 0.028 * st.session_state.size_date))
                tw = draw.textlength(st.session_state.tour_date, font=f_date)
                bx2, by2 = int(w - 30), int(h - bh_bot - 20)
                bx1, by1 = int(bx2 - tw - 40), int(by2 - 60)
                safe_rect(draw, [bx1, by1, bx2, by2], fill=(0, 0, 0, 160), outline="white", width=2)
                draw.text(((bx1 + bx2)//2, (by1 + by2)//2 + 2), st.session_state.tour_date, fill="white", font=f_date, anchor="mm")

            # ROUTE & MARKER ZEICHNEN
            margin = 0.20
            la_eps, lo_eps = (ma_la-mi_la) or 0.001, (ma_lo-mi_lo) or 0.001
            def transform(lat, lon):
                return (int(w*margin + (lon-mi_lo)/lo_eps*w*(1-2*margin)), int(h*(1-margin) - (lat-mi_la)/la_eps*h*(1-2*margin)))

            rgb_route = tuple(int(st.session_state.c_line[i*2+1:i*2+3], 16) for i in range(3))

            for seg in segments_pts:
                s_pts = [transform(p[0], p[1]) for p in seg]
                if len(s_pts) > 1: 
                    # Die Linie wird jetzt garantiert immer gezeichnet!
                    draw.line(s_pts, fill=rgb_route + (255,), width=int(st.session_state.w_line), joint="round")
                
            if st.session_state.show_markers and all_pts:
                draw_marker(draw, transform(all_pts[0][0], all_pts[0][1]), "green", "S")
                draw_marker(draw, transform(all_pts[-1][0], all_pts[-1][1]), "red", "Z")

            final = Image.alpha_composite(canvas, overlay).convert('RGB')
            st.image(final, use_container_width=True)
            buf = io.BytesIO()
            final.save(buf, format="JPEG", quality=95)
            
            st.download_button("🚀 BILD SPEICHERN", buf.getvalue(), f"tour_final.jpg", "image/jpeg")
            st.markdown("<br><strong>📲 Bild manuell teilen (zuerst speichern):</strong>", unsafe_allow_html=True)
            st.markdown("""
                <a href="https://www.facebook.com/sharer/sharer.php?u=https://deine-website.de" target="_blank" class="social-btn fb-btn">📘 Facebook URL teilen</a>
                <a href="whatsapp://send?text=Schau%20dir%20meine%20neue%20Motorrad-Tour%20an!" class="social-btn wa-btn">💬 WhatsApp öffnen</a>
                """, unsafe_allow_html=True)

    except Exception as e: st.error(f"Fehler: {e}")
