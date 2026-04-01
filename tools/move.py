import dearpygui.dearpygui as dpg
import math
from .base import BaseTool

# How close to the pivot (in world units) counts as a pivot grab
PIVOT_GRAB_RADIUS = 14

class MoveTool(BaseTool):
    name = "Move"
    icon = "up-down-left-right"
    placement_props = []

    def __init__(self, defaults):
        super().__init__(defaults)
        self.target_shapes = []
        self.last_pos = None
        self.pivot_shape = None   # shape whose pivot we're dragging (not the whole body)

    def _pivot_pos(self, shape):
        """Return world-space pivot for a kinematic wall shape, or None."""
        st = getattr(shape, "shape_type", "")
        if st == "RotatingWall":
            return shape.pivot
        if st == "OscillatingWall":
            return getattr(shape, "center", None)
        return None

    def _near_pivot(self, world, pos, grab_r):
        """Return the first kinematic wall shape whose pivot is within grab_r, or None."""
        for s in world.shapes:
            if getattr(s, "shape_type", "") not in ("RotatingWall", "OscillatingWall"):
                continue
            pv = self._pivot_pos(s)
            if pv is None:
                continue
            dx = pos[0] - pv[0]
            dy = pos[1] - pv[1]
            if math.sqrt(dx*dx + dy*dy) <= grab_r:
                return s
        return None

    def on_mouse_click(self, world, pos, cam=None):
        zoom = cam.zoom if cam else 1.0
        # Adjust grab radius by zoom so it stays ~14px on screen regardless of zoom
        grab_r = PIVOT_GRAB_RADIUS / zoom

        # Check for pivot grab first
        ps = self._near_pivot(world, pos, grab_r)
        if ps is not None:
            self.pivot_shape = ps
            world.selected_shapes = [ps]
            self.target_shapes = []
            self.last_pos = pos
            return

        self.pivot_shape = None
        shape = world.select_at(pos, zoom=zoom)
        if shape:
            self.target_shapes = list(world.selected_shapes)
            self.last_pos = pos
        else:
            self.target_shapes = []
            self.last_pos = None

    def on_mouse_drag(self, world, pos, cam=None):
        if not self.last_pos:
            return
        dx = pos[0] - self.last_pos[0]
        dy = pos[1] - self.last_pos[1]

        # Pivot-only drag — move the rotation origin without moving the arm
        if self.pivot_shape is not None:
            s = self.pivot_shape
            st = getattr(s, "shape_type", "")
            if st == "RotatingWall":
                new_pivot = (s.pivot[0] + dx, s.pivot[1] + dy)
                s.pivot = new_pivot
                s.body.position = new_pivot
            elif st == "OscillatingWall":
                new_center = (s.center[0] + dx, s.center[1] + dy)
                s.center = new_center
                s.body.position = new_center
            world.space.reindex_shape(s)
            self.last_pos = pos
            return

        if not self.target_shapes:
            return

        processed_bodies = set()
        has_static = False

        for s in self.target_shapes:
            if isinstance(s, dict):
                s["pos"] += (dx, dy); continue
            if not s.body:
                continue
            btype = s.body.body_type
            if btype == 0:  # DYNAMIC
                if s.body not in processed_bodies:
                    s.body.position += (dx, dy)
                    processed_bodies.add(s.body)
                world.space.reindex_shape(s)
            elif btype == 1:  # KINEMATIC — move whole body + update stored pivot
                if s.body not in processed_bodies:
                    s.body.position += (dx, dy)
                    processed_bodies.add(s.body)
                    if getattr(s, "shape_type", "") == "RotatingWall":
                        s.pivot = (s.pivot[0]+dx, s.pivot[1]+dy)
                    elif getattr(s, "shape_type", "") == "OscillatingWall":
                        s.center = (s.center[0]+dx, s.center[1]+dy)
                world.space.reindex_shape(s)
            else:  # STATIC
                has_static = True
                if hasattr(s, "a") and hasattr(s, "b"):
                    s.unsafe_set_endpoints(s.a+(dx,dy), s.b+(dx,dy))
                if hasattr(s, "circle_center"):
                    s.circle_center = (s.circle_center[0]+dx, s.circle_center[1]+dy)
                if hasattr(s, "box_p1"):
                    s.box_p1 = (s.box_p1[0]+dx, s.box_p1[1]+dy)
                    s.box_p2 = (s.box_p2[0]+dx, s.box_p2[1]+dy)
                world.space.reindex_shape(s)

        if has_static:
            world.space.reindex_static()
        self.last_pos = pos

    def on_mouse_release(self, world, pos, cam=None):
        self.target_shapes = []
        self.last_pos = None
        self.pivot_shape = None

    def draw_preview(self, canvas, canvas_h, cam=None): pass
