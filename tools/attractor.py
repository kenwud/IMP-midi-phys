import dearpygui.dearpygui as dpg
import math, time
from .base import BaseTool

class AttractorTool(BaseTool):
    name = "Attractor"
    icon = "magnet"

    placement_props = [
        {"key": "att_strength", "label": "Strength", "type": "float", "default": 20.0, "step": 5.0},
        {"key": "att_falloff",  "label": "Falloff",  "type": "float", "default": 2.0,  "min": 0.1, "step": 0.1},
    ]

    def on_mouse_click(self, world, pos, cam=None):
        a = world.add_attractor(pos,
            strength=self.defaults.get("att_strength", 20.0),
            falloff=self.defaults.get("att_falloff", 2.0))
        world.selected_shapes = [a]

    def on_mouse_drag(self, world, pos, cam=None): pass
    def on_mouse_release(self, world, pos, cam=None): pass

    def draw_preview(self, canvas, canvas_h, cam):
        mx, my = dpg.get_mouse_pos(local=True)
        if mx < 220: return
        pos = (mx, my)
        pulse = (10 + 5 * math.sin(time.time() * 10)) * cam.zoom
        dpg.draw_circle(pos, pulse, color=(255, 200, 100, 150), fill=(255, 200, 100, 50), parent=canvas)
        for r in [50, 100]:
            dpg.draw_circle(pos, r * cam.zoom, color=(255, 200, 100, 50), thickness=1, parent=canvas)

    @staticmethod
    def get_properties(obj):
        if not isinstance(obj, dict) or obj.get("shape_type") != "Attractor": return []
        return [
            {"key": "strength",    "label": "Strength",       "type": "float", "value": obj.get("strength", 20.0), "step": 5.0},
            {"key": "falloff",     "label": "Falloff",        "type": "float", "value": obj.get("falloff", 2.0),   "min": 0.1, "step": 0.1},
            {"key": "visible",     "label": "Visible",        "type": "bool",  "value": obj.get("visible", True)},
            {"key": "trigger_midi","label": "Trigger MIDI",   "type": "bool",  "value": obj.get("trigger_midi", False)},
            {"key": "threshold",   "label": "Trigger Radius", "type": "float", "value": obj.get("threshold", 50.0), "min": 1.0, "step": 5.0},
            {"key": "channel",     "label": "Channel (1-16)", "type": "int",   "value": obj.get("channel", 0)+1, "min": 1, "max": 16},
        ]
