# 2. Data Formats

This document outlines the structure of proprietary data formats used in the application, based on official documentation and the project's parsing implementation.

## 2.1. osu! Database File (`osu!.db`)

The `osu!.db` file is a binary file that contains a cached version of information about all beatmaps installed in the `Songs` folder. The application parses this file to quickly build a cache of beatmap details without needing to read every individual `.osu` file on startup.

The file consists of a header followed by a variable number of beatmap entries.

### Data Types

The parser reads the following primitive data types, all stored in little-endian format unless specified:

| Name | Bytes | Description |
| :--- | :--- | :--- |
| `Byte` | 1 | An 8-bit unsigned integer. |
| `Short` | 2 | A 16-bit unsigned integer. |
| `Int` | 4 | A 32-bit unsigned integer. |
| `Long` | 8 | A 64-bit unsigned integer. |
| `Float` | 4 | A 32-bit IEEE floating point number. |
| `Double` | 8 | A 64-bit IEEE floating point number. |
| `String` | Var. | A custom string format starting with a `0x0b` byte, followed by a ULEB128-encoded length, and then the UTF-8 encoded string content. |
| `DateTime` | 8 | A 64-bit integer representing Windows Ticks (100-nanosecond intervals since 0001-01-01). The parser converts this to an ISO 8601 string. |

### File Structure

#### Header

| Data Type | Description |
| :--- | :--- |
| `Int` | osu! client version (e.g., `20150203`). |
| `Int` | Number of beatmap folders in the `Songs` directory. |
| `Boolean` | Account lock/ban status. |
| `DateTime` | Date the account will be unlocked. |
| `String` | Player's username. |
| `Int` | The number of beatmap entries that follow. |

#### Beatmap Entry

This structure is repeated for the number of beatmaps specified in the header.

| Data Type | Description | Parser Notes |
| :--- | :--- | :--- |
| `String` | Artist name. | Read and stored. |
| `String` | Artist name (Unicode). | Skipped. |
| `String` | Song title. | Read and stored. |
| `String` | Song title (Unicode). | Skipped. |
| `String` | Creator/Mapper name. | Read and stored. |
| `String` | Difficulty name (e.g., "Insane"). | Read and stored. |
| `String` | Audio filename (e.g., `audio.mp3`). | Skipped (read from `.osu` file instead). |
| `String` | MD5 hash of the beatmap file. | Read and used as the primary key for the cache. |
| `String` | Filename of the `.osu` difficulty file. | Read and stored. |
| `Byte` | Ranked status (0-7). | Skipped. |
| `Short` | Number of hit circles. | Read and stored. |
| `Short` | Number of sliders. | Read and stored. |
| `Short` | Number of spinners. | Read and stored. |
| `Long` | Last modification time (Windows Ticks). | Skipped. |
| `Float` | Approach Rate (AR). | Read as `Float` or `Byte` based on DB version. |
| `Float` | Circle Size (CS). | Read as `Float` or `Byte` based on DB version. |
| `Float` | HP Drain (HP). | Read as `Float` or `Byte` based on DB version. |
| `Float` | Overall Difficulty (OD). | Read as `Float` or `Byte` based on DB version. |
| `Double`| Base slider velocity. | Skipped. |
| `List`| Star ratings for various mod combinations. | Skipped entirely to advance the file cursor. |
| `Int` | Drain time in seconds. | Skipped. |
| `Int` | Total time in milliseconds. | Skipped. |
| `Int` | Audio preview start time in ms. | Skipped. |
| `List`| Timing points. | Parsed to find the initial BPM. The parser iterates through all points, finds the first uninherited point, and calculates BPM as `60000.0 / beat_length`. |
| `Int` | Difficulty ID. | Skipped. |
| `Int` | Beatmap ID. | Skipped. |
| `Int` | Thread ID. | Skipped. |
| `Byte` | Grade achieved in osu!. | Stored as part of a `grades` dictionary. |
| `Byte` | Grade achieved in Taiko. | Stored as part of a `grades` dictionary. |
| `Byte` | Grade achieved in CTB. | Stored as part of a `grades` dictionary. |
| `Byte` | Grade achieved in Mania. | Stored as part of a `grades` dictionary. |
| `Short` | Local beatmap offset. | Skipped. |
| `Single`| Stack leniency. | Skipped. |
| `Byte` | Gameplay mode. | Skipped. |
| `String`| Song source. | Skipped. |
| `String`| Song tags. | Skipped. |
| `Short` | Online offset. | Skipped. |
| `String`| Font used for song title. | Skipped. |
| `Bool` | Is beatmap unplayed. | Skipped. |
| `Long` | Last time played (Windows Ticks). | Read and stored. |
| `Bool` | Is the beatmap osz2. | Skipped. |
| `String`| Folder name relative to `Songs` dir. | Read and stored. |

---

## 2.2. osu! Replay File (`.osr`)

The `.osr` file is a binary format that stores a recording of a player's performance on a specific beatmap. The application scans the osu! `Data/r` directory, parses these files, and stores them in its own `osu_tracker.db` database.

### File Structure

The format is a sequential list of fields.

| Data Type | Description |
| :--- | :--- |
| `Byte` | Game mode (0=osu!, 1=Taiko, 2=CTB, 3=Mania). |
| `Int` | Game version when replay was created (e.g., `20131216`). |
| `String` | MD5 hash of the beatmap played. |
| `String` | Player's username. |
| `String` | MD5 hash of the replay itself. |
| `Short` | Number of 300s scored. |
| `Short` | Number of 100s/150s scored. |
| `Short` | Number of 50s scored. |
| `Short` | Number of "Gekis" (300s in Mania). |
| `Short` | Number of "Katus" (200s in Mania). |
| `Short` | Number of misses. |
| `Int` | Total score achieved. |
| `Short` | Highest combo achieved. |
| `Byte` | Whether the combo was "perfect" (1 for true, 0 for false). |
| `Int` | Bitmask integer representing mods used (e.g., HD, HR). |
| `String` | Life bar graph data (skipped by parser). |
| `Long` | Timestamp of when the play occurred (Windows Ticks). |
| `Int` | Length of the compressed replay data that follows. |
| `Byte[]` | LZMA-compressed stream of cursor movements and key presses (skipped). |

---

## 2.3. osu! Beatmap File (`.osu`)

The `.osu` file is a human-readable text file that contains all information about a single difficulty of a beatmap. The application parses these files on-demand to retrieve details not present in `osu!.db`, such as background images, audio files, and detailed BPM changes.

The file is organized into sections denoted by bracketed headers (e.g., `[General]`).

### File Sections

#### `[General]`
General information about the beatmap.
- **`AudioFilename`**: Location of the audio file. The parser reads this to enable the audio preview feature.

#### `[Editor]`
Saved settings for the beatmap editor.
- This section is ignored by the parser.

#### `[Metadata]`
Information used to identify the beatmap.
- `Title`, `Artist`, `Creator`, `Version`. The application gets this data from `osu!.db` instead.

#### `[Difficulty]`
Difficulty settings like `HPDrainRate`, `CircleSize`, `OverallDifficulty`, and `ApproachRate`.
- The application gets this data from `osu!.db` instead.

#### `[Events]`
Beatmap and storyboard graphic events.
- The parser reads this section to find the background image file, looking for lines starting with `0,0,`.

#### `[TimingPoints]`
Defines BPM, time signatures, and slider velocity changes. The format is a comma-separated list: `time,beatLength,meter,sampleSet,sampleIndex,volume,uninherited,effects`.
- The parser reads all **uninherited** timing points (`uninherited` flag is `1`).
- An uninherited point has a positive `beatLength` value, which is the duration of a single beat in milliseconds. BPM is calculated as `60000.0 / beatLength`.
- The parser gathers all BPM changes to determine a `bpm_min`, `bpm_max`, and a primary `bpm` (the one with the longest duration during gameplay).

#### `[HitObjects]`
Contains all the hit objects (circles, sliders, spinners) for the map.
- The parser reads this section to find the timestamp of the very last object in the map (`last_object_time`). This value is critical for calculating the duration of each BPM section accurately.