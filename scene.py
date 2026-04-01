import json
import os
from logger import get_logger

log = get_logger("Scene")

class SceneManager:
    def __init__(self, world):
        self.world = world

    def serialize(self, global_settings, placement_defaults, camera=None):
        scene_data = {
            "version": 2,
            "global": global_settings,
            "defaults": placement_defaults,
            "camera": {"pan": camera.pan, "zoom": camera.zoom} if camera else {"pan": [0,0], "zoom": 1.0},
            "objects": []
        }

        # Shapes
        processed_uids = set()
        for shape in self.world.shapes:
            uid = getattr(shape, "uid", None)
            if uid in processed_uids: continue
            processed_uids.add(uid)

            obj_data = {
                "type": shape.shape_type,
                "uid": uid,
                "friction": shape.friction,
                "elasticity": shape.elasticity,
                "notes": shape.notes,
                "channel": shape.channel,
                "trigger_midi": getattr(shape, "trigger_midi", True),
                "sensor": getattr(shape, "sensor", False)
            }

            if shape.shape_type == "Ball":
                obj_data["position"] = (shape.body.position.x, shape.body.position.y)
                obj_data["radius"] = shape.radius
                obj_data["mass"] = shape.body.mass
            elif shape.shape_type == "Wall":
                obj_data["p1"], obj_data["p2"] = (shape.a.x, shape.a.y), (shape.b.x, shape.b.y)
            elif shape.shape_type == "HollowCircle":
                obj_data["center"] = getattr(shape, "circle_center", (0,0))
                obj_data["radius"] = getattr(shape, "circle_radius", 50)
            elif shape.shape_type == "HollowBox":
                obj_data["p1"] = getattr(shape, "box_p1", (0,0))
                obj_data["p2"] = getattr(shape, "box_p2", (100,100))
            elif shape.shape_type == "RotatingWall":
                obj_data["pivot"], obj_data["arm_length"] = shape.pivot, shape.arm_length
                obj_data["speed"] = shape.speed
                obj_data["start_angle"] = getattr(shape, "start_angle", 0)
            elif shape.shape_type == "OscillatingWall":
                obj_data["center"], obj_data["arm_length"] = shape.center, shape.arm_length
                obj_data["sweep"], obj_data["speed"] = shape.sweep, shape.speed
                obj_data["rest_angle"] = shape.rest_angle

            scene_data["objects"].append(obj_data)

        # Attractors
        for a in self.world.attractors:
            scene_data["objects"].append({
                "type": "Attractor",
                "uid": a["uid"],
                "pos": (a["pos"].x, a["pos"].y),
                "strength": a["strength"],
                "falloff": a["falloff"],
                "visible": a.get("visible", True),
                "trigger_midi": a.get("trigger_midi", False),
                "threshold": a.get("threshold", 50.0),
                "notes": a.get("notes", [60]),
                "channel": a.get("channel", 0)
            })
        
        # Emitters
        for e in self.world.emitters:
            scene_data["objects"].append({
                "type": "Emitter",
                "uid": e["uid"],
                "pos": (e["pos"].x, e["pos"].y),
                "interval_ms": e["interval_ms"],
                "angle": e["angle"],
                "speed": e["speed"],
                "spread": e["spread"],
                "max_balls": e["max_balls"],
                "notes": e.get("notes", [60]),
                "elasticity": e.get("elasticity", 0.8),
                "friction": e.get("friction", 0.1)
            })

        return scene_data

    def save(self, filepath, global_settings, placement_defaults, camera=None):
        try:
            data = self.serialize(global_settings, placement_defaults, camera)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
            log.info(f"Scene saved to {filepath}")
            return True
        except Exception as e:
            log.error(f"Failed to save scene: {e}")
            return False

    def load(self, filepath):
        try:
            if not os.path.exists(filepath): return None
            with open(filepath, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            log.error(f"Failed to load scene: {e}")
            return None
