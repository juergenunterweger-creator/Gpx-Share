# --- STRICHLISTE (COUNTER) FUNKTIONEN ---
COUNTER_FILE = "tour_counter.txt"

def get_tour_count():
    count = 50 # Grund-Startwert
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r") as f:
                saved_count = int(f.read().strip())
                # Nur den gespeicherten Wert nehmen, wenn er größer/gleich 50 ist
                if saved_count > 50:
                    count = saved_count
        except:
            pass
            
    # Falls der Wert (neu) auf 50 gesetzt wurde, direkt in die Datei schreiben
    try:
        with open(COUNTER_FILE, "w") as f:
            f.write(str(count))
    except:
        pass
        
    return count

def increment_tour_count():
    count = get_tour_count() + 1
    try:
        with open(COUNTER_FILE, "w") as f:
            f.write(str(count))
    except:
        pass
    return count

# Globale Variable für den aktuellen Stand
current_tour_count = get_tour_count()
