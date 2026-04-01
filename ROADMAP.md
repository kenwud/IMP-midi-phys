# IMP — Roadmap & Task Tracker
*Version 7g · Last updated March 2026*

This is the living task list. Update it every session.
**If you're an AI agent starting fresh: read this + ARCHITECTURE.md before touching code.**

---

## DONE — Shipped and stable

### Core Architecture
- [x] Event bus — physics fully decoupled from MIDI
- [x] Drop-in tool system — auto-discovered, no main.py changes to add a tool
- [x] Data-driven UI — props and defaults panels render from tool descriptors
- [x] Y-up world coordinate system with live canvas offset tracking
- [x] Strict module boundaries: world.py has no MIDI, tools don't import each other
- [x] DPG initialization order documented and enforced (ARCHITECTURE.md)

### Note System (completed v7f/7g — major architecture pass)
- [x] `parse_notes()` + `normalize_notes()` in `scales.py` — single canonical location
- [x] All runtime objects carry `notes: list[int]` + `note_index: int` at all times
- [x] No strings at runtime — strings only exist in UI inputs and .imp save files
- [x] `next_note(obj)` in `tools/base.py` — single melody sequencer for shapes + dicts
- [x] `midi_engine._select_note()` delegates to `next_note()` — no inline logic
- [x] Attractor dict uses `notes`/`note_index` — no more bare `"note"` int
- [x] Emitter dict uses `notes`/`note_index` — `melody` string retired from runtime
- [x] All `world.add_*()` functions accept `notes=list` as primary param
- [x] Scene save/load uses `notes: list[int]` — legacy `note`/`melody` handled on load
- [x] Duplicate `parse_notes` removed from `main.py` and `tools/base.py`

### Defaults System (completed v7g — consistency pass)
- [x] `sync_defaults_from_widgets()` — comprehensive, covers ALL global + tool fields
- [x] Called before every `on_mouse_click` — guarantees fresh data at placement time
- [x] Channel callback fixed — now updates `global_defaults` + all `tool.defaults`
- [x] Trigger MIDI checkbox tagged `##DefTriggerMidi` — readable by sync
- [x] Tools read ONLY from `self.defaults` — no `dpg.get_value()` inside tools
- [x] `_read()` hacks removed — self.defaults is the reliable single source
- [x] Array root note and scale now apply correctly at placement

### Physics
- [x] Hollow geometry containers (circle, box)
- [x] Substepping + time scale controls
- [x] Variable substeps (scales to fastest ball velocity)
- [x] Accurate elastic bouncing (collision_slop=0, collision_bias=0.01, iterations=20)
- [x] Ball-ball MIDI collision toggle

### MIDI
- [x] Collision → MIDI via event bus (CollisionEvent)
- [x] Proximity → MIDI via event bus (ProximityEvent)
- [x] Note-off queue — fixed and velocity-based sustain modes
- [x] Unified velocity calculation via _calc_velocity()
- [x] MIDI panic on stop
- [x] MusicalEvent dataclass in midi_engine.py

### Tools
- [x] Select, Move (with pivot-grab), Wall, Ball, Hollow Circle, Hollow Box
- [x] Rotating Wall, Oscillating Wall (kinematic, correct arrow-key behavior)
      Arrow keys move wall body only; mouse drag moves whole assembly; pivot-grab moves pivot only
- [x] Attractor, Emitter (melody cycling correct)
- [x] Array — 27 scales, root note, octave spread, Ascending/Descending/Ping-Pong
- [x] Custom Array — custom CSV notes, cycle/mirror direction
- [x] Shift+drag angle snap (7.5°) on Wall and Array
- [x] Multi-select transpose (each object shifts from its own notes independently)
- [x] Pivot visualisation (magenta = Rotating, cyan = Oscillating)
- [x] BALL_SPAWN_PROPS shared list in base.py

### UI
- [x] Top bar MIDI indicator, save/load slots
- [x] Tool rail with Font Awesome icons
- [x] Placement defaults panel — correct sync, all fields apply at placement
- [x] Properties panel — data-driven, all shape types
- [x] Transpose buttons in properties panel
- [x] Note name hints in defaults and properties panels

---

## TODO — Ordered by priority

---

### Tier 0 — Bug fixes (do before any new features)

- [ ] **Pivot behavior regression — restore correct arrow key behavior**
      Current broken behavior: arrow keys move body + pivot together.
      Correct intended behavior (three distinct operations):
      - Arrow keys → move selected body only, pivot stays in place
      - Move tool drag → move body + pivot together as assembly
      - Pivot-grab → move pivot only, body stays
      This was working previously and regressed. Restore before adding any new input handling.

---

### Tier 1 — Foundational (do before building features)

- [ ] **Frame lifecycle — design pass** ⚠️ DOCUMENT BEFORE CODING
      Before touching world.py's main loop, formally define and document the frame lifecycle
      in ARCHITECTURE.md. This is a documentation task, not a code task.

      Correct frame lifecycle (verify against current code then lock in):
      ```
      1. Read input (keyboard, mouse)
      2. Apply deferred mutation queue
             ↓ all pending body changes applied here, once, safely
      3. world.step() — one call, N substeps run internally inside pymunk
             ↓ pymunk handles substep collision detection internally
             ↓ IMP never touches physics bodies during this call
      4. Collect all collision events that emerged from step()
             ↓ once per frame, not once per substep
      5. Process collision events → MIDI out
      6. Render / draw frame
      7. Queue any mutations triggered by input this frame
             ↓ applied at step 2 of next frame
      ```

      Key decisions baked in:
      - Mutations apply before physics — sim never modified mid-step
      - Events collected after ALL substeps complete — single bounce = single event
      - MIDI fires after physics fully done — never mid-substep
      - Render is always last — draws result of fully completed frame
      - Substeps are an internal pymunk detail — IMP never reasons about between-substep state

      This is the foundation slab. All future systems (Clock Mode, CC output, deferred queue,
      visuals) slot into a specific numbered step. Define once, reference forever.

- [ ] **Deferred physics mutation queue**
      Known crash: moving/modifying physics bodies mid-substep causes race condition.
      Rare under normal use, frequent under continuous real-time input.
      Fix: queue all user-initiated body mutations (position, endpoints, removal).
      Apply entire queue at step 2 of frame lifecycle — never during step 3 (world.step()).
      Sub-frame delay is imperceptible to user.
      Prerequisite for: player-controlled objects, destructible bodies, stable real-time interaction.

- [ ] **Fixed timestep accumulator — Clock Mode** ⚠️ DESIGN CONVERSATION REQUIRED
      Currently world.py steps pymunk with variable timestep tied to frame render time.
      Causes 1–2 BPM drift in controlled scenes (confirmed via FL Studio tap tempo).
      Fix: fixed-timestep accumulator — physics steps in equal increments, leftover time
      carries to next frame. Implement deferred queue first, then this.

      Two simulation modes as a global toggle:
      - **Chaos Mode** — current behavior. Variable timestep, drift allowed, every run unique.
        Organic, generative, best for live performance. Default. Existing scenes unaffected.
      - **Clock Mode** — fixed timestep. Fully deterministic and reproducible.
        Tempo-stable. Enables scene reproduction, DAW sync, scientific documentation.
      Neither mode is deprecated — both are valid creative tools.

- [ ] **MusicalEvent expansion**
      CollisionEvent → MusicalEvent with energy, contact point position,
      surface normal, timestamp. Data model upgrade not a feature.
      Everything downstream benefits from richer event data.
      Prerequisite for: collision priority system, CC output, future quantization.

- [ ] **Minimal global settings (early subset)**
      Small centralized settings dict for what Tier 1–2 needs immediately:
      - Simulation mode (Chaos / Clock)
      - Ball/wall collision priority (Ball wins / Wall wins)
      - Note cooldown value + toggle
      Full settings UI comes in Tier 7. Establish the pattern now — nothing ad hoc.

- [ ] **Emitter notes — fully list-driven at runtime**
      world.py emitter still has minor legacy debt in `add_emitter` signature.
      Verify emitter tool passes `notes=list` correctly end-to-end, no string paths survive.

- [ ] **transpose() in scales.py**
      `def transpose(notes, semitones): return normalize_notes([n + semitones for n in notes])`
      Wire keyboard shortcuts: Shift+Up/Down = transpose selected ±1 semitone.
      Multi-select transpose already works via buttons — shortcuts make it feel like an instrument.

---

### Tier 2 — Core musical behavior

- [ ] **Ball/wall note collision priority toggle**
      Currently implicit — undefined which body provides the note on collision.
      Global toggle (lives in minimal global settings above):
      - **Ball wins** — ball is melodic voice, wall is trigger. Pinball paradigm.
      - **Wall wins** — wall is instrument, ball is mallet. Xylophone/Arkanoid paradigm.
      Cooldown applies to whichever body wins — not hardcoded to ball.
      Future: **Both play** — both notes fire, producing intervals/chords on collision.

- [ ] **Global note cooldown**
      Per-emitter minimum interval between note-ons from the same source body.
      Tames settling balls / Euler's disc retriggering without quantizing physics.
      Physically analogous to mechanical reset time on real instruments.
      Cooldown timer lives on whichever body wins collision priority:
      - Ball wins → cooldown on ball
      - Wall wins → cooldown on wall
      - Both play → independent timers on each
      Controls: slider 0ms–500ms (default ~30ms) + disable toggle.
      0 / disabled = fully raw physics, Euler's disc behavior fully preserved.
      Does NOT prevent chords — different bodies have independent timers.

- [ ] **Quantizer / beat scheduler**
      Buffer MusicalEvents, snap to nearest 1/16th (configurable).
      Strictly opt-in — raw physics timing is a feature not a problem.
      Requires MusicalEvent expansion + Clock Mode first.

- [ ] **Note duration display** — show next note to fire for emitters in properties panel

---

### Tier 3 — Input & UI

- [ ] **Tool rail → top bar** (UI layout change)
      Move tool icon rail from left sidebar into top bar as a second row of icons.
      Left sidebar that currently holds tool icons is removed entirely.
      All other sidebars (defaults panel, properties panel, global panel) stay in place.
      Net result: more canvas width, less wasted top bar space.
      Tool order: previous sidebar top-to-bottom becomes top bar left-to-right.
      1–5 keybinds select from this left-to-right order.
      Follow DPG initialization order — bind themes after windows exist.

- [ ] **Keybinds**
      Implement after pivot bug is fixed to avoid conflicting with arrow key restoration.

      Tool selection:
      - `1`–`5` → select tools 1–5 in top bar left-to-right order

      Selected object nudge (restore + formalize):
      - `Arrow keys` → nudge selected body in world space, pivot stays

      Selected object rotate (non-kinematic only: walls, lines, boxes):
      - `Numpad 7` → rotate counter-clockwise
      - `Numpad 9` → rotate clockwise
      - Rotation center = centroid of selection
        Single object = own center. Multi-select = average center of all selected.

      Selected object scale (walls/lines, length only):
      - `Numpad 1` → decrease length
      - `Numpad 3` → increase length
      - Wall thickness is a separate UI property — not affected by this keybind

      Viewport pan:
      - `Numpad 4` → pan left
      - `Numpad 8` → pan up
      - `Numpad 6` → pan right
      - `Numpad 2` → pan down
      Arrow keys = object manipulation. Numpad = viewport navigation.
      Intentionally separate. Matches Blender muscle memory.

- [ ] **Wall thickness as UI property**
      pymunk Segment shapes have a radius property (effectively thickness).
      Expose in properties panel alongside length and note.
      Numpad 1/3 affects length only — thickness via properties panel.

- [ ] **Duplicate tool** — click+drag leaves original, places copy at drag destination
- [ ] **Grid overlay** — toggleable world-unit grid
- [ ] **Grid snap** — Ctrl held snaps placement/movement to grid
- [ ] **File menu button** — moves save/load/clear out of top bar into dropdown

---

### Tier 4 — CC Output & Physics Data

      Architecture: CC output is a pure consumer of physics state snapshot.
      Same pattern as visuals.py — optional module, no simulation dependency.
      Disable at startup = zero effect on simulation.

- [ ] **Physics state snapshot** — `world.get_state_snapshot()`
      Read-only struct produced by world.py after step() completes each frame.
      Contains: positions, velocities, angular velocities, collision data.
      Both CC output and visuals.py consume this. Neither reaches into world.py directly.
      Formalizes one-way data flow. Add this before building CC or visuals modules.

      Available physics data from pymunk:
      - Per body: position x/y, velocity x/y + magnitude, angular velocity,
        rotation angle, mass, kinetic energy
      - Per collision (Arbiter): impulse energy, contact point in world space,
        contact point position along wall surface, angle of impact, first-contact flag

- [ ] **CC Output Module** (`cc_output.py`)
      Subscribes to state snapshot. Outputs continuous MIDI CC each frame.
      CC channel + number configured in IMP settings per mapping.
      Matched manually in FL Studio: right-click knob → Link to controller.
      FL Studio handles smoothing internally. IMP sends clean values at controlled rate.

      Physics→MIDI mappings:
      - Ball speed → filter cutoff (CC71 typical)
      - Ball height (y) → reverb send / volume
      - Ball x position → panning (CC10)
      - Spin rate → mod wheel / LFO rate (CC1)
      - Collision energy → expression / accent
      - Contact point position along wall → any CC (physical theremin)

- [ ] **CC Zone Tool**
      Invisible-to-physics region outputting CC based on ball position within zone.
      Zone defines its own 0–127 range — world coordinates and zoom irrelevant.
      Fits drop-in tool architecture (no collision geometry, pure output).
      - **CC Box** — 2D, x → CC A, y → CC B simultaneously
      - **CC Line** — 1D, position along line → one CC
      - **CC Circle** — distance from center → CC (proximity instrument)

- [ ] **object group_id / instrument_id** — multi-instrument MIDI channel routing

---

### Tier 5 — New Physics Tools

- [ ] **Polygon primitive** — configurable sides parameter
      3 = triangle, 4 = square, higher = more circular.
      pymunk native polygon support — not a workaround.
      Makes rotation/spin visually readable. Shape as tool property.

- [ ] **Destructible bodies** — hit counter, removed on depletion
      Requires deferred mutation queue (safe body removal).
      Enables Arkanoid-style layouts, finite-use note sources.

- [ ] **Player-controlled body** — keyboard-driven kinematic body
      Requires deferred mutation queue (continuous real-time mutation).

- [ ] **Physically oscillating wall as tool** — user-tunable frequency + amplitude
      Kinematic body. Separate from cosmetic wall vibration in visuals.py.

---

### Tier 6 — Display Layer / visuals.py

      Hard boundary between simulation and display.
      All DPG draw calls originate from display layer only.
      World.py produces read-only state snapshot. visuals.py consumes it.
      One-way data flow. Modeled after Blender viewport shading + Powder Toy visual presets.
      visuals.py is optional — disable at startup, sim runs identically without it.

- [ ] **Simulation/display decoupling refactor** ⚠️ PREREQUISITE for all visual features
      Move all DPG draw calls out of world.py into visuals.py.
      World.py produces snapshot (Tier 4). visuals.py consumes it.
      Do this before any visual feature — debt compounds fast otherwise.

- [ ] **visuals.py — Display Manager Module**
      Pure consumer of snapshot + event bus. No simulation dependency.
      Deletion leaves IMP functionally identical except appearance.

- [ ] **Display modes**
      - **Minimal** — current behavior, plain colors, no effects
      - **Musical** — HSV note colors, polygon shape rendering, spin indicators
      - **Expressive** — above plus trails and wall vibration
      - **Debug** — velocity vectors, collision normals, body IDs, timestep info

- [ ] **HSV note color system** — `get_ball_color(note, octave) → (r, g, b)`
      Hue = chromatic position C→B mapped 0°–360° (smooth rainbow on chromatic scale).
      Value = octave (dim low, bright high). Saturation = 1.0.
      C hue offset = global setting, real-time adjustable.
      Sequence balls update color on note advance. Trail inherits color at note-on.

- [ ] **Trail system**
      Trail duration = sustain value (no new data needed — already tracked).
      Starts on note-on, fades on note-off.
      Scale balls leave multicolored trails — visual history of note output.
      Decaying polyline in DPG draw layer.

- [ ] **Wall vibration effect** — cosmetic only, physics segment never moves
      Sine wave overlay on wall position. Amplitude = impact velocity.
      Oscillation frequency loosely maps to pitch. Decay maps to sustain.

- [ ] **Spin indicator** — dual-tone hemispheres on circular balls rotating with body angle

- [ ] **Wall note display** — HSV tint or note label on walls for readable tuned layouts

- [ ] **Visual mode** — F11 hides all panels, canvas fills window, aspect ratio presets
      For recording, performance, demo capture.

---

### Tier 7 — Global Settings (full system)

      Minimal early subset lives in Tier 1. This is the complete formalized system.

- [ ] **settings.py — Global settings module**
      All session-wide behavioral switches in one place:
      - Simulation mode (Chaos / Clock)
      - Ball/wall collision priority + Both play toggle
      - Note cooldown value + toggle
      - C hue offset
      - Display mode
      - CC output mappings
      - MIDI channel defaults
      Settings UI panel. Values persist with scene save (.imp file).

---

### Tier 8 — Known debt

- [ ] **Attractor draw_preview()** — uses raw screen coords, should use cam.w2s
- [ ] **slot_None.imp** in quicksave — legacy file, safe to delete manually
- [ ] **Velocity scaling calibration** — impulse_scale (600.0) may need tuning per scene

---

## Scene Archetypes (Planned Presets)

- **Xylophone** — wall-wins, walls tuned to scale, ball is passive mallet,
  Clock Mode for timing, wall note labels visible.
- **Arkanoid** — wall-wins, destructible blocks, player paddle, Expressive display mode.
- **Pinball** — ball-wins, bumper clusters, oscillating flappers,
  Chaos Mode, trails show ball path history.

---

## NOT PLANNED

- Real shader post-processing (use ReShade externally)
- Wind zones / gravity zones (Attractor covers this)
- 3D physics

---

## AI Agent Rules

- Read ARCHITECTURE.md before touching any file.
- Read this file to know what's done and what's next.
- **Update ARCHITECTURE.md, ROADMAP.md, README.md, and CONTEXT_handoff.md when work is complete.**
- One atomic change at a time. Syntax-check between edits.
- Do not rename or restructure modules without explicit instruction.
- Do not install new dependencies without confirmation.
- Frame lifecycle is defined in ARCHITECTURE.md — respect step ordering.
  Never modify physics bodies during world.step(). Always use the mutation queue.
- When in doubt, ask.
