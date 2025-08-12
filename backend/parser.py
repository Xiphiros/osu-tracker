import struct
import lzma
import logging
import os
from datetime import datetime, timedelta
import rosu_pp_py

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
    
def read_float(file):
    """Reads a 4-byte single-precision float from the file."""
    return struct.unpack('<f', file.read(4))[0]

def read_double(file):
    """Reads an 8-byte double-precision float from the file."""
    return struct.unpack('<d', file.read(8))[0]

def read_windows_ticks(file):
    """Reads an 8-byte Windows Ticks value and converts it to an ISO string."""
    ticks = read_long(file)
    if ticks == 0:
        return None
    # Convert from 100-nanosecond intervals since 1/1/0001 to a datetime object
    return (datetime(1, 1, 1) + timedelta(microseconds=ticks / 10)).isoformat()

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
    """Reads a string from the file based on the osu! string format."""
    if read_byte(file) == 0x0b:
        length = read_uleb128(file)
        if length > 0:
            return file.read(length).decode('utf-8')
    return ""

def read_windows_ticks(file):
    """Reads an 8-byte Windows Ticks value and converts it to an ISO string."""
    ticks = read_long(file)
    if ticks == 0:
        return None
    try:
        # Convert from 100-nanosecond intervals since 1/1/0001 to a datetime object
        return (datetime(1, 1, 1) + timedelta(microseconds=ticks / 10)).isoformat()
    except OverflowError:
        # The date is invalid or out of the supported range, return None
        return None

def parse_replay_file(file_path):
    """Parses an .osr replay file and returns a dictionary of its data."""
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
        replay_data['max_combo'] = read_short(f)
        replay_data['is_perfect_combo'] = read_byte(f) != 0
        replay_data['mods_used'] = read_int(f)
        read_string(f)  # Life bar graph, not needed for now
        replay_data['played_at'] = read_windows_ticks(f)
        logging.debug(f"Parsed replay data from {os.path.basename(file_path)}: {replay_data}")
        return replay_data
        
def parse_osu_db(db_path):
    """Parses the osu!.db file and returns a dictionary of beatmaps keyed by MD5 hash."""
    beatmaps = {}
    with open(db_path, 'rb') as f:
        version = read_int(f)
        f.seek(4, 1) # folder_count
        f.seek(1, 1) # account_unlocked
        f.seek(8, 1) # unlock_date
        read_string(f) # player_name
        num_beatmaps = read_int(f)

        for _ in range(num_beatmaps):
            if version < 20191106:
                read_int(f)

            artist = read_string(f)
            read_string(f) # artist_unicode
            title = read_string(f)
            read_string(f) # title_unicode
            creator = read_string(f)
            difficulty = read_string(f)
            read_string(f) # audio_file
            md5_hash = read_string(f)
            osu_file_name = read_string(f)
            f.seek(1, 1) # ranked_status
            num_hitcircles = read_short(f)
            num_sliders = read_short(f)
            num_spinners = read_short(f)
            f.seek(8, 1) # last_mod_time

            if version < 20140609:
                ar, cs, hp, od = float(read_byte(f)), float(read_byte(f)), float(read_byte(f)), float(read_byte(f))
            else:
                ar, cs, hp, od = read_float(f), read_float(f), read_float(f), read_float(f)
            
            f.seek(8, 1) # slider_velocity
            if version >= 20140609:
                # Determine the size of the star rating pairs based on the db version
                pair_size = 10 if version >= 20250107 else 14
                for _ in range(4): # Star rating difficulties for different modes
                    num_pairs = read_int(f)
                    f.seek(num_pairs * pair_size, 1) # Skip the pairs data

            f.seek(12, 1) # drain_time, total_time, preview_time
            
            num_timing_points = read_int(f)
            bpm = 0.0
            found_bpm = False
            # We must iterate through all timing points to advance the file cursor correctly.
            for _ in range(num_timing_points):
                beat_length = read_double(f)
                read_double(f)  # offset
                # The boolean is non-zero (true) for uninherited timing points.
                is_uninherited = read_byte(f) != 0

                # The first uninherited point defines the BPM. Its beat_length is a positive
                # value representing milliseconds per beat. Inherited points have a negative value.
                if not found_bpm and is_uninherited and beat_length > 0:
                    bpm = 60000.0 / beat_length
                    found_bpm = True
            
            f.seek(12, 1) # difficulty_id, beatmap_id, thread_id
            grades = {"osu": read_byte(f), "taiko": read_byte(f), "ctb": read_byte(f), "mania": read_byte(f)}
            f.seek(7, 1) # local_offset, stack_leniency, gameplay_mode
            read_string(f) # song_source
            read_string(f) # song_tags
            f.seek(2, 1) # online_offset
            read_string(f) # font
            f.seek(1, 1) # is_unplayed
            last_played_date = read_windows_ticks(f) # Read last played time
            f.seek(1, 1) # is_osz2
            folder_name = read_string(f)
            f.seek(8, 1) # last_time_checked
            f.seek(5, 1) # ignore_flags
            if version < 20140609: f.seek(2, 1)
            f.seek(5, 1) # last_modification_time, mania_scroll_speed

            if md5_hash:
                beatmaps[md5_hash] = {
                    "artist": artist, "title": title, "creator": creator, "difficulty": difficulty,
                    "folder_name": folder_name, "osu_file_name": osu_file_name, "grades": grades,
                    "last_played_date": last_played_date,
                    "num_hitcircles": num_hitcircles, "num_sliders": num_sliders, "num_spinners": num_spinners,
                    "ar": round(ar, 2), "cs": round(cs, 2), "hp": round(hp, 2), "od": round(od, 2), "bpm": round(bpm, 2)
                }
    return beatmaps

def parse_osu_file(file_path):
    """
    Parses a .osu file to find audio/background filenames and min/max BPM.
    Note: This is a simplified parser and might not cover all edge cases.
    """
    data = {
        "audio_file": None, 
        "background_file": None,
        "bpm_min": None,
        "bpm_max": None
    }
    timing_bpms = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            current_section = ""
            for line in f:
                line = line.strip()
                if not line or line.startswith("//"):
                    continue
                
                if line.startswith('['):
                    current_section = line
                    continue

                if current_section == "[General]":
                    if line.startswith("AudioFilename:"):
                        data["audio_file"] = line.split(":", 1)[1].strip()
                
                elif current_section == "[Events]":
                    # [cite_start]Find the first background image entry [cite: 71, 76]
                    if data.get("background_file") is None and (line.startswith("0,0,") or line.startswith("Image,")):
                        parts = line.split(',')
                        if len(parts) >= 3:
                            data["background_file"] = parts[2].strip().strip('"')

                elif current_section == "[TimingPoints]":
                    parts = line.split(',')
                    if len(parts) < 8:
                        continue
                    
                    # [cite_start]An uninherited timing point defines a new BPM [cite: 110]
                    is_uninherited = parts[6].strip() == '1'
                    if is_uninherited:
                        # [cite_start]beatLength is the duration of a beat in milliseconds [cite: 103]
                        beat_length = float(parts[1].strip())
                        if beat_length > 0:
                            # [cite_start]Formula to convert beat length to BPM [cite: 126]
                            bpm = 60000.0 / beat_length
                            timing_bpms.append(bpm)
        
        if timing_bpms:
            data['bpm_min'] = min(timing_bpms)
            data['bpm_max'] = max(timing_bpms)

    except Exception as e:
        print(f"Warning: Could not parse {file_path}: {e}")
    return data

def calculate_pp(osu_file_path, replay_data):
    """Calculates PP and star rating for a given play using rosu-pp-py."""
    try:
        # Parse the beatmap file
        beatmap = rosu_pp_py.Beatmap(path=osu_file_path)

        # First, calculate the difficulty attributes (stars)
        diff_attrs = rosu_pp_py.Difficulty().calculate(beatmap)

        # Then, create a performance calculator with the score's details
        perf_calc = rosu_pp_py.Performance(
            n300=replay_data.get('num_300s'),
            n100=replay_data.get('num_100s'),
            n50=replay_data.get('num_50s'),
            n_geki=replay_data.get('num_gekis'),
            n_katu=replay_data.get('num_katus'),
            misses=replay_data.get('num_misses'),
            combo=replay_data.get('max_combo'),
        )
        
        # Calculate the performance attributes (pp) using the difficulty attributes
        # for better performance.
        perf_attrs = perf_calc.calculate(diff_attrs)
        
        pp_data = {
            "pp": perf_attrs.pp,
            "stars": diff_attrs.stars,
            "map_max_combo": diff_attrs.max_combo
        }
        logging.debug(f"Calculated PP data for {os.path.basename(osu_file_path)}: {pp_data}")
        return pp_data
    except Exception as e:
        # Return default values if calculation fails for any reason
        logging.error(f"Could not calculate PP for {osu_file_path}: {e}", exc_info=True)
        return {"pp": None, "stars": None, "map_max_combo": None}