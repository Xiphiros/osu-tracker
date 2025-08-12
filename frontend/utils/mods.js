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
    SpunOut: 4096,
    Perfect: 16384,
};

// Converts a mod integer into an array of string acronyms
export function getModsFromInt(modInt) {
    if (modInt === 0) return [];
    
    const activeMods = [];

    // Handle special cases first
    if (modInt & MODS.Nightcore) activeMods.push('NC');
    else if (modInt & MODS.DoubleTime) activeMods.push('DT');

    if (modInt & MODS.Perfect) activeMods.push('PF');
    else if (modInt & MODS.SuddenDeath) activeMods.push('SD');

    if (modInt & MODS.Hidden) activeMods.push('HD');
    if (modInt & MODS.HardRock) activeMods.push('HR');
    if (modInt & MODS.Flashlight) activeMods.push('FL');
    if (modInt & MODS.Easy) activeMods.push('EZ');
    if (modInt & MODS.NoFail) activeMods.push('NF');
    if (modInt & MODS.HalfTime) activeMods.push('HT');
    if (modInt & MODS.Relax) activeMods.push('RX');
    if (modInt & MODS.SpunOut) activeMods.push('SO');
    if (modInt & MODS.TouchDevice) activeMods.push('TD');

    return activeMods;
}