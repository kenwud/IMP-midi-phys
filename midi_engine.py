import time
from event_bus import CollisionEvent, ProximityEvent, TransportEvent
from scales import midi_to_note_name
from tools.base import next_note


# ---------------------------------------------------------------------------
# MusicalEvent
# ---------------------------------------------------------------------------
# Sits between raw CollisionEvent/ProximityEvent and MIDI output.
# Carries musical intent, not physics data.
# Future: a musical_engine module will transform CollisionEvents into
# MusicalEvents before they reach here, enabling quantization, grouping,
# routing — all opt-in and non-destructive to the raw physics feel.

class MusicalEvent:
    """
    A resolved musical intention: note, velocity, duration, channel.
    Created from a physics event; consumed by _emit().

    source: "collision" | "proximity"  — for future routing/filtering
    timestamp: perf_counter ms at creation (monotonic, high-res)
    """
    __slots__ = ("note", "velocity", "channel", "duration_ms", "source", "timestamp")

    def __init__(self, note, velocity, channel, duration_ms, source="collision"):
        self.note        = note
        self.velocity    = velocity
        self.channel     = channel
        self.duration_ms = duration_ms
        self.source      = source
        self.timestamp   = time.perf_counter() * 1000


# ---------------------------------------------------------------------------
# MidiEngine
# ---------------------------------------------------------------------------

class MidiEngine:
    """
    Translates physics events into MIDI output.

    Pipeline (current):
        CollisionEvent / ProximityEvent
            → _select_note()          # musical decision: which note, which channel
            → MusicalEvent            # resolved intent
            → _emit(event)            # MIDI send + schedule note-off
            → tick()                  # fires scheduled note-offs each frame

    Pipeline (future, opt-in):
        CollisionEvent
            → musical_engine          # quantize, group, route  (NEW MODULE)
            → MusicalEvent
            → _emit()                 # this file unchanged

    Timing
    ------
    Uses time.perf_counter() throughout — monotonic, high-resolution,
    unaffected by NTP or system clock adjustments. Do NOT mix with
    time.time() in timing-sensitive paths.

    Sustain modes
    -------------
    "fixed"    — all notes held for sustain_ms ms
    "velocity" — duration = sustain_ms * (velocity / 127)  (harder = longer)

    Quantization (future)
    ---------------------
    Quantization will be opt-in via a toggle in the UI.
    Off by default — raw physics timing is a feature, not a bug.
    When enabled, MusicalEvents will be nudged to the nearest beat-grid
    point before _emit() is called, without changing any physics.
    """

    def __init__(self, midi_output, event_bus):
        self.midi = midi_output
        self.bus  = event_bus

        # Velocity
        self.dynamic_velocity     = True
        self.velocity_sensitivity = 0.5
        self.fixed_velocity       = 100
        self.impulse_scale        = 600.0   # impulse magnitude → vel ~100

        # Sustain
        self.sustain_ms   = 80
        self.sustain_mode = "fixed"         # "fixed" | "velocity"

        # Note-off queue: list of (fire_at_perf_ms, note, channel)
        # Ordered by insertion; at our note counts linear scan is fine.
        # Future: replace with heapq if note counts grow large.
        self._note_queue = []

        # Ball-ball MIDI toggle
        self.ball_ball_midi = False

        # CC mapping
        self.cc_mapping = None
        self.cc_number  = 1

        # UI monitor — read by main loop to update top-bar display
        self.last_note       = -1
        self.last_velocity   = 0
        self.last_channel    = 0
        self.last_event_info = ""

        self.bus.subscribe(self.handle_event)

    # ------------------------------------------------------------------
    # Per-frame tick — must be called once per frame from main loop
    # ------------------------------------------------------------------

    def tick(self):
        """Fire any scheduled note-offs whose time has arrived."""
        now = time.perf_counter() * 1000
        remaining = []
        for fire_at, note, ch in self._note_queue:
            if now >= fire_at:
                self.midi.send_note_off(note, channel=ch)
            else:
                remaining.append((fire_at, note, ch))
        self._note_queue = remaining

    # ------------------------------------------------------------------
    # Output stage — receives a resolved MusicalEvent
    # ------------------------------------------------------------------

    def _emit(self, event: MusicalEvent):
        """
        Send note-on immediately; schedule note-off.
        This is the only place MIDI messages are sent for notes.
        Future quantizer will call this after nudging event.timestamp.
        """
        self.midi.send_note_on(event.note,
                               velocity=event.velocity,
                               channel=event.channel)
        fire_at = time.perf_counter() * 1000 + event.duration_ms
        self._note_queue.append((fire_at, event.note, event.channel))

        self.last_note       = event.note
        self.last_velocity   = event.velocity
        self.last_channel    = event.channel
        self.last_event_info = (
            f"{midi_to_note_name(event.note)} "
            f"| V:{event.velocity} | Ch:{event.channel + 1}"
        )

    # ------------------------------------------------------------------
    # Musical helpers
    # ------------------------------------------------------------------

    def _calc_velocity(self, impulse_magnitude) -> int:
        """Map pymunk impulse magnitude to MIDI velocity 1–127."""
        if not self.dynamic_velocity:
            return self.fixed_velocity
        dynamic = int(
            (impulse_magnitude / self.impulse_scale) * 127
            * self.velocity_sensitivity
            + self.fixed_velocity * (1.0 - self.velocity_sensitivity)
        )
        return max(1, min(127, dynamic))

    def _calc_duration(self, velocity) -> float:
        """Return note-off delay in ms based on sustain settings."""
        if self.sustain_mode == "velocity":
            return max(10.0, self.sustain_ms * (velocity / 127.0))
        return float(self.sustain_ms)

    def _select_note(self, shape) -> tuple[int, int]:
        """
        Extract and advance the melody for a shape or emitter dict.
        Returns (note, channel).
        Delegates sequencing to next_note() in base.py — single source of truth.
        """
        note    = next_note(shape)
        channel = shape.get("channel", 0) if isinstance(shape, dict) else getattr(shape, "channel", 0)
        return note, channel

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    def handle_event(self, event):
        if isinstance(event, TransportEvent):
            if not event.playing:
                self.panic()
            return
        if isinstance(event, ProximityEvent):
            self._handle_proximity(event)
            return
        if isinstance(event, CollisionEvent):
            self._handle_collision(event)

    def _handle_proximity(self, event):
        if event.ball_shape:
            note, channel = self._select_note(event.ball_shape)
        else:
            note, channel = self._select_note(event.attractor)

        me = MusicalEvent(
            note=note,
            velocity=self.fixed_velocity,
            channel=channel,
            duration_ms=self._calc_duration(self.fixed_velocity),
            source="proximity",
        )
        self._emit(me)
        # Proximity overrides the event info label to show source
        self.last_event_info = (
            f"{midi_to_note_name(note)} | PROX | Ch:{channel + 1}"
        )

    def _handle_collision(self, event):
        vel     = event.velocity
        impulse = vel.length if hasattr(vel, "length") else float(vel)
        sa, sb  = event.shape_a, event.shape_b
        both_balls = (getattr(sa, "is_ball", False)
                      and getattr(sb, "is_ball", False))

        for shape in (sa, sb):
            if not getattr(shape, "is_ball", False):
                continue
            other = sb if shape is sa else sa

            if both_balls and not self.ball_ball_midi:
                continue
            if not getattr(other, "trigger_midi", True):
                continue

            note, channel = self._select_note(shape)
            velocity      = self._calc_velocity(impulse)

            me = MusicalEvent(
                note=note,
                velocity=velocity,
                channel=channel,
                duration_ms=self._calc_duration(velocity),
                source="collision",
            )
            self._emit(me)

        if self.cc_mapping:
            self._process_cc(event, impulse)

    # ------------------------------------------------------------------
    # CC mapping
    # ------------------------------------------------------------------

    def _process_cc(self, event, impulse):
        shape = (event.shape_a
                 if getattr(event.shape_a, "is_ball", False)
                 else event.shape_b)
        if not getattr(shape, "is_ball", False):
            return
        channel = getattr(shape, "channel", 0)

        if self.cc_mapping == "height":
            # Clamp immediately — world height varies
            raw = (shape.body.position.y / 800.0) * 127
        elif self.cc_mapping == "speed":
            raw = (shape.body.velocity.length / 1500.0) * 127
        elif self.cc_mapping == "impulse":
            raw = (impulse / self.impulse_scale) * 127
        else:
            raw = 0

        val = max(0, min(127, int(raw)))
        self.midi.send_cc(self.cc_number, val, channel=channel)
        self.last_event_info = f"CC#{self.cc_number}:{val} | Ch:{channel + 1}"

    # ------------------------------------------------------------------

    def panic(self):
        """Stop all sound and clear pending note-offs."""
        self._note_queue.clear()
        self.midi.panic()
