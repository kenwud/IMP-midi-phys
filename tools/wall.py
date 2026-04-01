import dearpygui.dearpygui as dpg
from .base import BaseTool

class WallTool(BaseTool):
    name = "Wall"
    icon = "minus"
    placement_props = []  # uses only global defaults

    def __init__(self, defaults):
        super().__init__(defaults)
        self.start_pos = None
        self.current_pos = None

    def on_mouse_click(self, world, pos, cam=None):
        self.start_pos = pos
        self.current_pos = pos

    def on_mouse_drag(self, world, pos, cam=None):
        self.current_pos = self.angle_snap(self.start_pos, pos) if self.start_pos else pos

    def on_mouse_release(self, world, pos, cam=None):
        if self.start_pos and self.current_pos:
            end = self.angle_snap(self.start_pos, pos)
            dx = end[0] - self.start_pos[0]
            dy = end[1] - self.start_pos[1]
            if dx*dx + dy*dy > 25:
                shapes = world.add_wall(
                    self.start_pos, end,
                    friction=self.defaults["friction"],
                    elasticity=self.defaults["elasticity"],
                    note=self.get_note(),
                    channel=self.defaults["channel"],
                    trigger_midi=self.defaults.get("trigger_midi", True)
                )
                world.selected_shapes = shapes
        self.start_pos = None; self.current_pos = None

    def draw_preview(self, canvas, canvas_h, cam=None):
        if self.start_pos and self.current_pos:
            p1 = cam.w2s(self.start_pos, canvas_h) if cam else (self.start_pos[0]+220, canvas_h-self.start_pos[1])
            p2 = cam.w2s(self.current_pos, canvas_h) if cam else (self.current_pos[0]+220, canvas_h-self.current_pos[1])
            dpg.draw_line(p1, p2, color=(255, 255, 255, 120), thickness=2, parent=canvas)

    @staticmethod
    def get_properties(obj):
        import pymunk
        if not isinstance(obj, pymunk.Segment): return []
        if getattr(obj, "shape_type", "Wall") not in ("Wall", "HollowBox", "HollowCircle"): return []
        return [
            {"key": "friction",    "label": "Friction",     "type": "float", "value": obj.friction,    "min": 0.0, "step": 0.05},
            {"key": "elasticity",  "label": "Elasticity",   "type": "float", "value": obj.elasticity,  "min": 0.0, "step": 0.05},
            {"key": "trigger_midi","label": "Trigger MIDI", "type": "bool",  "value": getattr(obj, "trigger_midi", True)},
            {"key": "sensor",      "label": "Pass-Through", "type": "bool",  "value": obj.sensor},
        ]
