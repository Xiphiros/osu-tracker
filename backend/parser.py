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
    (Source: osr_reference.pdf, "String" data type)
    """
    if read_byte(file) == 0x0b:
        length = read_uleb128(file)
        return file.read(length).decode('utf-8')
    return None

def parse_replay_file(file_path):
    """
    Parses an .osr replay file and returns a dictionary of its data.
    This function reads data fields in the order specified by osr_reference.pdf.
    """
    with open(file_path, 'rb') as f:
        replay_data = {}
        
        # (Source: osr_reference.pdf, "Format" table)
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

if __name__ == '__main__':
    try:
        replay = parse_replay_file('test.osr')
        for key, value in replay.items():
            print(f"{key}: {value}")
    except FileNotFoundError:
        print("Test file 'test.osr' not found.")
        print("Please place a replay file in the root directory to test the parser.")
    except Exception as e:
        print(f"An error occurred: {e}")