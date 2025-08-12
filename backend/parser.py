import struct
import lzma
from datetime import datetime

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
            # The beatmap entry size is only present in older versions
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
            read_string(f) # osu_file_name
            f.seek(1, 1) # ranked_status
            
            num_hitcircles = read_short(f)
            num_sliders = read_short(f)
            num_spinners = read_short(f)
            
            f.seek(8, 1) # last_mod_time

            # Difficulty stats data type varies by version
            if version < 20140609:
                ar = float(read_byte(f))
                cs = float(read_byte(f))
                hp = float(read_byte(f))
                od = float(read_byte(f))
            else:
                ar = read_float(f)
                cs = read_float(f)
                hp = read_float(f)
                od = read_float(f)
            
            f.seek(8, 1) # slider_velocity

            # Star rating pairs vary by version
            if version >= 20140609:
                for _ in range(4): # For each game mode
                    num_pairs = read_int(f)
                    pair_size = 14 if version < 20250107 else 10 
                    f.seek(num_pairs * pair_size, 1)

            f.seek(4, 1) # drain_time
            f.seek(4, 1) # total_time
            f.seek(4, 1) # preview_time

            num_timing_points = read_int(f)
            bpm = 0.0
            for i in range(num_timing_points):
                tp_bpm = read_double(f)
                read_double(f) # offset
                tp_inherited = read_byte(f)
                # Found the first non-inherited timing point, which dictates the main BPM
                if not tp_inherited: 
                    if tp_bpm > 0:
                        bpm = 60000.0 / tp_bpm
                    # Seek past remaining points and break
                    f.seek((num_timing_points - 1 - i) * 17, 1)
                    break
                elif i == 0: # Fallback to first timing point if all are inherited
                    if tp_bpm > 0:
                        bpm = 60000.0 / tp_bpm

            f.seek(4, 1) # difficulty_id
            f.seek(4, 1) # beatmap_id
            f.seek(4, 1) # thread_id
            f.seek(4, 1) # grade_achieved
            f.seek(2, 1) # local_offset
            f.seek(4, 1) # stack_leniency
            f.seek(1, 1) # gameplay_mode

            read_string(f) # song_source
            read_string(f) # song_tags
            f.seek(2, 1) # online_offset
            read_string(f) # font
            f.seek(1, 1) # is_unplayed
            f.seek(8, 1) # last_time_played
            f.seek(1, 1) # is_osz2
            
            folder_name = read_string(f)
            
            f.seek(8, 1) # last_time_checked
            f.seek(5, 1) # ignore_flags
            
            if version < 20140609:
                f.seek(2, 1)

            f.seek(4, 1) # last_modification_time
            f.seek(1, 1) # mania_scroll_speed

            if md5_hash:
                beatmaps[md5_hash] = {
                    "artist": artist,
                    "title": title,
                    "creator": creator,
                    "difficulty": difficulty,
                    "folder_name": folder_name,
                    "num_hitcircles": num_hitcircles,
                    "num_sliders": num_sliders,
                    "num_spinners": num_spinners,
                    "total_objects": num_hitcircles + num_sliders + num_spinners,
                    "ar": round(ar, 2),
                    "cs": round(cs, 2),
                    "hp": round(hp, 2),
                    "od": round(od, 2),
                    "bpm": round(bpm, 2)
                }
    return beatmaps