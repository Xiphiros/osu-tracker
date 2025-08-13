# 4. Training Model & Recommender

## 4.1. Purpose & Philosophy

The Training Recommender is designed to provide a structured, consistent, and incremental path for skill improvement in osu!standard. It is based on a session-based training methodology focused on gradually pushing a player's skill ceiling.

The core philosophy is to find the "edge" of a player's current ability (represented by a Star Rating) and consistently practice within that narrow band, moving it slightly up or down based on performance. This avoids the common pitfalls of jumping between wildly different difficulties, promoting more focused and efficient improvement.

## 4.2. Core Logic

### 4.2.1. Inputs

The model requires two primary user inputs to begin a session:
1.  **Target Star Rating (SR):** The difficulty level the player wants to start at. This can be entered manually or, in the future, suggested automatically.
2.  **Max BPM:** The maximum "main" BPM the player is comfortable playing at for the session.
3.  **Mods:** The user can select a combination of mods (EZ, HD, HR, DT, HT, FL) to train.

### 4.2.2. Search Criteria

When a recommendation is requested, the system searches the local beatmap database for a **single, random map** that meets the criteria after calculating mod-adjusted difficulty with `rosu-pp-py`:
-   **Game Mode:** Must be osu!standard (`game_mode = 0`).
-   **Star Rating:** Must be within a narrow range: `modded_stars >= Target SR` and `modded_stars < Target SR + 0.1`.
-   **BPM:** The map's mod-adjusted main BPM must be less than or equal to the specified Max BPM (`modded_bpm <= Max BPM`).

## 4.3. Session Flow

### 4.3.1. Current Manual Flow (v2)

The current implementation requires manual user feedback to guide the session.
1.  **Initialization:** The user selects their desired mods and enters their starting SR and Max BPM.
2.  **Request:** The user clicks "Find a map". The system finds and displays a suitable beatmap.
3.  **Play:** The user switches to the osu! client, finds the recommended map, and plays it with the intention of meeting a personal goal.
4.  **Feedback:** The user returns to the tracker and provides feedback:
    *   **"Passed Goal":** If their performance met their goal. This increases the Target SR by 0.1.
    *   **"Failed Goal":** If their performance did not meet their goal. This decreases the Target SR by 0.1.
    *   **"Skip":** If the map was undesirable for any reason (e.g., too difficult, disliked song). This also decreases the Target SR by 0.1.
5.  **Iteration:** The user can click "Reroll" up to 3 times to get a new map with the same settings, or click "Find a map" to start a new search with the adjusted SR.

## 4.4. Future Automation & Roadmap

The end goal is a fully automated system that minimizes user input after the initial setup. This requires several key features to be developed.

### 4.4.1. Automatic Starting SR Suggestion

To eliminate guesswork, the system will provide a suggested starting SR.
1.  A button will be added next to the SR input, e.g., "Suggest SR".
2.  When clicked, the system will fetch all of the user's plays with the currently selected mods.
3.  It will filter these plays based on the user's defined "pass" criteria (see next section). For example, it will only consider plays with >= 96% accuracy.
4.  It will take the top 100 of these passing plays, sorted by Star Rating (descending).
5.  It will calculate the average SR of these top 100 plays.
6.  This average will be rounded to the nearest tenth (e.g., 5.56 becomes 5.6) and populated in the Target SR input field.

### 4.4.2. User-Definable Goals

A new UI section will allow players to define what constitutes a "Passed Goal". This will be configurable and saved per-user.
-   **Goal Types:** The user will be able to set one or more conditions:
    -   Accuracy (`>= 96%`)
    -   ScoreV2 (`>= 500,000`)
    -   Max Combo (`>= 500x`)
    -   Miss Count (`<= 5`)
-   **Mod Scaling:** ScoreV2 goals will be automatically scaled by the appropriate multiplier for mods like HR, HD, and FL.

### 4.4.3. Automatic Session Management

This is the ultimate goal, creating a seamless training loop:
1.  **Play Detection:** After a map is recommended, the application will monitor for new replays in the background. It will specifically look for a new play by the current user on the recommended map's hash.
2.  **Automatic Evaluation:** When a new replay appears, the system will parse it. It will check that the mods match the training session and that the **NoFail (NF) mod was not used**. It will then automatically compare the play's stats (accuracy, score, etc.) against the user's defined goals.
3.  **Automatic SR Adjustment:** Based on the evaluation, the system will automatically adjust the user's session SR up or down.
4.  **Notifications:** The UI will provide a clear notification that the goal was passed/failed and the SR has been adjusted, prompting the user to find the next map.
5.  **Persistent State:** The user's current training SR and defined goals will be saved locally, so they are automatically loaded the next time they open the Recommender tab.