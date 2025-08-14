import sqlite3
import os

# Go up one level from the 'tools' directory to find the DB
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(BASE_DIR, '..', 'osu_tracker.db')
OUTPUT_DIR = os.path.join(BASE_DIR, 'focus_lists')


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
    """Fetches beatmaps from the DB, prints their focus tags, and exports lists."""
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

    focus_counts = { "Balanced": 0, "Jumps": 0, "Flow": 0, "Speed": 0, "Stamina": 0, "Incomplete Data": 0 }
    grouped_maps = {tag: [] for tag in focus_counts}
    
    for beatmap_row in all_beatmaps:
        beatmap = dict(beatmap_row)
        tag = get_focus_tag(beatmap)
        focus_counts[tag] += 1
        grouped_maps[tag].append(beatmap)
        
    # Export the lists to files
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for tag, maps in grouped_maps.items():
        if not maps: continue
        
        # Sort maps by star rating, descending
        maps.sort(key=lambda m: m['stars'], reverse=True)
        
        filename = f"{tag.lower().replace(' ', '_')}.txt"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for bmap in maps:
                f.write(f"[{bmap['stars']:.2f}*] {bmap['artist']} - {bmap['title']} [{bmap['difficulty']}]\n")

    print(f"\nExported {len(all_beatmaps)} beatmaps into skill-focused lists in: {OUTPUT_DIR}")

    # --- Console Output ---
    # Combine all maps back for a general Top 100 list, sorted by stars
    all_tagged_maps = [item for sublist in grouped_maps.values() for item in sublist]
    all_tagged_maps.sort(key=lambda x: x['stars'], reverse=True)

    print("-" * 80)
    print(f"Analysis complete. Overall Top 100 beatmaps by Star Rating:")
    print("-" * 80)
    
    for beatmap in all_tagged_maps[:100]:
        tag = get_focus_tag(beatmap)
        print(f"[{tag:<10}] {beatmap['stars']:.2f}* | {beatmap['artist']} - {beatmap['title']} [{beatmap['difficulty']}]")
        
    if len(all_tagged_maps) > 100:
        print("\n...")
        print(f"(and {len(all_tagged_maps) - 100} more)")

    print("\n" + "=" * 80)
    print("Focus Distribution Summary:")
    print("=" * 80)
    for tag, count in focus_counts.items():
        percentage = (count / len(all_beatmaps)) * 100 if all_beatmaps else 0
        print(f"{tag:<15}: {count:>5} maps ({percentage:.2f}%)")
    print("-" * 80)

if __name__ == '__main__':
    analyze_beatmaps()