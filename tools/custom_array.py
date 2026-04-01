import dearpygui.dearpygui as dpg
import math, uuid
from .base import BaseTool, BALL_SPAWN_PROPS, parse_notes

class CustomArrayTool(BaseTool):
    """
    Drag out a line of balls whose notes come from a custom comma-separated
    string rather than a scale formula.

    Direction modes:
      Ascending  — left-to-right through the string, cycling if count > len
      Descending — right-to-left through the string, cycling
      Mirror     — ping-pong back and forth through the string
    """
    name = "Custom Array"
    icon = "list"

    placement_props = [
        {"key": "ca_notes",  "label": "Notes (CSV)",  "type": "text",  "default": "60,64,67,72"},
        {"key": "ca_count",  "label": "Count",        "type": "int",   "default": 5,    "min": 1, "step": 1},
        {"key": "ca_mode",   "label": "Direction",    "type": "combo", "default": "Ascending",
         "options": ["Ascending", "Descending", "Mirror"]},
    ] + BALL_SPAWN_PROPS

    def __init__(self, defaults):
        super().__init__(defaults)
        self.start_pos = None
        self.current_pos = None

    # ------------------------------------------------------------------
    def _build_sequence(self, base_notes, count, mode):
        """Expand base_notes to exactly count notes according to mode."""
        if not base_notes:
            base_notes = [60]
        n = len(base_notes)

        if mode == "Descending":
            src = list(reversed(base_notes))
            return [src[i % n] for i in range(count)]

        elif mode == "Mirror":
            # ping-pong: forward then backward (no repeated endpoints)
            if n == 1:
                return [base_notes[0]] * count
            mirror = base_notes + list(reversed(base_notes[1:-1]))
            m = len(mirror)
            return [mirror[i % m] for i in range(count)]

        else:  # Ascending (default)
            return [base_notes[i % n] for i in range(count)]

    # ------------------------------------------------------------------
    def on_mouse_click(self, world, pos, cam=None):
        self.start_pos = pos
        self.current_pos = pos

    def on_mouse_drag(self, world, pos, cam=None):
        self.current_pos = self.angle_snap(self.start_pos, pos) if self.start_pos else pos

    def on_mouse_release(self, world, pos, cam=None):
        if not (self.start_pos and self.current_pos):
            return
        end = self.angle_snap(self.start_pos, pos)
        dx = end[0] - self.start_pos[0]
        dy = end[1] - self.start_pos[1]
        if math.sqrt(dx*dx + dy*dy) < 10:
            self.start_pos = None; self.current_pos = None
            return

        count       = max(1, self.defaults.get("ca_count", 5))
        mode        = self.defaults.get("ca_mode", "Ascending")
        raw_notes   = parse_notes(self.defaults.get("ca_notes", "60,64,67,72"))
        notes       = self._build_sequence(raw_notes, count, mode)

        new_shapes = []
        for i in range(count):
            t = i / (count - 1) if count > 1 else 0
            px = self.start_pos[0] + dx * t
            py = self.start_pos[1] + dy * t
            res = world.add_ball(
                (px, py),
                radius=self.defaults.get("ball_radius", 10.0),
                mass=self.defaults.get("ball_mass", 1.0),
                note=notes[i],
                friction=self.defaults["friction"],
                elasticity=self.defaults["elasticity"],
                channel=self.defaults["channel"],
                uid=str(uuid.uuid4())
            )
            new_shapes.extend(res)
        world.selected_shapes = new_shapes
        self.start_pos = None; self.current_pos = None

    def draw_preview(self, canvas, canvas_h, cam):
        if not (self.start_pos and self.current_pos):
            return
        p1 = cam.w2s(self.start_pos, canvas_h)
        p2 = cam.w2s(self.current_pos, canvas_h)
        dpg.draw_line(p1, p2, color=(255, 255, 255, 80), thickness=1, parent=canvas)
        count = max(1, self.defaults.get("ca_count", 5))
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        r = self.defaults.get("ball_radius", 10.0) * cam.zoom
        raw_notes = parse_notes(self.defaults.get("ca_notes", "60,64,67,72"))
        seq = self._build_sequence(raw_notes, count, self.defaults.get("ca_mode", "Ascending"))
        for i in range(count):
            t = i / (count - 1) if count > 1 else 0
            px = p1[0] + dx * t
            py = p1[1] + dy * t
            # Tint cycles subtly so you can see note changes in preview
            hue_step = (i * 30) % 360
            col = (180, 255, 180, 200)  # green-ish to distinguish from scale array
            dpg.draw_circle((px, py), max(2, r), color=col, fill=(180, 255, 180, 50), parent=canvas)
