# 3. rosu-pp-py Library Reference

## 3.1. Overview

`rosu-pp-py` is a high-performance Python binding for the `rosu-pp` Rust library. Its primary purpose is to calculate difficulty (star rating) and performance (pp) attributes for all osu! game modes. This document serves as a detailed technical reference for its public API.

## 3.2. Core Concepts

### 3.2.1. Mods

Mods are a central concept in osu! and this library. They can be specified in various ways, conforming to the `GameMods` type alias:

```python
from typing import List, Mapping, Optional, Union

GameMods = Union[int, str, 'GameMod', List[Union['GameMod', str, int]]]
GameMod = Mapping[str, Union[str, Optional['GameModSettings']]]
GameModSettings = Mapping[str, Union[bool, float, str]]
```

This means mods can be provided as:
-   An `int` representing the legacy bitmask (e.g., `8` for Hidden, `64` for DoubleTime, `72` for HDDT).
-   A `str` of case-insensitive acronyms (e.g., `"HDHR"`, `"dt"`).
-   A `GameMod` dictionary for lazer-style mods with custom settings (e.g., `{'acronym': 'DA', 'settings': {'ar': 9.5}}`).
-   A `list` containing a mix of the above types.

**Example:**
```python
# All of these are valid ways to specify Hidden + DoubleTime
mods_int = 8 + 64
mods_str = "HDDT"
mods_list = ["HD", "DT"]
```

### 3.2.2. Lazer vs. Stable

Some performance calculations, particularly for osu!standard and osu!mania, differ between the osu!(stable) and osu!(lazer) clients. All calculator classes (`Difficulty`, `Performance`) accept a `lazer: bool` keyword argument, which defaults to `True`. It is important to set this correctly based on the source of the score to ensure accurate calculations.

---

## 3.3. Enums

### 3.3.1. `GameMode`

An enum representing the four osu! game modes.

| Member | Integer Value |
| :--- | :--- |
| `GameMode.Osu` | 0 |
| `GameMode.Taiko` | 1 |
| `GameMode.Catch` | 2 |
| `GameMode.Mania` | 3 |

### 3.3.2. `HitResultPriority`

When generating hit results from just an accuracy value, this enum decides how the hits are distributed.

| Member | Description |
| :--- | :--- |
| `HitResultPriority.BestCase` | Assumes the best possible hit results for the given accuracy (Default). |
| `HitResultPriority.WorstCase`| Assumes the worst possible hit results for the given accuracy. |
| `HitResultPriority.Fastest` | Generates a valid hit result distribution quickly, without trying to optimize for best/worst pp. **Recommended for performance.** |

---

## 3.4. Main Classes

### 3.4.1. `Beatmap`

This class contains all beatmap data relevant for calculation, parsed from a `.osu` file.

**Instantiation:**
`Beatmap(**kwargs)` must be called with one of the following keyword arguments:
-   `path: str`: The path to a `.osu` file.
-   `content: Union[str, bytearray]`: The content of a `.osu` file as a string or bytes.
-   `bytes: bytearray`: The content of a `.osu` file as bytes.

*Raises `ParseError` if the file cannot be parsed.*

**Methods:**
-   `convert(mode: GameMode, mods: Optional[GameMods] = None) -> None`: Converts the beatmap to a different game mode, optionally applying mods during conversion. *Raises `ConvertError` on failure.*
-   `is_suspicious() -> bool`: Checks if the map contains unusual patterns that might cause performance issues during calculation (e.g., extremely high object density). It's recommended to call this before performing calculations on unknown maps.

**Properties:**

| Property | Type | Description |
| :--- | :--- | :--- |
| `mode` | `GameMode` | The game mode of the beatmap. |
| `version` | `int` | The beatmap format version from the `.osu` file. |
| `is_convert`| `bool` | Whether the beatmap is a conversion from another mode. |
| `bpm` | `float` | The primary Beats Per Minute of the map. |
| `ar` | `float` | Approach Rate. |
| `cs` | `float` | Circle Size. |
| `hp` | `float` | HP Drain Rate. |
| `od` | `float` | Overall Difficulty. |
| `stack_leniency`| `float` | How lenient stacks are. |
| `slider_multiplier`| `float` | Base slider velocity. |
| `slider_tick_rate`| `float` | How often slider ticks appear. |
| `n_objects` | `int` | Total number of hit objects. |
| `n_circles` | `int` | Total number of circles. |
| `n_sliders` | `int` | Total number of sliders. |
| `n_spinners` | `int` | Total number of spinners. |
| `n_holds` | `int` | Total number of hold notes (mania-specific). |
| `n_breaks` | `int` | Total number of break periods. |

### 3.4.2. `ScoreState`

An object holding the hit statistics and combo of a score. Used for gradual performance calculations.

**Instantiation:** `ScoreState(**kwargs)`

**Properties:**

| Property | Type | Description |
| :--- | :--- | :--- |
| `max_combo` | `int` | Maximum combo achieved. |
| `n300` | `int` | Number of 300s (Greats). |
| `n100` | `int` | Number of 100s (Oks). |
| `n50` | `int` | Number of 50s (Mehs). |
| `misses` | `int` | Number of misses. |
| `n_geki` | `int` | Number of Gekis (320s in mania). |
| `n_katu` | `int` | Number of Katus (200s in mania, tiny droplet misses in catch). |
| `osu_large_tick_hits`| `int` | **osu!lazer specific:** Hits on slider heads, ticks, and repeats (with CL mod). |
| `osu_small_tick_hits`| `int` | **osu!lazer specific:** Hits on slider ends. |
| `slider_end_hits` | `int` | **osu!lazer specific:** Hits on slider ends. |

---

## 3.5. Calculators

These classes follow a builder pattern. You instantiate them with initial settings, can modify them with `set_*` methods, and then call a final method like `calculate()` or `build()`.

### 3.5.1. `Difficulty`

A builder for calculating `DifficultyAttributes` and `Strains`.

**Instantiation:** `Difficulty(**kwargs)`
-   Accepts mods (`mods`), `clock_rate`, `passed_objects`, `hardrock_offsets`, `lazer`, and beatmap attributes (`ar`, `cs`, `hp`, `od`) with corresponding `_with_mods` booleans.

**Methods:**
-   `calculate(map: Beatmap) -> DifficultyAttributes`: Performs the main difficulty calculation.
-   `strains(map: Beatmap) -> Strains`: Calculates strain values over time, suitable for plotting.
-   `performance() -> Performance`: Creates a `Performance` calculator with the same difficulty settings.
-   `gradual_difficulty(map: Beatmap) -> GradualDifficulty`: Creates a gradual difficulty calculator.
-   `gradual_performance(map: Beatmap) -> GradualPerformance`: Creates a gradual performance calculator.
-   `set_...()`: A full suite of setter methods is available to modify the calculator's state after instantiation.

### 3.5.2. `Performance`

A builder for calculating `PerformanceAttributes`.

**Instantiation:** `Performance(**kwargs)`
-   Accepts all arguments from `Difficulty`.
-   Also accepts score-specific arguments: `accuracy`, `combo`, `misses`, hit counts (`n300`, `n100`, etc.), and `hitresult_priority`.

**Methods:**
-   `calculate(arg) -> PerformanceAttributes`: Performs the performance calculation. The `arg` can be a `Beatmap`, `DifficultyAttributes`, or `PerformanceAttributes` object. Providing pre-calculated attributes is significantly faster than providing a `Beatmap`.
-   `difficulty() -> Difficulty`: Creates a `Difficulty` calculator with the same difficulty settings.
-   `set_...()`: A full suite of setter methods for all difficulty and performance parameters.

### 3.5.3. `GradualDifficulty`

An iterator that calculates difficulty attributes after each successive hit object.

**Instantiation:** Not instantiated directly. Created via `Difficulty.gradual_difficulty(map)`.

**Methods:**
-   `next() -> Optional[DifficultyAttributes]`: Returns attributes after the next object, or `None` if finished.
-   `nth(n: int) -> Optional[DifficultyAttributes]`: Returns the nth attribute set from the current position.

### 3.5.4. `GradualPerformance`

Calculates performance attributes gradually as a score is being played.

**Instantiation:** Not instantiated directly. Created via `Difficulty.gradual_performance(map)`.

**Methods:**
-   `next(state: ScoreState) -> Optional[PerformanceAttributes]`: Calculates PP for the next object given the *new* total score state.
-   `nth(state: ScoreState, n: int) -> Optional[PerformanceAttributes]`: Processes the next `n` objects.

### 3.5.5. `BeatmapAttributesBuilder`

Calculates a map's base attributes (`AR`, `OD`, etc.) after applying mods or other custom settings.

**Instantiation:** `BeatmapAttributesBuilder(**kwargs)`
-   Accepts `map`, `mode`, `is_convert`, `mods`, `clock_rate`, and attribute overrides.

**Methods:**
-   `build() -> BeatmapAttributes`: Returns the final calculated attributes.
-   `set_...()`: Setters to configure the builder.

---

## 3.6. Result Objects

These are immutable ("frozen") data classes returned by the calculators.

### 3.6.1. `DifficultyAttributes`

The result of a difficulty calculation.

| Property | Type | Game Mode(s) | Description |
| :--- | :--- | :--- | :--- |
| `mode` | `GameMode` | All | The game mode of these attributes. |
| `stars` | `float` | All | The final star rating. |
| `max_combo` | `int` | All | Maximum possible combo. |
| `is_convert` | `bool` | All | Whether the map was a convert. |
| `aim` | `float` | osu! | The difficulty of the aim skill. |
| `speed` | `float` | osu! | The difficulty of the speed skill. |
| `flashlight` | `float` | osu! | The difficulty of the flashlight skill. |
| `slider_factor` | `float` | osu! | Ratio of aim strain with and without sliders. |
| `speed_note_count`| `float` | osu! | Number of objects weighted by speed difficulty. |
| `aim_difficult_slider_count`|`float`| osu! | Number of sliders weighted by difficulty. |
| `aim_difficult_strain_count`|`float`| osu! | Weighted sum of aim strains. |
| `speed_difficult_strain_count`|`float`| osu! | Weighted sum of speed strains. |
| `ar` | `float` | osu!, Catch | The final Approach Rate after mods. |
| `od` | `float` | osu! | The final Overall Difficulty after mods. |
| `hp` | `float` | osu! | The final HP Drain Rate after mods. |
| `great_hit_window` | `float` | osu!, Taiko | Time window (ms) for a "Great" (300) hit. |
| `ok_hit_window` | `float` | osu!, Taiko | Time window (ms) for an "Ok" (100) hit. |
| `meh_hit_window` | `float` | osu! | Time window (ms) for a "Meh" (50) hit. |
| `n_circles` | `int` | osu! | The number of circles. |
| `n_sliders` | `int` | osu! | The number of sliders. |
| `n_spinners` | `int` | osu! | The number of spinners. |
| `n_large_ticks`| `int` | osu! | Number of slider ticks and repeats. |
| `stamina` | `float` | Taiko | The difficulty of the stamina skill. |
| `single_color_stamina`| `float`| Taiko | Stamina difficulty of single-color sections. |
| `rhythm` | `float` | Taiko | The difficulty of the rhythm skill. |
| `color` | `float` | Taiko | The difficulty of the color-change skill. |
| `reading` | `float` | Taiko | The difficulty of pattern reading. |
| `n_fruits` | `int` | Catch | The number of fruits. |
| `n_droplets` | `int` | Catch | The number of droplets. |
| `n_tiny_droplets`| `int` | Catch | The number of tiny droplets. |
| `n_objects` | `int` | Mania | The total number of notes. |
| `n_hold_notes` | `int` | Mania | The number of hold notes. |

### 3.6.2. `PerformanceAttributes`

The result of a performance calculation.

| Property | Type | Game Mode(s) | Description |
| :--- | :--- | :--- | :--- |
| `difficulty` | `DifficultyAttributes`| All | The difficulty attributes used for this calculation. |
| `pp` | `float` | All | The final performance points (pp). |
| `pp_aim` | `float` | osu! | The aim portion of the final pp. |
| `pp_speed` | `float` | osu! | The speed portion of the final pp. |
| `pp_accuracy` | `float` | osu!, Taiko | The accuracy portion of the final pp. |
| `pp_flashlight` | `float` | osu! | The flashlight portion of the final pp. |
| `pp_difficulty` | `float` | Taiko, Mania | The strain/difficulty portion of the final pp. |
| `effective_miss_count`| `float` | osu!, Taiko | Miss count, scaled by total hits. |
| `speed_deviation`| `float` | osu! | Approximated unstable rate of the play. |
| `estimated_unstable_rate`|`float`| Taiko | Upper bound on the player's tap deviation. |
| `state`| `ScoreState`| All | The score state used. Not available for gradual calculations. |

### 3.6.3. `Strains`

Contains strain values for each skill, useful for plotting difficulty over time.

| Property | Type | Game Mode(s) | Description |
| :--- | :--- | :--- | :--- |
| `mode` | `GameMode` | All | The game mode of these strains. |
| `section_length` | `float` | All | The time in milliseconds between each strain value. |
| `aim` | `List[float]` | osu! | Strain values for the aim skill. |
| `aim_no_sliders` | `List[float]` | osu! | Strain values for aim, ignoring sliders. |
| `speed` | `List[float]` | osu! | Strain values for the speed skill. |
| `flashlight` | `List[float]` | osu! | Strain values for the flashlight skill. |
| `stamina` | `List[float]` | Taiko | Strain values for the stamina skill. |
| `rhythm` | `List[float]` | Taiko | Strain values for the rhythm skill. |
| `color` | `List[float]` | Taiko | Strain values for the color skill. |
| `reading` | `List[float]` | Taiko | Strain values for the reading skill. |
| `single_color_stamina`|`List[float]`| Taiko | Strain values for single-color stamina. |
| `movement` | `List[float]` | Catch | Strain values for the movement skill. |
| `strains` | `List[float]` | Mania | Strain values for the overall strain skill. |

### 3.6.4. `BeatmapAttributes`

The result of `BeatmapAttributesBuilder.build()`. Contains the final map values after mods and overrides.

| Property | Type | Description |
| :--- | :--- | :--- |
| `ar` | `float` | Final Approach Rate. |
| `od` | `float` | Final Overall Difficulty. |
| `cs` | `float` | Final Circle Size. |
| `hp` | `float` | Final HP Drain Rate. |
| `clock_rate` | `float` | Final clock rate. |
| `ar_hit_window` | `float` | The approach time in milliseconds. |
| `od_great_hit_window` | `float` | Time window (ms) to hit a 300 ("Great"). |
| `od_ok_hit_window` | `float` | Time window (ms) to hit a 100 ("Ok"). |
| `od_meh_hit_window` | `float` | Time window (ms) to hit a 50 ("Meh"). (osu! only) |