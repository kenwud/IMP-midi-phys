import dearpygui.dearpygui as dpg
from .base import BaseTool

class BoxTool(BaseTool):
    name = "Hollow Box"
    icon = "square"
    placement_props = []

    def __init__(self, defaults):
        super().__init__(defaults)
        self.start_pos = None
        self.current_pos = None

    def on_mouse_click(self, world, pos, cam=None):
        self.start_pos = pos; self.current_pos = pos

    def on_mouse_drag(self, world, pos, cam=None):
        self.current_pos = pos

    def on_mouse_release(self, world, pos, cam=None):
        if self.start_pos and self.current_pos:
            dx = abs(self.current_pos[0]-self.start_pos[0])
            dy = abs(self.current_pos[1]-self.start_pos[1])
            if dx > 5 and dy > 5:
                shapes = world.add_hollow_box(
                    self.start_pos, self.current_pos,
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
            dpg.draw_rectangle(p1, p2, color=(255, 255, 255, 100), thickness=2, parent=canvas)
