import struct
import lzma
from datetime import datetime

# Based on the data type specification from the provided osu! documentation.
# Source: osr_reference.pdf & db_reference.pdf

def read_byte(file):
    """Reads a 1-byte integer from the file."""
    return struct.unpack('<B', file.read(1))[0]

def read_short(file):
    """Reads a 2-byte little-endian integer from the file."""
    return struct.unpack('<H', file.read(2))[0]

def read_int(file):
    """Reads a 4-byte little-endian integer from the file."""
    return struct.unpack('<I', file.read(4))[0]

def read_long(file):
    """Reads an 8-byte little-endian integer from the file."""
    return struct.unpack('<Q', file.read(8))[0]

def read_uleb128(file):
    """Reads a ULEB128-encoded integer from the file."""
    result = 0
    shift = 0
    while True:
        byte = read_byte(file)
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
    return result

def read_string(file):
    """
    Reads a string from the file.
    Format is a single byte (0x00 or 0x0b), then ULEB128 for length, then UTF-8 string.
    (Source: osr_reference.pdf, "String" data type) [cite: 87, 88]
    """
    if read_byte(file) == 0x0b:
        length = read_uleb128(file)
        if length > 0:
            return file.read(length).decode('utf-8')
    return ""

def parse_replay_file(file_path):
    """
    Parses an .osr replay file and returns a dictionary of its data.
    This function reads data fields in the order specified by osr_reference.pdf.
    """
    with open(file_path, 'rb') as f:
        replay_data = {}
        replay_data['game_mode'] = read_byte(f)
        replay_data['game_version'] = read_int(f)
        replay_data['beatmap_md5'] = read_string(f)
        replay_data['player_name'] = read_string(f)
        replay_data['replay_md5'] = read_string(f)
        replay_data['num_300s'] = read_short(f)
        replay_data['num_100s'] = read_short(f)
        replay_data['num_50s'] = read_short(f)
        replay_data['num_gekis'] = read_short(f)
        replay_data['num_katus'] = read_short(f)
        replay_data['num_misses'] = read_short(f)
        replay_data['total_score'] = read_int(f)
        return replay_data

def parse_osu_db(db_path):
    """
    Parses the osu!.db file and returns a dictionary of beatmaps keyed by MD5 hash.
    (Source: db_reference.pdf)
    """
    beatmaps = {}
    with open(db_path, 'rb') as f:
        version = read_int(f) # osu! version [cite: 42]
        read_int(f) # Folder count [cite: 42]
        read_byte(f) # Account unlocked [cite: 42]
        read_long(f) # Date account will be unlocked [cite: 42]
        read_string(f) # Player name [cite: 42]
        num_beatmaps = read_int(f) # Number of beatmaps [cite: 42]

        for _ in range(num_beatmaps):
            # The beatmap entry size is only present in older versions [cite: 48]
            if version < 20191106:
                entry_size = read_int(f)

            artist = read_string(f)
            # Skip unicode artist name, not needed for this app
            read_string(f)
            title = read_string(f)
            # Skip unicode song title
            read_string(f)
            creator = read_string(f)
            difficulty = read_string(f)
            read_string(f) # Audio file name
            md5_hash = read_string(f)
            read_string(f) # osu file name

            # We only need the string data for now, so we can skip the numeric fields.
            # This requires careful seeking based on the documented structure.
            # For simplicity in this step, we will read them but discard them.
            f.seek(1, 1) # Ranked status
            f.seek(2, 1) # Hitcircles
            f.seek(2, 1) # Sliders
            f.seek(2, 1) # Spinners
            f.seek(8, 1) # Last modification time

            # Difficulty settings vary by version
            if version < 20140609:
                f.seek(4 * 1, 1) # AR, CS, HP, OD as Bytes
            else:
                f.seek(4 * 4, 1) # AR, CS, HP, OD as Singles
            
            f.seek(8, 1) # Slider velocity

            # Star rating pairs vary by version
            if version >= 20140609:
                for _ in range(4): # For each game mode
                    num_pairs = read_int(f)
                    # Data type for pairs depends on version [cite: 52]
                    pair_size = 14 if version < 20250107 else 10 
                    f.seek(num_pairs * pair_size, 1)

            f.seek(4, 1) # Drain time
            f.seek(4, 1) # Total time
            f.seek(4, 1) # Preview time

            num_timing_points = read_int(f)
            f.seek(num_timing_points * 17, 1) # Seek past timing points

            f.seek(4, 1) # Difficulty ID
            f.seek(4, 1) # Beatmap ID
            f.seek(4, 1) # Thread ID
            f.seek(4 * 1, 1) # Grade achieved per mode
            f.seek(2, 1) # Local offset
            f.seek(4, 1) # Stack leniency
            f.seek(1, 1) # Gameplay mode

            read_string(f) # Song source
            read_string(f) # Song tags
            f.seek(2, 1) # Online offset
            read_string(f) # Font
            f.seek(1, 1) # Is unplayed
            f.seek(8, 1) # Last time played
            f.seek(1, 1) # Is osz2
            
            folder_name = read_string(f) # Beatmap folder name [cite: 58]
            
            f.seek(8, 1) # Last time checked
            f.seek(5 * 1, 1) # Ignore flags
            
            # Unknown short only present in older versions [cite: 58]
            if version < 20140609:
                f.seek(2, 1)

            f.seek(4, 1) # Last modification time
            f.seek(1, 1) # Mania scroll speed

            # Store the essential data in our dictionary
            if md5_hash:
                beatmaps[md5_hash] = {
                    "artist": artist,
                    "title": title,
                    "creator": creator,
                    "difficulty": difficulty,
                    "folder_name": folder_name
                }
    return beatmaps