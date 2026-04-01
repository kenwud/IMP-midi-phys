# IMP — Architecture & Code Conventions
*Version 7g · Last updated March 2026*

This document is the source of truth for how IMP is structured and why. Read this before touching any file.

---

## ⚠️ Documentation Rule

**Update ARCHITECTURE.md, ROADMAP.md, README.md, and CONTEXT_handoff.md whenever you complete work.**
These four files are the project's entire memory. If the chat session ends unexpectedly,
a new AI agent must be able to read them and know exactly what state the code is in.
No archaeology. No guessing. Update docs before ending the session.

---

## Philosophy

**1. Tools are drop-in mods.**
Adding a new object type requires one file in `/tools/` and nothing else. No changes to `main.py` or `world.py`.

**2. The UI is data-driven.**
Props panel and defaults panel render from descriptor dicts returned by tools. No hardcoded widget trees for specific tools in `main.py`.

**3. Physics and MIDI are decoupled.**
`world.py` never imports `midi_engine.py`. Collision events travel through `event_bus.py`.

**4. Defaults are the single source of truth at placement time.**
`sync_defaults_from_widgets()` runs before every `on_mouse_click`. It reads ALL UI
widget state and writes to `global_defaults` + all `tool.defaults`. Tools read ONLY
from `self.defaults` — never call `dpg.get_value()` inside a tool.

---

## Module Responsibilities

```
main.py          — DPG context, theme setup, window creation, main loop,
                   input handling, UI callbacks. No physics logic.

world.py         — Pymunk Space wrapper. All shape creation, body management,
                   attractor force, emitter spawning, physics step.
                   No DPG imports. No MIDI imports.

scene.py         — SceneManager: serialize/deserialize .imp files (JSON).

event_bus.py     — Publish/subscribe. Physics posts CollisionEvents.
                   MidiEngine subscribes.

midi_engine.py   — Translates CollisionEvents into MIDI note/velocity.
midi_output.py   — rtmidi wrapper.
transport.py     — Play/stop state, BPM.
scales.py        — Pure functions: scale intervals, note name ↔ MIDI.
icons.py         — Font Awesome loading.
logger.py        — Logging setup.

tools/base.py    — BaseTool ABC. parse_notes(), get_note(), get_notes(),
                   angle_snap(). Tool interface contract.
tools/*.py       — One tool per file. Only imports: DPG, BaseTool, stdlib, scales.
                   Must NOT import main.py, world.py, or each other.
```

---

## DPG Initialization Order (Mandatory)

Violating this order causes `Item not found` errors at startup.

```
1.  dpg.create_context()
2.  Load fonts (setup_fonts)
3.  Create ALL themes
4.  dpg.bind_theme()        ← global theme BEFORE any window
5.  Create ALL windows
6.  Bind per-item themes    ← AFTER all windows exist
7.  dpg.create_viewport()
8.  dpg.setup_dearpygui()
9.  dpg.show_viewport()
10. dpg.set_primary_window()
11. Main loop
```

**Never call `dpg.bind_item_theme(tag, ...)` before the window with that tag has been created.**

---

## Theme System

| Theme tag             | Applied to         | Purpose                                      |
|-----------------------|--------------------|----------------------------------------------|
| `GlobalCompactTheme`  | `dpg.bind_theme()` | Overrides DPG's default 8px padding globally |
| `TopBarTheme`         | TopBar window      | Ultra-tight vertical spacing                 |
| `PanelTheme`          | All sidebar panels | Comfortable but compact padding              |
| `PrimaryWindowTheme`  | PrimaryWindow      | Zero padding, canvas fills edge-to-edge      |

Do not add per-widget style overrides scattered through the code.

---

## Layout System

Constants defined at top of `main.py`:
```python
TOPBAR_H     = 24    # approximate — actual height measured dynamically
TOOL_RAIL_W  = 52
TOOL_DEF_W   = 210
GLOBAL_W     = 210
RIGHT_PROP_W = 260
```

`UIManager.layout_chrome()` runs every frame. It measures the actual rendered TopBar height via `dpg.get_item_rect_size("TopBar")` and positions all sidebars below it dynamically. This handles font size changes correctly.

**All panels use `no_title_bar=True`.** Headers are `dpg.add_text()` inside content — not DPG title bars. Title bars cause overlap bugs.

---

## Physics Settings (world.py)

```python
space.collision_slop = 0.0        # no penetration allowance
space.collision_bias = 0.01       # aggressive overlap correction
space.iterations     = 20         # double default solver iterations
space.idle_speed_threshold = 0.0  # never sleep bodies
```

These settings are tuned for accurate elastic bouncing. Do not increase `collision_slop` — it causes energy loss proportional to impact velocity, which creates asymmetric bounce heights in arrays.

**World scale matters.** Pymunk uses a fixed timestep. Large world-space distances (zoomed-out scenes) cause more integration error per step. Keep scenes at a natural scale — box ~500-800 units tall, balls radius 10-20, gravity ~-900. Substeps can compensate somewhat but scale is the real fix.

---

## Tool System

### How tools are discovered

`load_tools()` scans `tools/`, imports each file, finds the first `BaseTool` subclass, instantiates with merged `global_defaults` + `placement_props` defaults.

**To add a tool:** subclass `BaseTool`, drop in `tools/`, restart. Nothing else.

### BaseTool contract

```python
class MyTool(BaseTool):
    name = "My Tool"
    icon = "icon-name"           # Font Awesome icon name

    placement_props = [          # tool-specific defaults ONLY
        {"key": "my_val", "label": "My Val", "type": "float",
         "default": 1.0, "min": 0.0, "step": 0.1}
    ]
    # type options: "float" | "int" | "bool" | "text" | "combo"
    # combo requires "options": ["A", "B", "C"]

    def on_mouse_click(self, world, pos, cam=None): ...
    def on_mouse_drag(self, world, pos, cam=None): ...
    def on_mouse_release(self, world, pos, cam=None): ...
    def draw_preview(self, canvas, canvas_h, cam): ...  # optional

    @staticmethod
    def get_properties(obj):
        # MUST return [] if obj is not your shape type
        # Check shape_type attr before returning anything
        if getattr(obj, "shape_type", "") != "MyType": return []
        return [{"key": ..., "label": ..., "type": ..., "value": ...}]
```

### Critical rules for get_properties

**Always check `shape_type` specifically.** `pymunk.Segment` is used by Wall, HollowBox, HollowCircle, RotatingWall, and OscillatingWall. If you only check `isinstance(obj, pymunk.Segment)` your tool will steal properties from other segment types. Check `shape_type` first.

**Do not declare** `note`, `notes`, `melody`, `channel`, `elasticity`, `friction`, or `trigger_midi` in `placement_props` — these are global defaults, always present automatically.

**Do not declare** `note` or `notes` in `get_properties()` — the unified notes field is rendered by `build_properties_panel()` for all objects automatically.

### Notes access in tools

```python
self.get_note()    # → int, first MIDI note (0-127)
self.get_notes()   # → list of ints, full melody
```

Never access `self.defaults["note"]` directly.

### Angle snap

```python
end = self.angle_snap(start, end)  # snaps to 7.5° if Shift held
```

Available on all tools via `BaseTool`. Uses `mvKey_LShift` / `mvKey_RShift` — not `mvKey_Shift` (doesn't exist in this DPG version).

---

## Body Types (pymunk)

```
body_type == 0  DYNAMIC    — balls, affected by forces
body_type == 1  KINEMATIC  — rotating/oscillating walls, move by velocity
body_type == 2  STATIC     — walls, boxes, circles, never move via physics
```

The move tool handles all three types explicitly. Do not use `body_type == 0` as a catch-all — kinematic bodies must be moved via `body.position`, static bodies via `unsafe_set_endpoints`.

---

## Notes / Melody System

**Single canonical form at runtime: `notes: list[int]` + `note_index: int` on every object.**
Strings only exist in UI text fields and .imp JSON files. They are normalized immediately
on entry via `normalize_notes()` in `scales.py`.

| Location          | Field        | Type       | Notes                                      |
|-------------------|--------------|------------|--------------------------------------------|
| `global_defaults` | `"notes"`    | str        | comma-separated, UI only                   |
| `tool.defaults`   | `"notes"`    | str        | same format, UI only                       |
| pymunk shape      | `.notes`     | list[int]  | set at creation via normalize_notes()      |
| pymunk shape      | `.note_index`| int        | melody sequencer position                  |
| emitter dict      | `"notes"`    | list[int]  | set at creation, no melody string          |
| emitter dict      | `"note_index"`| int       | melody sequencer position                  |
| attractor dict    | `"notes"`    | list[int]  | set at creation                            |
| attractor dict    | `"note_index"`| int       | melody sequencer position                  |

**Key functions:**
- `scales.parse_notes(value)` — str/int/list → list[int], canonical parser
- `scales.normalize_notes(value)` — same, always returns non-empty list (use at creation time)
- `tools/base.next_note(obj)` — reads notes[note_index], advances index, returns int
  Works on both pymunk shapes and dicts. Used by midi_engine._select_note().

`"note"` and `"melody"` must NOT appear in runtime objects. They may appear in .imp files
for legacy compatibility — normalize_notes() handles them on load.

---

## Known Technical Debt

**Medium priority:**
1. Attractor `draw_preview()` uses `dpg.get_mouse_pos()` directly — bypasses camera transform. Should receive world_pos from main loop.
2. Velocity scaling calibration — impulse_scale (600.0) may need per-scene tuning. Consider exposing as an advanced setting.

**Low priority:**
3. `slot_None.imp` in quicksave — legacy file from old bug, safe to delete manually.
4. Green note-name hint in defaults panel lags on `+`/`-` button presses (DPG limitation).
   Placed notes are always correct. Hint updates on Enter/focus-loss only.

**Resolved (do not re-introduce):**
- parse_notes() duplication — consolidated into scales.py ✅
- Emitter melody string — retired, uses notes list at runtime ✅
- Attractor bare "note" int — replaced with notes list + note_index ✅
- Defaults inconsistency — sync_defaults_from_widgets() covers all fields ✅
- Channel default not applying — callback fixed to update all tool.defaults ✅

---

## Target State

When base code is fully clean:
- `parse_notes()` only in `scales.py`
- Emitter stores `notes` list in world.py, no `melody` field
- Attractor preview uses camera-transformed coords
- Kinematic walls have pivot visualisation
- `ARCHITECTURE.md`, `README.md`, `wishlist.txt` updated each session

---

## AI Agent Rules

- Read this document before touching any file.
- Do not add features not in `README.md` or explicitly requested.
- Do not rename or restructure modules without explicit instruction.
- Do not install new dependencies without confirmation.
- Make small atomic changes. Syntax-check between edits.
- Follow DPG initialization order above — theme binds after window creation.
- Use `self.get_note()` / `self.get_notes()` in tools, never `self.defaults["note"]`.
- Check `shape_type` in `get_properties()` before returning — never match on `isinstance` alone for Segment types.
- Use `mvKey_LShift` / `mvKey_RShift`, not `mvKey_Shift`.
- When in doubt, ask.
