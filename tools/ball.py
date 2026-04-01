import dearpygui.dearpygui as dpg
from .base import BaseTool, BALL_SPAWN_PROPS

class BallTool(BaseTool):
    name = "Ball"
    icon = "circle"

    placement_props = BALL_SPAWN_PROPS  # radius + mass, defined once in base.py

    def on_mouse_click(self, world, pos, cam=None):
        shapes = world.add_ball(
            pos,
            radius=self.defaults.get("ball_radius", 10.0),
            mass=self.defaults.get("ball_mass", 1.0),
            friction=self.defaults["friction"],
            elasticity=self.defaults["elasticity"],
            note=self.get_note(),
            channel=self.defaults["channel"]
        )
        world.selected_shapes = shapes

    def on_mouse_drag(self, world, pos, cam=None): pass
    def on_mouse_release(self, world, pos, cam=None): pass

    @staticmethod
    def get_properties(obj):
        import pymunk
        if not isinstance(obj, pymunk.Circle): return []
        return [
            {"key": "ball_radius", "label": "Radius",     "type": "float",
             "value": obj.radius,      "min": 1.0,  "step": 1.0},
            {"key": "ball_mass",   "label": "Mass",       "type": "float",
             "value": obj.body.mass,   "min": 0.01, "step": 0.1},
            {"key": "friction",    "label": "Friction",   "type": "float",
             "value": obj.friction,    "min": 0.0,  "step": 0.05},
            {"key": "elasticity",  "label": "Elasticity", "type": "float",
             "value": obj.elasticity,  "min": 0.0,  "step": 0.05},
        ]
