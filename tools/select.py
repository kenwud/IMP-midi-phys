import dearpygui.dearpygui as dpg
from .base import BaseTool

class SelectTool(BaseTool):
    name = "Select"
    icon = "arrow-pointer"
    placement_props = []

    def __init__(self, defaults):
        super().__init__(defaults)
        self.start_pos = None
        self.current_pos = None
        self.is_dragging = False

    def on_mouse_click(self, world, pos, cam=None):
        self.start_pos = pos; self.current_pos = pos; self.is_dragging = False
        multi = dpg.is_key_down(dpg.mvKey_LShift) or dpg.is_key_down(dpg.mvKey_RShift)
        zoom = cam.zoom if cam else 1.0
        world.select_at(pos, multi=multi, zoom=zoom)

    def on_mouse_drag(self, world, pos, cam=None):
        self.current_pos = pos
        if abs(pos[0]-self.start_pos[0]) > 5 or abs(pos[1]-self.start_pos[1]) > 5:
            self.is_dragging = True

    def on_mouse_release(self, world, pos, cam=None):
        if self.is_dragging:
            world.select_box(self.start_pos, pos)
        self.is_dragging = False; self.start_pos = None

    def draw_preview(self, canvas, canvas_h, cam):
        if self.is_dragging and self.start_pos and self.current_pos:
            p1 = cam.w2s(self.start_pos, canvas_h)
            p2 = cam.w2s(self.current_pos, canvas_h)
            dpg.draw_rectangle(p1, p2, color=(100, 255, 100, 100), fill=(100, 255, 100, 30), parent=canvas)
