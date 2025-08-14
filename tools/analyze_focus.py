import sqlite3
import os

# Go up one level from the 'tools' directory to find the DB
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(BASE_DIR, '..', 'osu_tracker.db')

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    if not os.path.exists(DATABASE_FILE):
        print(f"Error: Database file not found at {DATABASE_FILE}")
        print("Please run the application and sync your beatmaps from the Config page first.")
        return None
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_focus_tag(beatmap):
    """Determines the focus tag for a given beatmap based on its attributes."""
    # Ensure all required attributes are present and not None
    required_attrs = ['aim', 'speed', 'slider_factor', 'speed_note_count', 
                      'aim_difficult_slider_count', 'num_sliders', 'num_hitcircles', 'num_spinners']
    for attr in required_attrs:
        if beatmap[attr] is None:
            return "Incomplete Data"

    # Extract values for easier access
    aim = beatmap['aim']
    speed = beatmap['speed']
    slider_factor = beatmap['slider_factor']
    speed_note_count = beatmap['speed_note_count']
    aim_difficult_slider_count = beatmap['aim_difficult_slider_count']
    num_sliders = beatmap['num_sliders']
    num_circles = beatmap['num_hitcircles']
    num_spinners = beatmap['num_spinners']
    
    n_objects = num_circles + num_sliders + num_spinners
    if n_objects == 0:
        return "Incomplete Data"

    # Apply heuristics in a specific order of precedence
    # Jumps
    if aim > speed * 1.1 and slider_factor > 0.95:
        return "Jumps"
    
    # Flow
    if num_sliders > 0 and (aim_difficult_slider_count / num_sliders) > 0.5 and num_sliders > (n_objects * 0.2):
        return "Flow"
        
    # Speed
    if speed > aim * 1.1 and (speed_note_count / n_objects) < 0.4:
        return "Speed"
        
    # Stamina
    if (speed_note_count / n_objects) > 0.4:
        return "Stamina"

    return "Balanced"

def analyze_beatmaps():
    """Fetches beatmaps from the DB and prints their focus tags."""
    conn = get_db_connection()
    if not conn:
        return
        
    cursor = conn.cursor()
    
    # Fetch all osu!standard maps with calculated difficulty attributes
    cursor.execute("""
        SELECT 
            artist, title, difficulty, stars, 
            aim, speed, slider_factor, speed_note_count,
            aim_difficult_slider_count, num_sliders, num_hitcircles, num_spinners
        FROM beatmaps
        WHERE game_mode = 0 AND stars IS NOT NULL AND aim IS NOT NULL
    """)
    
    all_beatmaps = cursor.fetchall()
    conn.close()

    if not all_beatmaps:
        print("No processed beatmaps found in the database.")
        print("Please run the beatmap sync from the Config page in the application first.")
        return

    focus_counts = {
        "Balanced": 0,
        "Jumps": 0,
        "Flow": 0,
        "Speed": 0,
        "Stamina": 0,
        "Incomplete Data": 0
    }
    
    tagged_maps = []
    for beatmap in all_beatmaps:
        tag = get_focus_tag(dict(beatmap))
        focus_counts[tag] += 1
        tagged_maps.append((beatmap, tag))
        
    # Sort by star rating for a more structured output
    tagged_maps.sort(key=lambda x: x[0]['stars'], reverse=True)

    print("-" * 80)
    print(f"Analyzed {len(all_beatmaps)} beatmaps. Results (Top 100 shown):")
    print("-" * 80)
    
    for beatmap, tag in tagged_maps[:100]:
        print(f"[{tag:<10}] {beatmap['stars']:.2f}* | {beatmap['artist']} - {beatmap['title']} [{beatmap['difficulty']}]")
        
    if len(tagged_maps) > 100:
        print("\n...")
        print(f"(and {len(tagged_maps) - 100} more)")

    print("\n" + "=" * 80)
    print("Focus Distribution Summary:")
    print("=" * 80)
    for tag, count in focus_counts.items():
        percentage = (count / len(all_beatmaps)) * 100 if all_beatmaps else 0
        print(f"{tag:<15}: {count:>5} maps ({percentage:.2f}%)")
    print("-" * 80)

if __name__ == '__main__':
    analyze_beatmaps()