import streamlit as st
import gpxpy
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import math
import os
import base64

# --- APP KONFIGURATION ---
def get_fav_icon():
    if os.path.exists("logo_icon.png"):
        return "logo_icon.png"
    return "🏍️"

st.set_page_config(
    page_title="GPX Share Pro XXL", 
    page_icon=get_fav_icon(), 
    layout="centered"
)

# --- AGGRESSIVER BRANDING KILLER ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden !important;}
            footer {visibility: hidden !important;}
            header {visibility: hidden !important;}
            #stDecoration {display:none !important;}
            [data-testid="stHeader"] {display: none !important;}
            .stDeployButton {display:none !important;}
            [data-testid="stToolbar"] {display: none !important;}
            div.stActionButton {display:none !important;}
            .main .block-container {padding-top: 0rem !important; padding-bottom: 0rem !important;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- STANDARDWERTE (v3.1.8 Beta) ---
DEFAULTS = {
    "canvas_format": "Story (9:16)",
    "tour_title": "Meine Tour",
    "tour_date": "",
    "show_weather": False,
    "weather_icon": "☀️ Sonnig",
    "weather_temp": "25",
    "show_bike_badge": False,
    "bike_type": "Adventure",
    "bike_name": "BMW R 1250 GS",
    "c_line": "#DA2323",
    "c_badge": "#DA2323",
    "c_title": "#DA2323",
    "c_date": "#FFFFFF",
    "c_data": "#FFFFFF",
    "c_grid": "#FFFFFF",
    "w_line": 9,
    "show_markers": True,
    "show_speed": True,
    "show_profile": True,
    "show_route": False,
    "show_minibox": True,
    "logo_type": "Grafisches logo",
    "show_date": True,
    "bg_opacity": 100,
    "size_title": 1.5,
    "size_date": 1.0,
    "size_data": 1.0,
    "size_grid": 1.0,
    "size_logo": 1.0,
    "size_minibox": 1.0,
    "size_badge": 1.0,
    "story_margins_active": True,
    "margin_top": 150,
    "margin_bottom": 100,
    "img_zoom": 100,          
    "img_offset_x": 0,        
    "img_offset_y": 0,
    "img_bw": False,
    "custom_text": "",
    "c_custom_text": "#FFFFFF",
    "size_custom_text": 1.5,
    "pos_x_custom_text": 540,
    "pos_y_custom_text": 960,
    "pos_x_minibox": 770,
    "pos_y_minibox": 1380,
    "show_bg_top": True,
    "show_bg_bottom": True,
    "show_bg_date": True,
    "show_bg_minibox": True,
    "show_bg_custom_text": False
}

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

if "last_gpx_file" not in st.session_state:
    st.session_state.last_gpx_file = ""

# --- CANVAS SETUP ---
format_choice = st.session_state.get("canvas_format", "Story (9:16)")
if format_choice == "Story (9:16)":
    W_CANVAS, H_CANVAS = 1080, 1920
elif format_choice == "Post (1:1)":
    W_CANVAS, H_CANVAS = 1080, 1080
else:
    W_CANVAS, H_CANVAS = 1920, 1080

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

def hex_to_rgba(hex_color, alpha=255):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (alpha,)

def draw_data_icon(mode, size, color="white"):
    res = 4
    size = int(max(10, size))
    img = Image.new('RGBA', (size*res, size*res), (0,0,0,0))
    d = ImageDraw.Draw(img)
    lw = int(max(2, size*res*0.08))
    x0, y0, x1, y1 = lw, lw, size*res - lw, size*res - lw
    
    if mode == "dist":
        d.line([(x0, y1-lw), (x1//2, y1-lw), (x1//2, y0+lw), (x1, y0+lw)], fill=color, width=lw, joint="round")
        d.ellipse([x0-lw, y1-2*lw, x0+lw, y1], fill=color)
        d.ellipse([x1-lw, y0, x1+lw, y0+2*lw], fill=color)
    elif mode == "elev":
        d.polygon([(lw, y1), (size*res//2, y0), (x1, y1)], fill=color)
    elif mode == "speed": 
        d.arc([x0, y0, x1, y1], 150, 390, fill=color, width=lw)
        cx, cy = size*res//2, size*res//2 + lw
        d.line([cx, cy, cx + size*res*0.25, cy - size*res*0.25], fill=color, width=lw)
        d.ellipse([cx-lw, cy-lw, cx+lw, cy+lw], fill=color)
    elif mode.startswith("weather_"):
        w_type = mode.split("_")[1]
        cx, cy = size*res//2, size*res//2
        r = size*res*0.3
        if "Sonnig" in w_type:
            d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=color, width=lw)
            for i in range(8):
                a = i * math.pi / 4
                d.line([cx+math.cos(a)*r*1.4, cy+math.sin(a)*r*1.4, cx+math.cos(a)*r*2, cy+math.sin(a)*r*2], fill=color, width=lw)
        elif "Bewölkt" in w_type:
            d.ellipse([cx-r*1.5, cy-r*0.2, cx-r*0.1, cy+r*0.8], fill=color)
            d.ellipse([cx-r*0.8, cy-r*1.2, cx+r*0.8, cy+r*0.8], fill=color)
            d.ellipse([cx+r*0.1, cy-r*0.4, cx+r*1.5, cy+r*0.8], fill=color)
        else:
            d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=color)
                
    return img.resize((size, size), Image.Resampling.LANCZOS)

# --- UI HEADER ---
st.markdown('<div style="text-align: center; background: #111; padding: 10px; border-radius: 15px; border: 1px solid #333;"><p style="font-size: 30px; font-weight: 900; color: #da2323; margin: 0;">GPX SHARE PRO XXL</p></div>', unsafe_allow_html=True)

# --- UPLOADS ---
c_up1, c_up2 = st.columns(2)
with c_up1:
    up_gpx = st.file_uploader("📍 GPX Datei", key="gpx_up")
with c_up2:
    up_img = st.file_uploader("📸 Foto", key="img_up")

# --- SETTINGS ---
with st.expander("⚙️ Einstellungen [v3.1.8 Beta]"):
    t1, t2, t3 = st.tabs(["📝 Inhalt", "🎨 Design", "🖼️ Bild"])
    with t1:
        st.text_input("Tour Name", key="tour_title")
        st.checkbox("Wetter", key="show_weather")
        if st.session_state.show_weather:
            st.selectbox("Wetter Typ", ["☀️ Sonnig", "⛅ Bewölkt", "🌧️ Regen"], key="weather_icon")
            st.text_input("Temperatur", key="weather_temp")
        st.write("---")
        st.checkbox("Bike Badge (Schild)", key="show_bike_badge")
        if st.session_state.show_bike_badge:
            st.selectbox("Kategorie", ["Adventure", "Naked Bike", "Sportler", "Cruiser"], key="bike_type")
            st.text_input("Modell Name", key="bike_name")
            st.color_picker("Schild Randfarbe", key="c_badge")
    with t2:
        st.color_picker("Routenfarbe", key="c_line")
        st.number_input("Größe Titel", 0.5, 4.0, key="size_title", step=0.1)
        st.number_input("Größe Badge", 0.5, 4.0, key="size_badge", step=0.1)
    with t3:
        st.number_input("Zoom (%)", 10, 500, key="img_zoom")
        st.number_input("↔️ X Kommentar", 0, 3000, key="pos_x_custom_text")
        st.number_input("↕️ Y Kommentar", 0, 3000, key="pos_y_custom_text")

# --- DRAWING ---
if up_gpx:
    try:
        gpx = gpxpy.parse(io.BytesIO(up_gpx.getvalue()))
        pts, elevs = [], []
        d_total, a_gain, total_time = 0.0, 0.0, 0.0
        l_p, l_e, l_t = None, None, None
        for seg in gpx.tracks[0].segments:
            s_pts = []
            for p in seg.points:
                s_pts.append([p.latitude, p.longitude]); elevs.append(p.elevation or 0)
                if l_p:
                    d_total += calc_dist(l_p[0], l_p[1], p.latitude, p.longitude)
                    if p.elevation and l_e and p.elevation > l_e: a_gain += (p.elevation - l_e)
                    if p.time and l_t: total_time += (p.time - l_t).total_seconds()
                l_p, l_e, l_t = [p.latitude, p.longitude], p.elevation, p.time
            if s_pts: pts.append(s_pts)
        avg_s = d_total / (total_time / 3600.0) if total_time > 0 else 0.0

        w, h = W_CANVAS, H_CANVAS
        canvas = Image.new('RGBA', (w, h), (30, 30, 30, 255))
        if up_img:
            bg = ImageOps.exif_transpose(Image.open(io.BytesIO(up_img.getvalue()))).convert("RGBA")
            bg_w, bg_h = bg.size
            sc = max(w/bg_w, h/bg_h) * (st.session_state.img_zoom/100)
            nw, nh = int(bg_w*sc), int(bg_h*sc)
            canvas.paste(bg.resize((nw, nh), Image.Resampling.LANCZOS), ((w-nw)//2 + st.session_state.img_offset_x, (h-nh)//2 + st.session_state.img_offset_y))

        overlay = Image.new('RGBA', (w, h), (0,0,0,0)); draw = ImageDraw.Draw(overlay)
        bh_t, bh_b = int(h*0.2), int(h*0.12)
        if st.session_state.show_bg_top: safe_rect(draw, [0,0,w,bh_t], fill=(0,0,0,160))
        
        # TITEL & DATEN
        draw_text_with_shadow(draw, (w//2, bh_t*0.35), st.session_state.tour_title, load_font(int(w*0.08*st.session_state.size_title)), fill=st.session_state.c_title)
        items = [("dist", f"{d_total:.1f} km"), ("speed", f"{avg_s:.1f} km/h"), ("elev", f"{int(a_gain)} m")]
        if st.session_state.show_weather:
            items.append((f"weather_{st.session_state.weather_icon}", f"{st.session_state.weather_temp}°C"))
        
        f_d = load_font(int(w*0.045*st.session_state.size_data))
        i_s = int(w*0.045*st.session_state.size_data)
        tw_tot = sum([i_s + 10 + draw.textlength(t, f_d) for _,t in items]) + 40*(len(items)-1)
        cx = (w - tw_tot)//2
        for m, t in items:
            ic = draw_data_icon(m, i_s, st.session_state.c_data)
            overlay.paste(ic, (int(cx), int(bh_t*0.7 - i_s//2)), ic)
            draw_text_with_shadow(draw, (int(cx + i_s + 10 + draw.textlength(t, f_d)//2), int(bh_t*0.7)), t, f_d)
            cx += i_s + 10 + draw.textlength(t, f_d) + 40

        # BIKE SHIELD (COMPACT)
        if st.session_state.show_bike_badge and st.session_state.bike_name:
            sz = st.session_state.size_badge
            bw = int(draw.textlength(st.session_state.bike_name, load_font(int(35*sz))) + 80*sz)
            bh = int(140*sz)
            bx, by = w - bw - 40, bh_t + 40
            c_b = st.session_state.c_badge
            pts_s = [(bx, by), (bx+bw, by), (bx+bw, by+bh*0.7), (bx+bw//2, by+bh), (bx, by+bh*0.7)]
            draw.polygon(pts_s, fill=(30,30,30,220), outline=c_b, width=int(5*sz))
            
            # ICON (GROSS & KLAR)
            ic_cx, ic_cy = bx + bw//2, by + int(45*sz)
            lw_i = int(4*sz)
            draw.ellipse([ic_cx-35*sz, ic_cy-5*sz, ic_cx-15*sz, ic_cy+15*sz], outline=c_b, width=lw_i) # Rad vorn
            draw.ellipse([ic_cx+15*sz, ic_cy-5*sz, ic_cx+35*sz, ic_cy+15*sz], outline=c_b, width=lw_i) # Rad hinten
            draw.line([ic_cx-25*sz, ic_cy, ic_cx+25*sz, ic_cy], fill=c_b, width=lw_i) # Rahmen
            if st.session_state.bike_type == "Adventure":
                draw.line([ic_cx+20*sz, ic_cy, ic_cx+25*sz, ic_cy-20*sz], fill=c_b, width=lw_i) # Lenker hoch
            
            draw.text((bx+bw//2, by+int(100*sz)), st.session_state.bike_name.upper(), fill="white", font=load_font(int(32*sz)), anchor="mm")

        st.image(Image.alpha_composite(canvas, overlay).convert("RGB"), use_container_width=True)
        buf = io.BytesIO(); Image.alpha_composite(canvas, overlay).save(buf, format="PNG")
        st.download_button("🚀 Bild speichern", buf.getvalue(), "tour_v318.png")

    except Exception as e: st.error(f"Fehler: {e}")
