# 2. Data Formats

This document provides a complete specification for the proprietary osu! file formats based on the provided reference documentation. It is intended to be an accurate technical reference for future development.

## 2.1. osu! Database File (`osu!.db`)

The `osu!.db` file is a binary file that contains a cached version of information about all beatmaps installed in the `Songs` folder.

### Data Types

These are the primitive data types used in the file format. All numerical types are little-endian and unsigned unless specified.

| Name | Bytes | Description |
| :--- | :--- | :--- |
| `Byte` | 1 | 8-bit integer. |
| `Short` | 2 | 16-bit integer. |
| `Int` | 4 | 32-bit integer. |
| `Long` | 8 | 64-bit integer. |
| `ULEB128` | Var. | Variable-length integer. |
| `Single` | 4 | 32-bit IEEE floating point value. |
| `Double` | 8 | 64-bit IEEE floating point value. |
| `Boolean` | 1 | `0x00` for false, non-zero for true. |
| `String` | Var. | Starts with a `Byte`. If `0x00`, the string is not present. If `0x0b`, it's followed by a ULEB128 for length, then the UTF-8 string. |
| `DateTime`| 8 | A 64-bit integer for Windows Ticks (100-nanosecond intervals since 0001-01-01). |

### File Structure

#### Header

| Data Type | Description |
| :--- | :--- |
| `Int` | osu! client version (e.g., `20150203`). |
| `Int` | Number of beatmap folders. |
| `Boolean`| Indicates if the user's account is unlocked. |
| `DateTime`| Date the account will be unlocked. |
| `String` | Player's username. |
| `Int` | Number of beatmap entries that follow. |

#### Beatmap Entry

This structure is repeated for the number of beatmaps specified in the header.

| Data Type | Description |
| :--- | :--- |
| `Int` | Size in bytes of this beatmap entry. Only present if DB version is less than `20191106`. |
| `String` | Artist name. |
| `String` | Artist name, in Unicode. |
| `String` | Song title. |
| `String` | Song title, in Unicode. |
| `String` | Creator/Mapper name. |
| `String` | Difficulty name (e.g., "Hard", "Insane"). |
| `String` | Audio filename. |
| `String` | MD5 hash of the beatmap. |
| `String` | Name of the `.osu` file for this difficulty. |
| `Byte` | Ranked status (0=unknown, 1=unsubmitted, 2=pending/wip/graveyard, 4=ranked, 5=approved, 6=qualified, 7=loved). |
| `Short` | Number of hit circles. |
| `Short` | Number of sliders. |
| `Short` | Number of spinners. |
| `Long` | Last modification time (Windows Ticks). |
| `Byte`/`Single` | Approach Rate (AR). `Byte` if version < `20140609`, `Single` otherwise. |
| `Byte`/`Single` | Circle Size (CS). `Byte` if version < `20140609`, `Single` otherwise. |
| `Byte`/`Single` | HP Drain (HP). `Byte` if version < `20140609`, `Single` otherwise. |
| `Byte`/`Single` | Overall Difficulty (OD). `Byte` if version < `20140609`, `Single` otherwise. |
| `Double` | Slider velocity. |
| `List` | Star ratings for osu!standard (Int-Double pairs before version `20250107`, Int-Float pairs after). |
| `List` | Star ratings for Taiko (Int-Double pairs before version `20250107`, Int-Float pairs after). |
| `List` | Star ratings for CTB (Int-Double pairs before version `20250107`, Int-Float pairs after). |
| `List` | Star ratings for osu!mania (Int-Double pairs before version `20250107`, Int-Float pairs after). |
| `Int` | Drain time, in seconds. |
| `Int` | Total time, in milliseconds. |
| `Int` | Audio preview start time, in milliseconds. |
| `List` | Timing points. |
| `Int` | Difficulty ID. |
| `Int` | Beatmap ID. |
| `Int` | Thread ID. |
| `Byte` | Grade achieved in osu!standard. |
| `Byte` | Grade achieved in Taiko. |
| `Byte` | Grade achieved in CTB. |
| `Byte` | Grade achieved in osu!mania. |
| `Short` | Local beatmap offset. |
| `Single`| Stack leniency. |
| `Byte` | osu! gameplay mode (0=osu!, 1=Taiko, 2=Catch, 3=Mania). |
| `String`| Song source. |
| `String`| Song tags. |
| `Short` | Online offset. |
| `String`| Font used for the song title. |
| `Boolean`| Is the beatmap unplayed. |
| `Long` | Last time the beatmap was played. |
| `Boolean`| Is the beatmap osz2 format. |
| `String`| Folder name of the beatmap, relative to the Songs folder. |
| `Long` | Last time beatmap was checked against the osu! repository. |
| `Boolean`| Ignore beatmap sound. |
| `Boolean`| Ignore beatmap skin. |
| `Boolean`| Disable storyboard. |
| `Boolean`| Disable video. |
| `Boolean`| Visual override. |
| `Int` | Last modification time (?). |
| `Byte` | Mania scroll speed. |

---

## 2.2. osu! Replay File (`.osr`)

The `.osr` file stores a recording of a player's performance.

### File Structure

| Data Type | Description |
| :--- | :--- |
| `Byte` | Game mode (0=osu!, 1=Taiko, 2=Catch, 3=Mania). |
| `Int` | Game version when replay was created (e.g., `20131216`). |
| `String` | MD5 hash of the beatmap played. |
| `String` | Player's username. |
| `String` | MD5 hash of this replay file. |
| `Short` | Number of 300s scored. |
| `Short` | Number of 100s scored. |
| `Short` | Number of 50s scored. |
| `Short` | Number of "Gekis". |
| `Short` | Number of "Katus". |
| `Short` | Number of misses. |
| `Int` | Total score achieved. |
| `Short` | Highest combo achieved. |
| `Byte` | Whether the combo was "perfect" (1 for true, 0 for false). |
| `Int` | Bitmask integer representing mods used. |
| `String` | Life bar graph: a comma-separated string of `time|health` pairs. |
| `Long` | Timestamp of when the play occurred (Windows Ticks). |
| `Int` | Length in bytes of the compressed replay data that follows. |
| `Byte[]` | LZMA-compressed stream of cursor movements and key presses. |
| `Long` | Online Score ID. |

---

## 2.3. osu! Beatmap File (`.osu`)

The `.osu` file is a human-readable text file containing all information for a single beatmap difficulty.

### File Sections

#### `[General]`
General information about the beatmap.

| Key | Description |
| :--- | :--- |
| `AudioFilename`| Location of the audio file. |
| `AudioLeadIn` | Milliseconds of silence before audio starts. |
| `PreviewTime` | Time in ms where audio preview should start. |
| `Countdown` | Speed of the countdown before the first object. |
| `SampleSet` | Default sample set (Normal, Soft, Drum). |
| `StackLeniency`| Multiplier for stacking threshold. |
| `Mode` | Gameplay mode for the beatmap. |
| `LetterboxInBreaks` | Enables letterboxing effect during breaks. |
| `UseSkinSprites` | Allows the storyboard to use the user's skin images. |
| `OverlayPosition`| Draw order of hit circle overlays. |
| `SkinPreference` | Preferred skin to use. |
| `EpilepsyWarning`| Shows a warning for flashing colours. |
| `CountdownOffset`| Number of beats for the countdown offset. |
| `SpecialStyle` | Enables N+1 key layout for osu!mania. |
| `WidescreenStoryboard`| Allows widescreen viewing for storyboards. |
| `SamplesMatchPlaybackRate` | Samples change rate with speed-changing mods. |

#### `[Editor]`
Editor-specific settings that do not affect gameplay.

| Key | Description |
| :--- | :--- |
| `Bookmarks` | Comma-separated list of bookmarked times in ms. |
| `DistanceSpacing` | Distance snap multiplier. |
| `BeatDivisor` | Beat snap divisor. |
| `GridSize` | Grid size. |
| `TimelineZoom` | Scale factor for the object timeline. |

#### `[Metadata]`
Information to identify the beatmap.

| Key | Description |
| :--- | :--- |
| `Title` | Romanised song title. |
| `TitleUnicode` | Song title in its original language. |
| `Artist` | Romanised song artist. |
| `ArtistUnicode` | Song artist in their original language. |
| `Creator` | Beatmap creator's username. |
| `Version` | Difficulty name. |
| `Source` | Original media the song was from. |
| `Tags` | Space-separated list of search terms. |
| `BeatmapID` | The beatmap's difficulty ID. |
| `BeatmapSetID` | The beatmap's set ID. |

#### `[Difficulty]`
Difficulty settings for the beatmap.

| Key | Description |
| :--- | :--- |
| `HPDrainRate` | HP setting (0-10). |
| `CircleSize` | CS setting (0-10). |
| `OverallDifficulty` | OD setting (0-10). |
| `ApproachRate` | AR setting (0-10). |
| `SliderMultiplier` | Base slider velocity multiplier. |
| `SliderTickRate` | Number of slider ticks per beat. |

#### `[Events]`
Beatmap and storyboard events. The syntax is `eventType,startTime,eventParams`.
-   **Backgrounds**: `0,0,"filename.jpg",xOffset,yOffset`
-   **Videos**: `Video,startTime,"filename.mp4",xOffset,yOffset`
-   **Breaks**: `2,startTime,endTime`

#### `[TimingPoints]`
Timing and control points, sorted chronologically. Syntax is `time,beatLength,meter,sampleSet,sampleIndex,volume,uninherited,effects`.
-   **Uninherited (Red) Points**: `uninherited` is 1. `beatLength` is positive and defines the milliseconds per beat. Sets BPM and time signature.
-   **Inherited (Green) Points**: `uninherited` is 0. `beatLength` is a negative inverse slider velocity multiplier.

#### `[Colours]`
Custom combo and skin colours.

| Key | Description |
| :--- | :--- |
| `Combo#` | Additive combo colours (RGB triplet). |
| `SliderTrackOverride` | Additive slider track colour (RGB triplet). |
| `SliderBorder` | Slider border colour (RGB triplet). |

#### `[HitObjects]`
All hit objects in the map. Syntax is `x,y,time,type,hitSound,objectParams,hitSample`.
-   **`type`**: An 8-bit integer flag: bit 0 for circle, 1 for slider, 3 for spinner, 7 for mania hold.
-   **`hitSound`**: A bit flag for hitsounds: bit 0 for normal, 1 for whistle, 2 for finish, 3 for clap.
-   **Sliders**: `objectParams` format is `curveType|curvePoints,slides,length,edgeSounds,edgeSets`.
-   **Spinners**: `objectParams` is simply `endTime`.
-   **osu!mania Holds**: `objectParams` is `endTime`. The `x` coordinate determines the column.