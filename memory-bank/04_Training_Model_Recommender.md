# 4. Training Model & Recommender

## 4.1. Purpose & Philosophy

The Training Recommender is designed to provide a structured, consistent, and incremental path for skill improvement in osu!standard. It is based on a session-based training methodology focused on gradually pushing a player's skill ceiling.

The core philosophy is to find the "edge" of a player's current ability (represented by a Star Rating) and consistently practice within that narrow band, moving it slightly up or down based on performance. This avoids the common pitfalls of jumping between wildly different difficulties, promoting more focused and efficient improvement.

## 4.2. Core Logic

### 4.2.1. Inputs

The model requires four primary user inputs to begin a session:
1.  **Target Star Rating (SR):** The difficulty level the player wants to start at. This can be entered manually or suggested by the application.
2.  **Max BPM:** The maximum "main" BPM the player is comfortable playing at for the session.
3.  **Mods:** The user can select a combination of mods (EZ, HD, HR, DT, HT, FL) to train.
4.  **Skill Focus:** The user can specify a type of skill to target. See Section 4.4 for the list of focuses and their logic.

### 4.2.2. Search Criteria

When a recommendation is requested, the system searches the local beatmap database for a **single, random map** that meets the following criteria after calculating mod-adjusted difficulty with `rosu-pp-py`:
-   **Game Mode:** Must be osu!standard (`game_mode = 0`).
-   **Star Rating:** Must be within a narrow range: `modded_stars >= Target SR` and `modded_stars < Target SR + 0.15`.
-   **BPM:** The map's mod-adjusted main BPM must be less than or equal to the specified Max BPM (`modded_bpm <= Max BPM`).
-   **Skill Focus Filter:** An advanced heuristic is applied based on the user's selected focus. See Section 4.4.

## 4.3. Session Flow

The current implementation requires manual user feedback to guide the session.
1.  **Initialization:** The user selects their desired mods and skill focus, and enters their starting SR and Max BPM.
2.  **Request:** The user clicks "Find a map". The system finds and displays a suitable beatmap.
3.  **Play:** The user plays the recommended map in the osu! client.
4.  **Feedback:** The user returns to the tracker and reports whether they passed or failed their personal goal for that map, which adjusts the session SR accordingly.

## 4.4. Skill Focus Categories & Heuristics

To provide meaningful recommendations, we use a set of five distinct skill categories. Each category uses a specific heuristic based on detailed metrics from `rosu-pp` to filter maps.

### 4.4.1. Key Metrics

-   **`aim` & `speed`**: The peak difficulty values for aim and speed skills.
-   **`slider_factor`**: A ratio (<= 1.0) of how much aim strain is preserved in sliders. A value near 1.0 means sliders are as aim-intensive as jumps.
-   **`speed_note_count`**: The number of notes weighted by their speed difficulty. A high value indicates a map is tap-heavy.
-   **`aim_difficult_slider_count`**: The raw, weighted difficulty sum of all sliders. A high value indicates a map has complex sliders.
-   **`n_sliders` & `n_objects`**: Raw counts of sliders and total hitobjects, used for normalization.

### 4.4.2. Skill Focus Definitions

This is the definitive set of skill focuses to be implemented in the recommender.

1.  **Balanced**
    -   **Description**: A generalist category with no specific skill filtering. Provides a variety of maps.
    -   **Heuristic**: No additional `WHERE` clause is applied.

2.  **Jumps**
    -   **Description**: Prioritizes maps where difficulty is driven by discrete, snappy aim between objects (typically circles).
    -   **Heuristic**: The map's peak `aim` must be significantly higher than its peak `speed`, and the `slider_factor` must be high, indicating sliders behave like jumps and do not offer rest.
    -   **`WHERE` clause**: `aim > speed * 1.1 AND slider_factor > 0.95`

3.  **Flow**
    -   **Description**: Prioritizes maps where aim difficulty comes from reading and executing continuous, complex slider patterns.
    -   **Heuristic**: The map must have a high "average slider complexity," found by normalizing the total slider difficulty by the number of sliders. It must also contain a significant proportion of sliders.
    -   **`WHERE` clause**: `(aim_difficult_slider_count / NULLIF(n_sliders, 0)) > 0.5 AND n_sliders > (n_objects * 0.2)`

4.  **Speed**
    -   **Description**: Prioritizes maps focused on short, intense tapping bursts.
    -   **Heuristic**: The map's peak `speed` must be significantly higher than its peak `aim`, and the proportion of "speed notes" must be relatively low, indicating the speed is not sustained.
    -   **`WHERE` clause**: `speed > aim * 1.1 AND (speed_note_count / n_objects) < 0.4`

5.  **Stamina**
    -   **Description**: Prioritizes maps with long, sustained tapping sections like streams, which test consistency.
    -   **Heuristic**: The map must have a high proportion of "speed notes," indicating that tapping is a persistent challenge throughout the map.
    -   **`WHERE` clause**: `(speed_note_count / n_objects) > 0.4`