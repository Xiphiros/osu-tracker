# 4. Training Model & Recommender

## 4.1. Purpose & Philosophy

The Training Recommender is designed to provide a structured, consistent, and incremental path for skill improvement in osu!standard. It is based on a session-based training methodology focused on gradually pushing a player's skill ceiling.

The core philosophy is to find the "edge" of a player's current ability (represented by a Star Rating) and consistently practice within that narrow band, moving it slightly up or down based on performance. This avoids the common pitfalls of jumping between wildly different difficulties, promoting more focused and efficient improvement.

## 4.2. Core Logic

### 4.2.1. Inputs

The model requires two primary user inputs to begin a session:
1.  **Target Star Rating (SR):** The difficulty level the player wants to start at. This is typically the SR they ended their last session on.
2.  **Max BPM:** The maximum "main" BPM the player is comfortable playing at for the session.

### 4.2.2. Search Criteria

When a recommendation is requested, the system searches the local beatmap database for a **single, random map** that meets all the following criteria:
-   **Game Mode:** Must be osu!standard (`game_mode = 0`).
-   **Star Rating:** Must be within a narrow range: `stars >= Target SR` and `stars < Target SR + 0.1`.
-   **BPM:** The map's main BPM must be less than or equal to the specified Max BPM (`bpm <= Max BPM`).

## 4.3. Session Flow

### 4.3.1. Current Manual Flow (v1)

The initial implementation requires manual user feedback to guide the session.
1.  **Initialization:** The user enters their starting SR and Max BPM.
2.  **Request:** The user clicks "Find a map". The system finds and displays a suitable beatmap.
3.  **Play:** The user switches to the osu! client, finds the recommended map, and plays it with the intention of meeting a personal goal.
4.  **Feedback:** The user returns to the tracker and provides feedback:
    *   **"Passed Goal":** If their performance met their goal. This increases the Target SR by 0.1.
    *   **"Failed Goal":** If their performance did not meet their goal. This decreases the Target SR by 0.1.
5.  **Iteration:** The user clicks "Find a map" again with the newly adjusted SR, and the cycle repeats.

## 4.4. Future Automation & Roadmap

The end goal is a fully automated system that minimizes user input after the initial setup. This requires several key features to be developed.

### 4.4.1. Goal Definition

A UI will be added to allow players to define what constitutes a "Passed Goal". This will be configurable and could include conditions like:
-   **Accuracy:** `Accuracy >= 96%`
-   **ScoreV2:** `Score >= 500,000`
-   **Combo:** `Max Combo >= 500x`
-   **Miss Count:** `Misses <= 5`

### 4.4.2. Mod Support & Goal Scaling

The system will be expanded to allow users to request recommendations for specific mod combinations (e.g., HD, HR, HDHR). When mods are active, the ScoreV2 goal will be automatically scaled by the appropriate multiplier.
-   **Example:** If the base goal is 500,000 and the user is training Hidden (HD), the required score on the recommended map would become `500,000 * 1.06 = 530,000`.

### 4.4.3. Automatic Session Management

This is the ultimate goal, creating a seamless training loop:
1.  **Play Detection:** After a map is recommended, the application will monitor the user's new replays (by periodically checking the replays folder or triggering a refresh).
2.  **Automatic Evaluation:** When a new replay appears for the recommended beatmap, the system will parse it and automatically compare the stats (accuracy, score, etc.) against the user's defined goals.
3.  **Automatic SR Adjustment:** Based on the evaluation, the system will automatically adjust the user's session SR up or down.
4.  **Persistent State:** The user's current training SR will be saved locally, so it's automatically loaded the next time they open the Recommender tab, allowing them to pick up exactly where they left off.