import dearpygui.dearpygui as dpg
import math
from .base import BaseTool

class RotatingWallTool(BaseTool):
    name = "Rotating Wall"
    icon = "rotate"

    placement_props = [
        {"key": "rot_speed",    "label": "Speed (deg/s)", "type": "float", "default": 90.0,  "step": 5.0},
        {"key": "pass_through", "label": "Pass-Through",  "type": "bool",  "default": False},
    ]

    def __init__(self, defaults):
        super().__init__(defaults)
        self.start_pos = None; self.current_pos = None

    def on_mouse_click(self, world, pos, cam=None):
        self.start_pos = pos; self.current_pos = pos

    def on_mouse_drag(self, world, pos, cam=None):
        self.current_pos = pos

    def on_mouse_release(self, world, pos, cam=None):
        if self.start_pos and self.current_pos:
            dx = self.current_pos[0]-self.start_pos[0]
            dy = self.current_pos[1]-self.start_pos[1]
            length = math.sqrt(dx*dx+dy*dy)
            angle = math.degrees(math.atan2(dy, dx))
            if length > 5:
                shapes = world.add_rotating_wall(
                    self.start_pos, length,
                    speed=self.defaults.get("rot_speed", 90.0),
                    start_angle=angle,
                    friction=self.defaults["friction"],
                    elasticity=self.defaults["elasticity"],
                    notes=self.get_notes(),
                    channel=self.defaults["channel"],
                    trigger_midi=self.defaults.get("trigger_midi", True)
                )
                for s in shapes:
                    s.sensor = self.defaults.get("pass_through", False)
                world.selected_shapes = shapes
        self.start_pos = None; self.current_pos = None

    def draw_preview(self, canvas, canvas_h, cam=None):
        if self.start_pos and self.current_pos:
            p1 = cam.w2s(self.start_pos, canvas_h) if cam else (self.start_pos[0]+220, canvas_h-self.start_pos[1])
            p2 = cam.w2s(self.current_pos, canvas_h) if cam else (self.current_pos[0]+220, canvas_h-self.current_pos[1])
            dpg.draw_line(p1, p2, color=(255, 100, 255, 150), thickness=4, parent=canvas)
            dpg.draw_circle(p1, 5, color=(255, 100, 255, 200), fill=(255, 100, 255, 100), parent=canvas)

    @staticmethod
    def get_properties(obj):
        import pymunk
        if not isinstance(obj, pymunk.Segment) or getattr(obj, "shape_type", "") != "RotatingWall": return []
        return [
            {"key": "speed",       "label": "Speed (deg/s)", "type": "float", "value": getattr(obj, "speed", 90.0), "step": 5.0},
            {"key": "friction",    "label": "Friction",      "type": "float", "value": obj.friction,   "min": 0.0, "step": 0.05},
            {"key": "elasticity",  "label": "Elasticity",    "type": "float", "value": obj.elasticity, "min": 0.0, "step": 0.05},
            {"key": "trigger_midi","label": "Trigger MIDI",  "type": "bool",  "value": getattr(obj, "trigger_midi", True)},
            {"key": "sensor",      "label": "Pass-Through",  "type": "bool",  "value": obj.sensor},
        ]
