"""
IMP Tool Base Classes
=====================
To create a new tool, subclass BaseTool and drop the file in /tools/.
It will be discovered and loaded automatically.

Required class attributes:
    name (str)  : Display name, e.g. "Ball"
    icon (str)  : Button label, e.g. "B"

Optional class attributes:
    placement_props (list): Tool-specific placement defaults (see below).
                            Global defaults (notes, channel, elasticity,
                            friction, trigger_midi) are injected
                            automatically — only declare extras here.

placement_props schema:
    [
        {
            "key":     str,   # internal key, stored in self.defaults
            "label":   str,   # shown in UI
            "type":    str,   # "float" | "int" | "bool" | "text"
            "default": any,   # initial value
            "min":     num,   # (optional) for float/int
            "max":     num,   # (optional) for float/int
            "step":    num,   # (optional) for float/int
        },
    ]

Notes access (preferred):
    self.get_note()   -> int  : first/primary MIDI note (0-127)
    self.get_notes()  -> list : full melody as list of ints

get_properties(obj) schema (for the selected-object panel):
    Returns same format as placement_props but each entry also has:
        "value": any   # current value read from the object

World API quick reference:
    world.add_ball(pos, radius, mass, friction, elasticity, note, channel, uid)
    world.add_wall(p1, p2, friction, elasticity, note, channel, trigger_midi, uid)
    world.add_hollow_circle(pos, radius, ...)
    world.add_hollow_box(p1, p2, ...)
    world.add_rotating_wall(pivot, length, speed, ...)
    world.add_oscillating_wall(center, length, sweep, speed, rest_angle, ...)
    world.add_attractor(pos, strength, falloff, uid)
    world.add_emitter(pos, interval_ms, angle, speed, spread, max_balls, ...)
    world.delete_shapes(shapes_list)
    world.select_at(pos, radius, multi, zoom)
    world.select_box(p1, p2)
    world.selected_shapes  -> list
    world.shapes           -> all pymunk shapes
    world.space            -> pymunk Space
"""

from abc import ABC, abstractmethod
import math
import dearpygui.dearpygui as dpg
from scales import normalize_notes, parse_notes


# ---------------------------------------------------------------------------
# next_note — canonical melody sequencer helper
# ---------------------------------------------------------------------------
# Call this from midi_engine (and anywhere else that needs to advance a
# shape's melody). Works on both pymunk shapes and emitter/attractor dicts.

def next_note(obj) -> int:
    """
    Read and advance the melody sequencer for a runtime object.
    obj must have .notes (list[int]) and .note_index (int).
    Returns the current note and increments note_index.
    """
    if isinstance(obj, dict):
        notes = obj.get("notes", [60])
        idx   = obj.get("note_index", 0)
        note  = notes[idx % len(notes)]
        obj["note_index"] = (idx + 1) % len(notes)
    else:
        notes = getattr(obj, "notes", [60])
        idx   = getattr(obj, "note_index", 0)
        note  = notes[idx % len(notes)]
        obj.note_index = (idx + 1) % len(notes)
    return note


# ---------------------------------------------------------------------------
# Shared ball spawn properties
# ---------------------------------------------------------------------------
# Any tool that spawns balls includes this list in its placement_props.
# Adding a new spawnable property = one edit here, propagates everywhere.
# Keys must match what world.add_ball() accepts and what on_prop_change handles.

BALL_SPAWN_PROPS = [
    {"key": "ball_radius", "label": "Radius", "type": "float",
     "default": 10.0, "min": 1.0, "step": 1.0},
    {"key": "ball_mass",   "label": "Mass",   "type": "float",
     "default": 1.0,  "min": 0.01, "step": 0.1},
]


class BaseTool(ABC):
    # Required
    name: str = "Unnamed Tool"
    icon: str = "?"

    # Declare tool-specific placement defaults here.
    # Global defaults (notes, channel, elasticity, friction,
    # trigger_midi) are always in self.defaults automatically.
    placement_props: list = []

    def __init__(self, defaults: dict):
        """defaults: merged global + tool-specific defaults dict."""
        self.defaults = defaults

    def get_notes(self):
        """Return the current notes list from defaults. Always non-empty."""
        return parse_notes(self.defaults.get("notes", "60"))

    def get_note(self):
        """Return the first (primary) note from defaults."""
        return self.get_notes()[0]

    @staticmethod
    def angle_snap(start, end, increment_deg=7.5):
        """
        If Shift is held, snap the end point so the line angle is a multiple
        of increment_deg, preserving the drag distance.
        Returns the (possibly snapped) end position.
        """
        if not (dpg.is_key_down(dpg.mvKey_LShift) or dpg.is_key_down(dpg.mvKey_RShift)):
            return end
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dist = math.sqrt(dx*dx + dy*dy)
        if dist < 1:
            return end
        angle = math.degrees(math.atan2(dy, dx))
        snapped = round(angle / increment_deg) * increment_deg
        rad = math.radians(snapped)
        return (start[0] + dist * math.cos(rad),
                start[1] + dist * math.sin(rad))

    # --- Mouse interaction (all coords are world-space) ---

    @abstractmethod
    def on_mouse_click(self, world, pos, cam=None):
        """Initial left-click."""
        pass

    @abstractmethod
    def on_mouse_drag(self, world, pos, cam=None):
        """Every frame while left button held."""
        pass

    @abstractmethod
    def on_mouse_release(self, world, pos, cam=None):
        """Left button released."""
        pass

    # --- Drawing ---

    def draw_preview(self, canvas, canvas_h, cam):
        """
        Draw placement ghost each frame.
        canvas_h: pixel height of canvas (for Y-flip)
        cam: Camera with .w2s(world_pos, canvas_h)
        """
        pass

    # --- Properties panel ---

    @staticmethod
    def get_properties(obj):
        """
        Return editable property descriptors for a selected object.
        The panel renders whatever this returns - no hardcoding in main.
        Override as @staticmethod on your tool class.

        Format: [{"key", "label", "type", "value", "min"?, "max"?, "step"?}]
        """
        return []
