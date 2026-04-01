# IMP — Interactive MIDI Physics
### Version 7g · Technical Specification & Collaboration Guide
*Last updated: March 2026*

---

## ⚠️ Critical Rule for AI Agents — Read First

**Always update ARCHITECTURE.md, ROADMAP.md, and this README when completing work.**
These three files are the project's memory. If context is lost mid-session (chat limit,
switching AI tools, crash), an incoming agent reading only these three files must be able
to reconstruct exactly what state the code is in and what to do next — no archaeology
required. If you shipped something, document it here before moving on.

### Rules for AI Coding Agents

- Read `ARCHITECTURE.md` before touching any file.
- Read `ROADMAP.md` to understand current priorities and what's already done.
- Do not add features not described in ROADMAP.md or directly requested.
- Do not rename or restructure modules without explicit instruction.
- Do not install new dependencies without confirmation.
- One atomic change at a time. Syntax-check between edits. Report before moving on.
- When in doubt, ask.

---

## Overview

**IMP** is a physics-based generative music environment. Users draw geometry, place
balls with musical properties, and generate real-time MIDI from collision events.

**Primary use cases:**
- Live MIDI generation alongside FL Studio via loopMIDI
- Visual content creation — OBS recording for TikTok/Reels polyrhythm videos

**Core philosophy:** tools are drop-in mods. Adding a new object type = one file in
`/tools/`, nothing else.

**Environment:** Windows 11 / Python 3.10 / dearpygui / pymunk 7.2 / python-rtmidi /
loopMIDI (external)

---

## What's Working (v7g)

### Architecture
- Clean note system: `parse_notes()` + `normalize_notes()` in `scales.py` — single source
- All runtime objects carry `notes: list[int]` + `note_index: int` — no strings at runtime
- `next_note(obj)` in `tools/base.py` — single melody sequencer, works on shapes and dicts
- `sync_defaults_from_widgets()` in `main.py` — called before every placement, guarantees
  all tool defaults are current regardless of DPG callback timing
- Defaults data flow: `UI widgets → sync → global_defaults + tool.defaults → tools`
  Tools only read from `self.defaults`, never call `dpg.get_value()` directly

### Physics
- Hollow geometry containers (circle, box)
- Accurate elastic bouncing (elasticity=1 returns ball to drop height)
- Substepping + time scale controls
- Variable substeps (scales to fastest ball velocity each frame)
- Gravity attractor/repulsor with proximity MIDI
- Kinematic rotating and oscillating walls
- Ball emitters with interval spawning and melody cycling
- Ball-ball MIDI collision toggle

### MIDI
- Collision → MIDI via decoupled event bus (world.py never imports midi_engine)
- Per-object melody (`notes: list[int]` + `note_index` cycling via `next_note()`)
- Note name display (60 → C4) in defaults and properties panels
- Velocity from impact speed with sensitivity blend
- Per-object MIDI channel
- Note-off queue with fixed/velocity sustain modes
- MIDI panic on stop

### Tools
- Select, Move (with pivot-grab for kinematic walls)
- Wall, Ball, Hollow Circle, Hollow Box
- Rotating Wall, Oscillating Wall
- Attractor, Emitter
- Array — scale dropdown (27 scales), root note, octave spread, Ascending/Descending/Ping-Pong
- Custom Array — custom CSV note string, cycle/mirror direction
- Shift+drag: 7.5° angle snap on Wall and Array tools

### UI
- Top bar: MIDI indicator, save/load slots, physics controls
- Tool rail: Font Awesome icon buttons
- Defaults panel: auto-rebuilds on tool switch, all fields sync correctly at placement
- Properties panel: data-driven, correct for all shape types
- Multi-select transpose buttons (+/-1, 3, 5, 7, 12 semitones)
- Pivot visualisation: magenta = RotatingWall, cyan = OscillatingWall
- F: toggle all panels | Space: play/stop | Delete | Arrow nudge (×2 / Shift×20)

### Scene
- Save/load .imp (JSON), 5 quick slots
- Legacy scene files load correctly (melody/note fields normalized on load)
- Auto-purge offscreen balls every ~5 seconds

---

## File Structure

```
version_7g/
├── main.py               # DPG context, themes, windows, input, main loop,
│                         # sync_defaults_from_widgets(), build_*_panel()
├── world.py              # PhysicsWorld — all creation paths use normalize_notes()
├── scene.py              # SceneManager — .imp save/load (notes as list[int])
├── event_bus.py          # CollisionEvent / ProximityEvent pub/sub
├── midi_engine.py        # Physics events → MusicalEvent → MIDI output
│                         # Uses next_note() from tools/base.py
├── midi_output.py        # rtmidi wrapper
├── transport.py          # Play/stop state, BPM
├── scales.py             # parse_notes(), normalize_notes(), midi_to_note_name(),
│                         # get_scale_notes(), SCALES dict, SCALE_NAMES list
├── icons.py              # Font Awesome loading
├── logger.py             # Logging setup
├── ARCHITECTURE.md       # Code conventions — read before editing anything
├── ROADMAP.md            # Task tracker — what's done, what's next
├── README.md             # This file
├── TOOL_MODDING.md       # Guide for writing new tools
├── fonts/
│   └── Font Awesome 7 Free-Solid-900.otf
├── scenes/
│   ├── quicksave/
│   └── *.imp
└── tools/
    ├── base.py           # BaseTool ABC, next_note(), parse_notes (re-export),
    │                     # BALL_SPAWN_PROPS, angle_snap()
    ├── select.py
    ├── move.py           # Handles all body types; pivot-grab for kinematic walls
    ├── wall.py
    ├── ball.py
    ├── box.py
    ├── circle.py
    ├── rotating_wall.py
    ├── oscillating_wall.py
    ├── attractor.py
    ├── emitter.py
    ├── array.py          # Uses self.defaults only (sync guarantees freshness)
    └── custom_array.py
```

---

## Physics Guidelines

Keep scenes at natural scale — Pymunk uses fixed timestep, large distances = integration error:
- Box height: 500–800 world units
- Ball radius: 10–20 units
- Gravity: ~-900

`elasticity=1, damping=1` = accurate lossless bouncing. Zoom is camera-only, does not
affect physics.

---

## Known Limitations / Debt

- `Attractor.draw_preview()` uses raw screen coords — bypasses camera transform
- Green note-name hint in defaults panel updates on focus-loss/Enter, not on `+`/`-`
  button press (DPG limitation — `input_int` buttons don't reliably fire callbacks)
  Placed notes are always correct because `sync_defaults_from_widgets()` reads widget
  state directly at placement time
- `slot_None.imp` in quicksave — legacy file, safe to delete manually
