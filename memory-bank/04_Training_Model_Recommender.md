# 4. Training Model & Recommender

## 4.1. Purpose & Philosophy

The Training Recommender is designed to provide a structured, consistent, and incremental path for skill improvement in osu!standard. It is based on a session-based training methodology focused on gradually pushing a player's skill ceiling.

The core philosophy is to find the "edge" of a player's current ability (represented by a Star Rating) and consistently practice within that narrow band, moving it slightly up or down based on performance. This avoids the common pitfalls of jumping between wildly different difficulties, promoting more focused and efficient improvement.

## 4.2. Core Logic & Session Flow

The recommender has evolved from a simple map finder into a comprehensive session planner. The new system guides the user through a structured training routine with automated feedback.

### 4.2.1. Session Planning

Before training, the user builds a session plan consisting of one or more sequential "steps". Each step defines:
-   **Mods:** The mod combination to be used for this part of the session (e.g., HD, HR, DT).
-   **Repetitions:** The number of maps that must be passed to complete the step.
-   **Pass Criteria (Goals):** A set of conditions a play must meet to be considered a "pass." This can include:
    -   Minimum Accuracy (e.g., ≥ 96%).
    -   Maximum Miss Count (e.g., ≤ 5 misses).
    -   Minimum Score (for ScoreV2 plays).

### 4.2.2. Active Session

Once the plan is created, the user starts the session. The application then guides them through each step.
1.  **Map Request:** For the current step, the user requests a map. They can specify:
    -   **Skill Focus:** A skill to target (e.g., Jumps, Flow, Speed).
    -   **Target SR:** The difficulty level to aim for. The app can suggest a value based on recent plays.
    -   **Max BPM:** The maximum comfortable BPM.
2.  **Recommendation:** The system searches the database for a map matching the step's mods and the user's criteria, excluding maps played recently in the session.
3.  **Play & Automatic Detection:** The user plays the recommended map in osu!. The application's file watcher detects when the new replay file is created.
4.  **Goal Evaluation:** The system automatically validates the new score:
    -   It confirms the replay is for the correct beatmap and mod combination.
    -   It evaluates the play against the current step's pass criteria (accuracy, misses, etc.).
5.  **Progress Update & SR Adjustment:**
    -   **Pass:** If the goals are met, the map is considered "passed." The session's Target SR is slightly increased.
    -   **Fail/Skip:** If goals are not met, or if the user manually skips the map, the Target SR is slightly decreased.
    -   The application then prompts the user to find the next map. If the required number of passes for the step is met, it automatically moves to the next step in the plan.
6.  **Session End:** The session concludes when all steps in the plan are completed.

This automated loop provides a clear, structured path for improvement by dynamically adjusting difficulty based on real performance.

## 4.3. Search Criteria

When a recommendation is requested, the system searches the local beatmap database for a **single, random map** that meets the following criteria after calculating mod-adjusted difficulty with `rosu-pp-py`:
-   **Game Mode:** Must be osu!standard (`game_mode = 0`).
-   **Star Rating:** Must be within a narrow range: `modded_stars >= Target SR` and `modded_stars < Target SR + 0.15`.
-   **BPM:** The map's mod-adjusted main BPM must be less than or equal to the specified Max BPM (`modded_bpm <= Max BPM`).
-   **Skill Focus Filter:** An advanced heuristic is applied based on the user's selected focus. See Section 4.4.
-   **Exclusion:** The map must not be in a temporary list of recently recommended maps for the current session to avoid repeats.

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