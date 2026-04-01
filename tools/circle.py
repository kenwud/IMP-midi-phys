import dearpygui.dearpygui as dpg
import math
from .base import BaseTool

class CircleTool(BaseTool):
    name = "Hollow Circle"
    icon = "circle"
    placement_props = []

    def __init__(self, defaults):
        super().__init__(defaults)
        self.center = None
        self.current_pos = None

    def on_mouse_click(self, world, pos, cam=None):
        self.center = pos; self.current_pos = pos

    def on_mouse_drag(self, world, pos, cam=None):
        self.current_pos = pos

    def on_mouse_release(self, world, pos, cam=None):
        if self.center and self.current_pos:
            dx = self.current_pos[0]-self.center[0]
            dy = self.current_pos[1]-self.center[1]
            radius = math.sqrt(dx*dx+dy*dy)
            if radius > 5:
                shapes = world.add_hollow_circle(
                    self.center, radius,
                    friction=self.defaults["friction"],
                    elasticity=self.defaults["elasticity"],
                    note=self.get_note(),
                    channel=self.defaults["channel"],
                    trigger_midi=self.defaults.get("trigger_midi", True)
                )
                world.selected_shapes = shapes
        self.center = None; self.current_pos = None

    def draw_preview(self, canvas, canvas_h, cam=None):
        if self.center and self.current_pos:
            dx = self.current_pos[0]-self.center[0]
            dy = self.current_pos[1]-self.center[1]
            radius = math.sqrt(dx*dx+dy*dy)
            sp = cam.w2s(self.center, canvas_h) if cam else (self.center[0]+220, canvas_h-self.center[1])
            sr = radius * (cam.zoom if cam else 1.0)
            dpg.draw_circle(sp, sr, color=(255, 255, 255, 100), thickness=2, parent=canvas)
