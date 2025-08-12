# 2. Data Formats

This document outlines the structure of proprietary data formats used in the application.

## 2.1. osu! Replay File (`.osr`)

The `.osr` file format contains information about a specific play. The data is stored as a sequence of binary types. (Source: `osr_reference.pdf`)

| Data Type | Description                 |
| :-------- | :-------------------------- |
| Byte      | Game Mode                   |
| Int       | Game Version                |
| String    | Beatmap MD5 Hash            |
| String    | Player Name                 |
| String    | Replay MD5 Hash             |
| Short     | Number of 300s              |
| Short     | Number of 100s              |
| Short     | Number of 50s               |
| Short     | Number of Gekis             |
| Short     | Number of Katus             |
| Short     | Number of Misses            |
| Int       | Total Score                 |
| Short     | Max Combo                   |
| Byte      | Perfect Combo (1 = true)    |
| Int       | Mods Used (Bitmask)         |
| String    | Life Bar Graph              |
| Long      | Timestamp (Windows Ticks)   |
| Int       | Replay Data Length          |
| Byte[]    | Compressed Replay Data      |
| Long      | Online Score ID             |