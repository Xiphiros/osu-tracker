// Enum for osu! mod bitmasks
export const MODS = {
    None: 0,
    NoFail: 1,
    Easy: 2,
    TouchDevice: 4,
    Hidden: 8,
    HardRock: 16,
    SuddenDeath: 32,
    DoubleTime: 64,
    Relax: 128,
    HalfTime: 256,
    Nightcore: 512, // Always used with DoubleTime
    Flashlight: 1024,
    Autoplay: 2048,
    SpunOut: 4096,
    Relax2: 8192,      // Autopilot
    Perfect: 16384,
    Key4: 32768,
    Key5: 65536,
    Key6: 131072,
    Key7: 262144,
    Key8: 524288,
    FadeIn: 1048576,
    Random: 2097152,
    Cinema: 4194304,
    TargetPractice: 8388608,
    Key9: 16777216,
    Coop: 33554432,
    Key1: 67108864,
    Key3: 134217728,
    Key2: 268435456,
    ScoreV2: 536870912,
    Mirror: 1073741824,
};

// Converts a mod integer into an array of string acronyms
export function getModsFromInt(modInt) {
    if (modInt === 0) return [];
    
    const activeMods = [];

    // Handle mutually exclusive speed mods first
    if (modInt & MODS.Nightcore) activeMods.push('NC');
    else if (modInt & MODS.DoubleTime) activeMods.push('DT');

    // Handle mutually exclusive perfect/sudden death mods
    if (modInt & MODS.Perfect) activeMods.push('PF');
    else if (modInt & MODS.SuddenDeath) activeMods.push('SD');

    // Add other mods
    if (modInt & MODS.Hidden) activeMods.push('HD');
    if (modInt & MODS.HardRock) activeMods.push('HR');
    if (modInt & MODS.Flashlight) activeMods.push('FL');
    if (modInt & MODS.Easy) activeMods.push('EZ');
    if (modInt & MODS.NoFail) activeMods.push('NF');
    if (modInt & MODS.HalfTime) activeMods.push('HT');
    if (modInt & MODS.Relax) activeMods.push('RX');
    if (modInt & MODS.Relax2) activeMods.push('AP'); // Autopilot
    if (modInt & MODS.SpunOut) activeMods.push('SO');
    if (modInt & MODS.TouchDevice) activeMods.push('TD');
    if (modInt & MODS.Autoplay) activeMods.push('AU');
    
    // Key mods for Mania
    if (modInt & MODS.Key1) activeMods.push('1K');
    if (modInt & MODS.Key2) activeMods.push('2K');
    if (modInt & MODS.Key3) activeMods.push('3K');
    if (modInt & MODS.Key4) activeMods.push('4K');
    if (modInt & MODS.Key5) activeMods.push('5K');
    if (modInt & MODS.Key6) activeMods.push('6K');
    if (modInt & MODS.Key7) activeMods.push('7K');
    if (modInt & MODS.Key8) activeMods.push('8K');
    if (modInt & MODS.Key9) activeMods.push('9K');
    
    // Other gameplay-altering mods
    if (modInt & MODS.FadeIn) activeMods.push('FI');
    if (modInt & MODS.Random) activeMods.push('RD');
    if (modInt & MODS.Cinema) activeMods.push('CN');
    if (modInt & MODS.TargetPractice) activeMods.push('TP');
    if (modInt & MODS.Coop) activeMods.push('CO');
    if (modInt & MODS.Mirror) activeMods.push('MR');
    if (modInt & MODS.ScoreV2) activeMods.push('V2');

    return activeMods;
}