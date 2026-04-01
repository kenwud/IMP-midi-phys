NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# ---------------------------------------------------------------------------
# Note parsing — single canonical location for all note string → list[int]
# ---------------------------------------------------------------------------

def parse_notes(value, fallback=60) -> list:
    """
    Parse a notes value into a list of MIDI ints.
    Accepts: comma-separated str | list | int | None.
    Always returns a non-empty list clamped 0–127.
    Strings are the ONLY form that should need parsing — at runtime
    all objects carry list[int] directly.
    """
    if value is None:
        return [fallback]
    if isinstance(value, int):
        return [max(0, min(127, value))]
    if isinstance(value, list):
        out = [max(0, min(127, int(v))) for v in value if isinstance(v, int)]
        return out if out else [fallback]
    # String path
    parts = [p.strip() for p in str(value).split(",") if p.strip()]
    out = []
    for p in parts:
        try:
            out.append(max(0, min(127, int(p))))
        except (ValueError, TypeError):
            pass
    return out if out else [fallback]


def normalize_notes(value, fallback=60) -> list:
    """
    Normalize any note representation to list[int], guaranteed non-empty.
    Accepts: str | list[int] | int | None.
    This is the gatekeeper: call this at object creation time so runtime
    objects ALWAYS carry list[int], never strings.
    """
    return parse_notes(value, fallback)

SCALES = {
    # Basics
    "Chromatic":        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    "Major":            [0, 2, 4, 5, 7, 9, 11],
    "Minor":            [0, 2, 3, 5, 7, 8, 10],
    # Pentatonic / Blues
    "Maj Pentatonic":   [0, 2, 4, 7, 9],
    "Min Pentatonic":   [0, 3, 5, 7, 10],
    "Blues":            [0, 3, 5, 6, 7, 10],
    # Modes
    "Dorian":           [0, 2, 3, 5, 7, 9, 10],
    "Phrygian":         [0, 1, 3, 5, 7, 8, 10],
    "Lydian":           [0, 2, 4, 6, 7, 9, 11],
    "Mixolydian":       [0, 2, 4, 5, 7, 9, 10],
    "Locrian":          [0, 1, 3, 5, 6, 8, 10],
    # Harmonic / Melodic
    "Harmonic Minor":   [0, 2, 3, 5, 7, 8, 11],
    "Melodic Minor":    [0, 2, 3, 5, 7, 9, 11],
    # Symmetric / Other
    "Whole Tone":       [0, 2, 4, 6, 8, 10],
    "Diminished":       [0, 2, 3, 5, 6, 8, 9, 11],
    "Aug Triad":        [0, 4, 8],
    "Dim Triad":        [0, 3, 6, 9],
    "Major Triad":      [0, 4, 7],
    "Minor Triad":      [0, 3, 7],
    "Maj7 Arp":         [0, 4, 7, 11],
    "Dom7 Arp":         [0, 4, 7, 10],
    "Min7 Arp":         [0, 3, 7, 10],
    "HalfDim7 Arp":     [0, 3, 6, 10],
    # World / Exotic
    "Phrygian Dom":     [0, 1, 4, 5, 7, 8, 10],
    "Hungarian Minor":  [0, 2, 3, 6, 7, 8, 11],
    "Japanese":         [0, 1, 5, 7, 8],
    "Arabic":           [0, 2, 4, 5, 6, 8, 10],
}

# Flat list for UI dropdowns — order matters
SCALE_NAMES = [
    "Major", "Minor", "Dorian", "Phrygian", "Lydian", "Mixolydian", "Locrian",
    "Harmonic Minor", "Melodic Minor",
    "Maj Pentatonic", "Min Pentatonic", "Blues",
    "Whole Tone", "Diminished",
    "Major Triad", "Minor Triad", "Aug Triad", "Dim Triad",
    "Maj7 Arp", "Dom7 Arp", "Min7 Arp", "HalfDim7 Arp",
    "Phrygian Dom", "Hungarian Minor", "Japanese", "Arabic",
    "Chromatic",
]

def midi_to_note_name(midi_note):
    if not (0 <= midi_note <= 127): return "N/A"
    octave = (midi_note // 12) - 1
    note_index = midi_note % 12
    return f"{NOTE_NAMES[note_index]}{octave}"

def get_scale_notes(root_note, scale_name, num_notes, octave_spread=1):
    """
    Generate num_notes MIDI notes from a scale.
    octave_spread: how many octaves to span before repeating pattern.
                   1 = normal (notes climb by semitone pattern each octave)
                   2 = skip an octave each cycle (wider voicing)
                   3 = two octaves apart, etc.
    """
    intervals = SCALES.get(scale_name, SCALES["Major"])
    notes = []
    for i in range(num_notes):
        octave_offset = (i // len(intervals)) * octave_spread
        note_in_scale = intervals[i % len(intervals)]
        note = root_note + (octave_offset * 12) + note_in_scale
        if 0 <= note <= 127:
            notes.append(note)
    return notes
