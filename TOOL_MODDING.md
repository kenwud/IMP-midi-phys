# IMP — Tool Modding Guide

## Adding a new tool

1. Create a `.py` file in `/tools/`
2. Subclass `BaseTool`
3. Restart IMP — it auto-discovers and loads your tool

That's it. No changes to `main.py` or any other file needed.

---

## Minimal template

```python
from .base import BaseTool

class MyTool(BaseTool):
    name = "My Tool"   # display name (shown in tooltip)
    icon = "?"         # button label — any unicode char works

    # Tool-specific placement defaults (optional).
    # Global defaults (note, channel, elasticity, friction,
    # melody, trigger_midi) are always in self.defaults.
    placement_props = [
        {"key": "my_size", "label": "Size", "type": "float",
         "default": 20.0, "min": 1.0, "step": 1.0},
    ]

    def on_mouse_click(self, world, pos, cam=None):
        # pos is in world coordinates
        pass

    def on_mouse_drag(self, world, pos, cam=None):
        pass

    def on_mouse_release(self, world, pos, cam=None):
        pass

    # Optional: draw a ghost while placing
    def draw_preview(self, canvas, canvas_h, cam):
        pass

    # Optional: editable properties when object is selected
    @staticmethod
    def get_properties(obj):
        return []  # see below for format
```

---

## placement_props format

Each entry is a dict:

| key       | type          | required | description                        |
|-----------|---------------|----------|------------------------------------|
| `key`     | str           | ✓        | key in `self.defaults`             |
| `label`   | str           | ✓        | shown in UI                        |
| `type`    | str           | ✓        | `"float"`, `"int"`, `"bool"`, `"text"` |
| `default` | any           | ✓        | initial value                      |
| `min`     | float/int     |          | minimum value (float/int only)     |
| `max`     | float/int     |          | maximum value (float/int only)     |
| `step`    | float/int     |          | increment step (float/int only)    |

---

## get_properties format

Same as `placement_props` but each entry also needs:

| key     | type | description              |
|---------|------|--------------------------|
| `value` | any  | current value on the object |

Example:
```python
@staticmethod
def get_properties(obj):
    import pymunk
    if not isinstance(obj, pymunk.Circle): return []
    return [
        {"key": "ball_radius", "label": "Radius", "type": "float",
         "value": obj.radius, "min": 1.0, "step": 1.0},
    ]
```

---

## World API

```python
# Add objects (all return list of shapes)
world.add_ball(pos, radius=10, mass=1.0, friction=0.5,
               elasticity=0.8, note=60, channel=0, uid=None)

world.add_wall(p1, p2, friction=0.1, elasticity=0.8,
               note=60, channel=0, trigger_midi=True, uid=None)

world.add_hollow_circle(pos, radius, segments=32, ...)
world.add_hollow_box(p1, p2, ...)
world.add_rotating_wall(pivot, length, speed=90, ...)
world.add_oscillating_wall(center, length, sweep=90, speed=0.5, ...)

# Add non-shape objects (return dict)
world.add_attractor(pos, strength=20, falloff=2.0, uid=None)
world.add_emitter(pos, interval_ms=1000, angle=90, speed=200, ...)

# Selection
world.select_at(pos, radius=20.0, multi=False, zoom=1.0)
world.select_box(p1, p2)
world.selected_shapes   # list of selected shapes/dicts

# Deletion
world.delete_shapes(shapes_list)

# All objects
world.shapes    # list of all pymunk shapes
world.bodies    # list of all pymunk bodies
world.attractors
world.emitters
world.space     # pymunk.Space — full pymunk API available
```

## Camera API

```python
cam.w2s(world_pos, canvas_h)   # world → screen pixels
cam.s2w(screen_pos, canvas_h)  # screen → world
cam.zoom   # float, current zoom level
cam.pan    # [x, y] pan offset
```

## Keyboard shortcuts

| Key        | Action                     |
|------------|----------------------------|
| Space      | Play / Stop                |
| 1–9        | Select tool by number      |
| Arrows     | Nudge selected (×2px)      |
| Shift+Arr  | Nudge selected (×20px)     |
| Delete     | Delete selected            |
| Escape     | Deselect all               |
| F          | Toggle UI (performance mode)|
| Scroll     | Zoom in/out                |
| Middle btn | Pan                        |
