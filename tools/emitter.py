import dearpygui.dearpygui as dpg
import math
from .base import BaseTool, BALL_SPAWN_PROPS

class EmitterTool(BaseTool):
    name = "Emitter"
    icon = "circle-dot"

    placement_props = [
        {"key": "emit_interval", "label": "Interval (ms)", "type": "int",   "default": 1000, "min": 50,  "step": 100},
        {"key": "emit_angle",    "label": "Angle (deg)",   "type": "float", "default": 90.0, "step": 5.0},
        {"key": "emit_speed",    "label": "Speed",         "type": "float", "default": 200.0,"min": 1.0, "step": 10.0},
        {"key": "emit_spread",   "label": "Spread",        "type": "float", "default": 10.0, "min": 0.0, "step": 1.0},
        {"key": "emit_max",      "label": "Max Balls",     "type": "int",   "default": 10,   "min": 1},
    ] + BALL_SPAWN_PROPS

    def on_mouse_click(self, world, pos, cam=None):
        notes = self.get_notes()
        emitter = world.add_emitter(
            pos,
            interval_ms=self.defaults.get("emit_interval", 1000),
            angle=self.defaults.get("emit_angle", 90.0),
            speed=self.defaults.get("emit_speed", 200.0),
            spread=self.defaults.get("emit_spread", 10.0),
            max_balls=self.defaults.get("emit_max", 10),
            notes=notes,
            elasticity=self.defaults["elasticity"],
            friction=self.defaults["friction"],
            ball_radius=self.defaults.get("ball_radius", 10.0),
            ball_mass=self.defaults.get("ball_mass", 1.0),
        )
        world.selected_shapes = [emitter]

    def on_mouse_drag(self, world, pos, cam=None): pass
    def on_mouse_release(self, world, pos, cam=None): pass

    @staticmethod
    def get_properties(obj):
        if not isinstance(obj, dict) or obj.get("shape_type") != "Emitter": return []
        return [
            {"key": "interval_ms", "label": "Interval (ms)", "type": "int",   "value": obj.get("interval_ms", 1000), "min": 50, "step": 100},
            {"key": "angle",       "label": "Angle (deg)",   "type": "float", "value": obj.get("angle", 90.0),       "step": 5.0},
            {"key": "speed",       "label": "Speed",         "type": "float", "value": obj.get("speed", 200.0),      "min": 1.0, "step": 10.0},
            {"key": "spread",      "label": "Spread",        "type": "float", "value": obj.get("spread", 10.0),      "min": 0.0, "step": 1.0},
            {"key": "max_balls",   "label": "Max Balls",     "type": "int",   "value": obj.get("max_balls", 10),     "min": 1},
            {"key": "elasticity",  "label": "Elasticity",    "type": "float", "value": obj.get("elasticity", 0.8),  "min": 0.0, "step": 0.05},
            {"key": "friction",    "label": "Friction",      "type": "float", "value": obj.get("friction", 0.1),    "min": 0.0, "step": 0.05},
        ]
