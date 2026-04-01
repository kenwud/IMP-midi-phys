import dearpygui.dearpygui as dpg
import math, uuid
from .base import BaseTool, BALL_SPAWN_PROPS
from scales import get_scale_notes, SCALE_NAMES


class ArrayTool(BaseTool):
    name  = "Array"
    icon  = "asterisk"

    placement_props = [
        {"key": "arr_count",  "label": "Count",         "type": "int",   "default": 5,
         "min": 2, "max": 64, "step": 1},
        {"key": "arr_scale",  "label": "Scale",         "type": "combo", "default": "Major",
         "options": SCALE_NAMES},
        {"key": "arr_root",   "label": "Root Note",     "type": "int",   "default": 60,
         "min": 0, "max": 127, "step": 1},
        {"key": "arr_octave", "label": "Octave Spread", "type": "int",   "default": 1,
         "min": 1, "max": 4,   "step": 1},
        {"key": "arr_mode",   "label": "Direction",     "type": "combo", "default": "Ascending",
         "options": ["Ascending", "Descending", "Ping-Pong"]},
    ] + BALL_SPAWN_PROPS

    def __init__(self, defaults):
        super().__init__(defaults)
        self.start_pos   = None
        self.current_pos = None

    def _build_notes(self, count):
        # sync_defaults_from_widgets() runs before on_mouse_click,
        # so self.defaults is always current here — no widget reads needed.
        root   = int(self.defaults.get("arr_root",   60))
        scale  = str(self.defaults.get("arr_scale",  "Major"))
        octave = int(self.defaults.get("arr_octave", 1))
        mode   = str(self.defaults.get("arr_mode",   "Ascending"))



        notes = get_scale_notes(root, scale, count, octave)

        if mode == "Descending":
            notes = list(reversed(notes))
        elif mode == "Ping-Pong":
            # True ping-pong: up then back, no repeated endpoints
            # e.g. [C D E F] -> [C D E F E D C D E F ...]
            if len(notes) >= 2:
                mirror = notes + list(reversed(notes[1:-1]))
                notes  = [mirror[i % len(mirror)] for i in range(count)]

        # Pad to exactly count notes by repeating the last
        while len(notes) < count:
            notes.append(notes[-1])

        return notes[:count]

    # ------------------------------------------------------------------

    def on_mouse_click(self, world, pos, cam=None):
        self.start_pos   = pos
        self.current_pos = pos

    def on_mouse_drag(self, world, pos, cam=None):
        if self.start_pos:
            self.current_pos = self.angle_snap(self.start_pos, pos)

    def on_mouse_release(self, world, pos, cam=None):
        if not self.start_pos:
            return

        end = self.angle_snap(self.start_pos, pos)
        dx  = end[0] - self.start_pos[0]
        dy  = end[1] - self.start_pos[1]

        if math.sqrt(dx * dx + dy * dy) > 10:
            count = int(self.defaults.get("arr_count", 5))
            notes = self._build_notes(count)

            new_shapes = []
            for i in range(count):
                t  = i / (count - 1) if count > 1 else 0
                px = self.start_pos[0] + dx * t
                py = self.start_pos[1] + dy * t
                shapes = world.add_ball(
                    (px, py),
                    radius=self.defaults.get("ball_radius", 10.0),
                    mass=self.defaults.get("ball_mass", 1.0),
                    notes=[notes[i]],
                    friction=self.defaults["friction"],
                    elasticity=self.defaults["elasticity"],
                    channel=self.defaults["channel"],
                    uid=str(uuid.uuid4()),
                )
                new_shapes.extend(shapes)

            world.selected_shapes = new_shapes

        self.start_pos = self.current_pos = None

    def draw_preview(self, canvas, canvas_h, cam):
        if not (self.start_pos and self.current_pos):
            return
        p1    = cam.w2s(self.start_pos,   canvas_h)
        p2    = cam.w2s(self.current_pos, canvas_h)
        count = int(self.defaults.get("arr_count", 5))
        r     = max(2, self.defaults.get("ball_radius", 10.0) * cam.zoom)
        dx    = p2[0] - p1[0]
        dy    = p2[1] - p1[1]
        dpg.draw_line(p1, p2, color=(255, 255, 255, 80), thickness=1, parent=canvas)
        for i in range(count):
            t  = i / (count - 1) if count > 1 else 0
            px = p1[0] + dx * t
            py = p1[1] + dy * t
            dpg.draw_circle((px, py), r,
                            color=(255, 255, 100, 200),
                            fill=(255, 255, 100, 60),
                            parent=canvas)
