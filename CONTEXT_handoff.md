# IMP — Context Handoff
*Version 7g · March 2026*

This file exists for one reason: if you're an AI agent starting cold with no chat
history, this gets you up to speed in 2 minutes. Keep it current. If you shipped
something, update this before ending the session.

---

## What IMP is

Physics sandbox → MIDI generator. Draw geometry, place balls, collisions fire MIDI
notes into FL Studio via loopMIDI. Also used for OBS-recorded polyrhythm videos.
Built by Katie (kenwud) in Python 3.10 on Windows with DearPyGui + pymunk + rtmidi.

---

## Current version: 7g

The last two sessions were architecture passes, not feature work:

**v7f — Note system normalization**
Every runtime object now carries `notes: list[int]` + `note_index: int`. No strings
at runtime. `parse_notes()` / `normalize_notes()` live in `scales.py` as the single
source. `next_note(obj)` in `tools/base.py` is the single melody sequencer — used by
`midi_engine._select_note()`. Emitter and attractor dicts normalized. All `world.add_*()`
functions accept `notes=list`. Scene save/load migrated.

**v7g — Defaults system consistency**
`sync_defaults_from_widgets()` in `main.py` is now comprehensive: reads ALL UI widgets
(global fields + tool placement props) and writes to `global_defaults` + all `t.defaults`
before every placement. Channel callback fixed (was only writing to `global_defaults`).
Trigger MIDI checkbox tagged so sync can read it. Tools read only from `self.defaults`,
never call `dpg.get_value()` directly. Array root note and scale now apply correctly.

---

## What's next (in order)

1. **transpose() in scales.py** — trivial now that notes are normalized:
   `def transpose(notes, semitones): return normalize_notes([n + semitones for n in notes])`
   Then: keyboard shortcuts Shift+Up/Down = transpose selected ±1 semitone.

2. **MusicalEvent expansion** — design conversation needed before coding.
   Enables quantization, groove, routing. See ROADMAP.md Tier 2.

3. **Visual mode** — F11, panels hide, aspect ratio presets. See ROADMAP.md Tier 4.

---

## Key architectural rules (don't violate these)

- `world.py` never imports `midi_engine` — physics and MIDI are fully decoupled
- Tools never import each other
- `get_properties()` must check `shape_type` attribute, never `isinstance` alone
  (Segment is used by Wall, HollowBox, HollowCircle, RotatingWall, OscillatingWall)
- Use `get_note()` / `get_notes()` in tools, never `self.defaults["note"]`
- Use `mvKey_LShift` / `mvKey_RShift`, not `mvKey_Shift` (doesn't exist in this DPG)
- DPG init order: context → fonts → themes → bind_theme → windows → bind_item_theme
  → viewport → setup → show → set_primary_window → loop
- `sync_defaults_from_widgets()` must be called before every `on_mouse_click`
- Tools read ONLY from `self.defaults` — no `dpg.get_value()` inside tools

---

## Files that matter most

```
main.py         — UI, input, sync_defaults_from_widgets(), build_*_panel()
world.py        — all physics object creation (normalize_notes at entry)
scales.py       — parse_notes, normalize_notes, next note name, scale data
tools/base.py   — BaseTool ABC, next_note(), BALL_SPAWN_PROPS
midi_engine.py  — CollisionEvent → MusicalEvent → MIDI, uses next_note()
ARCHITECTURE.md — full conventions, read before editing anything
ROADMAP.md      — what's done, what's next, priorities
```

---

## DPG quirk to know

`input_int` widget `+`/`-` buttons don't reliably fire callbacks before a mouse click
lands on the canvas. This is why `sync_defaults_from_widgets()` reads widget state
directly via `dpg.get_value()` rather than relying on callbacks. Do not remove this
sync call or route around it.
