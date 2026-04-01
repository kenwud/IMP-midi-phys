import pymunk
import math
import uuid
import time
import random
from event_bus import CollisionEvent, ProximityEvent
from scales import normalize_notes
from logger import get_logger

log = get_logger("PhysicsWorld")

class PhysicsWorld:
    def __init__(self, event_bus, gravity=(0, -900)):
        log.info(f"Initializing PhysicsWorld with Pymunk v{pymunk.version}")
        self.space = pymunk.Space()
        self.space.gravity = gravity
        self.space.damping = 1.0
        self.space.collision_slop = 0.0        # no penetration allowance
        self.space.collision_bias = 0.01       # aggressive overlap correction (default ~0.2)
        self.space.iterations = 20             # more solver iterations (default 10)
        self.space.idle_speed_threshold = 0.0  # disable sleep — never put bodies to sleep
        self.event_bus = event_bus
        self.bodies = []
        self.shapes = []
        self.selected_shapes = []
        self.attractors = []
        self.emitters = []
        
        # pymunk API varies by version - try both
        try:
            h = self.space.add_collision_handler(0, 0)
            h.begin = self._on_collision_begin
        except AttributeError:
            try:
                self.space.on_collision(0, 0, begin=self._on_collision_begin)
            except Exception as e:
                log.warning(f"Could not register collision handler: {e}")

    def _init_shape(self, shape, notes, channel, trigger_midi, is_ball, uid, shape_type):
        shape.notes = normalize_notes(notes)
        shape.note_index = 0
        shape.channel = channel
        # DEBUG (uncomment to trace placement):
        # log.debug(f"init {shape_type} notes={shape.notes} ch={channel}")
        shape.trigger_midi = trigger_midi
        shape.is_ball = is_ball
        shape.uid = uid
        shape.shape_type = shape_type
        shape.collision_type = 0
        shape.sensor = False 
        return shape

    def _on_collision_begin(self, arbiter, space, data):
        s1, s2 = arbiter.shapes
        # Capture impact velocity vector
        vel = arbiter.total_impulse
        self.event_bus.post(CollisionEvent(s1, s2, vel))
        return not (s1.sensor or s2.sensor)

    def set_gravity(self, x, y): self.space.gravity = (x, y)
    def set_damping(self, damping): self.space.damping = max(0.0, damping)

    def add_wall(self, p1, p2, friction=0.1, elasticity=0.8, notes=None, note=60, channel=0, trigger_midi=True, uid=None, shape_type="Wall"):
        if uid is None: uid = str(uuid.uuid4())
        body = self.space.static_body
        shape = pymunk.Segment(body, p1, p2, 5.0)
        shape.friction, shape.elasticity = friction, elasticity
        self._init_shape(shape, notes if notes is not None else note, channel, trigger_midi, False, uid, shape_type)
        self.space.add(shape); self.shapes.append(shape)
        return [shape]
    def add_ball(self, position, radius=10, mass=1, friction=0.5, elasticity=0.8, notes=None, note=60, channel=0, uid=None):
        # ALWAYS generate a new UUID if none is provided, or if we want to ensure isolation
        actual_uid = uid if uid is not None else str(uuid.uuid4())
        moment = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, moment)
        body.position = position
        def velocity_callback(body, gravity, damping, dt):
            pymunk.Body.update_velocity(body, gravity, damping, dt)
            l = body.velocity.length
            if l > 3000: body.velocity = body.velocity * (3000 / l)
        body.velocity_func = velocity_callback
        shape = pymunk.Circle(body, radius)
        shape.friction, shape.elasticity = friction, elasticity
        self._init_shape(shape, notes if notes is not None else note, channel, True, True, actual_uid, "Ball")
        # Store for property editing
        self.space.add(body, shape); self.bodies.append(body); self.shapes.append(shape)
        return [shape]

    def add_attractor(self, pos, strength=20, falloff=2.0, uid=None):
        if uid is None: uid = str(uuid.uuid4())
        attractor = {
            "uid": uid, "pos": pymunk.Vec2d(*pos), 
            "strength": strength, "falloff": falloff, 
            "shape_type": "Attractor",
            "visible": True, "trigger_midi": False, "threshold": 50.0,
            "notes": [60], "note_index": 0, "channel": 0,
            "in_radius": set() # For trigger logic
        }
        self.attractors.append(attractor)
        return attractor

    def add_rotating_wall(self, pivot, length, speed=90, start_angle=0, friction=0.1, elasticity=0.8, notes=None, note=60, channel=0, trigger_midi=True, uid=None):
        if uid is None: uid = str(uuid.uuid4())
        body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        body.position = pivot
        body.angle = math.radians(start_angle); body.angular_velocity = math.radians(speed)
        shape = pymunk.Segment(body, (0, 0), (length, 0), 5.0)
        shape.friction, shape.elasticity = friction, elasticity
        self._init_shape(shape, notes if notes is not None else note, channel, trigger_midi, False, uid, "RotatingWall")
        shape.pivot, shape.arm_length, shape.speed, shape.start_angle = pivot, length, speed, start_angle
        self.space.add(body, shape); self.bodies.append(body); self.shapes.append(shape)
        return [shape]

    def add_oscillating_wall(self, center, length, sweep=90, speed=0.5, rest_angle=0, friction=0.1, elasticity=0.8, notes=None, note=60, channel=0, trigger_midi=True, uid=None):
        if uid is None: uid = str(uuid.uuid4())
        body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        body.position = center
        body.angle = math.radians(rest_angle)
        shape = pymunk.Segment(body, (-length, 0), (length, 0), 5.0)
        shape.friction, shape.elasticity = friction, elasticity
        self._init_shape(shape, notes if notes is not None else note, channel, trigger_midi, False, uid, "OscillatingWall")
        shape.center, shape.arm_length, shape.sweep, shape.speed, shape.rest_angle = center, length, sweep, speed, rest_angle
        shape.phase = 0.0
        self.space.add(body, shape); self.bodies.append(body); self.shapes.append(shape)
        return [shape]

    def add_hollow_circle(self, position, radius, segments=32, friction=0.5, elasticity=0.8, note=60, channel=0, trigger_midi=True, uid=None):
        if uid is None: uid = str(uuid.uuid4())
        new_shapes = []
        for i in range(segments):
            angle1, angle2 = (i/segments)*math.pi*2, ((i+1)/segments)*math.pi*2
            p1, p2 = (position[0] + radius*math.cos(angle1), position[1] + radius*math.sin(angle1)), (position[0] + radius*math.cos(angle2), position[1] + radius*math.sin(angle2))
            s_list = self.add_wall(p1, p2, friction, elasticity, note, channel, trigger_midi, uid=uid, shape_type="HollowCircle")
            for s in s_list: s.circle_center, s.circle_radius = position, radius
            new_shapes.extend(s_list)
        return new_shapes

    def add_hollow_box(self, p1, p2, friction=0.5, elasticity=0.8, note=60, channel=0, trigger_midi=True, uid=None):
        if uid is None: uid = str(uuid.uuid4())
        xmin, xmax, ymin, ymax = min(p1[0], p2[0]), max(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[1], p2[1])
        edges = [((xmin, ymin), (xmax, ymin)), ((xmax, ymin), (xmax, ymax)), ((xmax, ymax), (xmin, ymax)), ((xmin, ymax), (xmin, ymin))]
        new_shapes = []
        for s, e in edges:
            s_list = self.add_wall(s, e, friction, elasticity, note, channel, trigger_midi, uid=uid, shape_type="HollowBox")
            for item in s_list: item.box_p1, item.box_p2 = (xmin, ymin), (xmax, ymax)
            new_shapes.extend(s_list)
        return new_shapes

    def delete_shapes(self, shapes_to_delete):
        uids_to_remove = set(getattr(s, "uid", None) for s in shapes_to_delete if getattr(s, "uid", None))
        for s in shapes_to_delete:
            if isinstance(s, dict): uids_to_remove.add(s["uid"])

        all_to_remove = [s for s in self.shapes if getattr(s, "uid", None) in uids_to_remove]
        for shape in all_to_remove:
            if shape in self.shapes: self.shapes.remove(shape)
            if shape in self.selected_shapes: self.selected_shapes.remove(shape)
            if shape.body and shape.body != self.space.static_body:
                if shape.body in self.space.bodies: self.space.remove(shape.body, shape)
                if shape.body in self.bodies: self.bodies.remove(shape.body)
            else:
                if shape in self.space.shapes: self.space.remove(shape)
        
        self.attractors = [a for a in self.attractors if a["uid"] not in uids_to_remove]
        self.emitters = [e for e in self.emitters if e["uid"] not in uids_to_remove]

    def delete_all_balls(self):
        balls = [s for s in self.shapes if getattr(s, "is_ball", False)]
        self.delete_shapes(balls)
        return len(balls)

    def cleanup_offscreen(self, bound=50000):
        """Remove balls that have wandered more than bound world units from origin."""
        offscreen_balls = [s for s in self.shapes
                           if getattr(s, "is_ball", False) and (
                               abs(s.body.position.x) > bound or
                               abs(s.body.position.y) > bound)]
        if offscreen_balls:
            self.delete_shapes(offscreen_balls)
            return len(offscreen_balls)
        return 0

    def add_emitter(self, pos, interval_ms=1000, angle=90, speed=200, spread=10, max_balls=10, notes=None, note=60, melody=None, elasticity=0.8, friction=0.5, ball_radius=10.0, ball_mass=1.0, uid=None):
        if uid is None: uid = str(uuid.uuid4())
        # Accept notes list, single note int, or legacy melody string — normalize immediately
        raw = notes if notes is not None else (melody if melody is not None else note)
        resolved = normalize_notes(raw)
        emitter = {
            "uid": uid, "pos": pymunk.Vec2d(*pos), "shape_type": "Emitter",
            "interval_ms": interval_ms, "angle": angle, "speed": speed, "spread": spread,
            "max_balls": max_balls,
            "notes": resolved, "note_index": 0,
            "elasticity": elasticity, "friction": friction,
            "ball_radius": ball_radius, "ball_mass": ball_mass,
            "last_spawn": 0, "spawned_uids": []
        }
        self.emitters.append(emitter)
        return emitter

    def step(self, dt):
        current_time_ms = time.time() * 1000
        for e in self.emitters:
            # Cleanup spawned_uids list (remove balls that no longer exist)
            existing_uids = set(getattr(s, "uid", None) for s in self.shapes if getattr(s, "is_ball", False))
            e["spawned_uids"] = [uid for uid in e["spawned_uids"] if uid in existing_uids]
            
            if len(e["spawned_uids"]) < e["max_balls"]:
                if current_time_ms - e["last_spawn"] >= e["interval_ms"]:
                    # Spawn!
                    angle_rad = math.radians(e["angle"] + random.uniform(-e["spread"], e["spread"]))
                    vel = pymunk.Vec2d(e["speed"], 0).rotated(angle_rad)
                    
                    notes = e.get("notes") or [60]
                    idx  = e.get("note_index", 0)
                    note = notes[idx % len(notes)]
                    e["note_index"] = (idx + 1) % len(notes)
                    
                    new_ball_uid = str(uuid.uuid4())
                    shapes = self.add_ball(e["pos"], radius=e.get("ball_radius", 10.0),
                                          mass=e.get("ball_mass", 1.0),
                                          friction=e["friction"], elasticity=e["elasticity"],
                                          note=note, uid=new_ball_uid)
                    for s in shapes:
                        s.body.velocity = vel
                        s.notes = notes
                    
                    e["spawned_uids"].append(new_ball_uid)
                    e["last_spawn"] = current_time_ms

        for shape in self.shapes:
            if shape.shape_type == "OscillatingWall":
                shape.phase += dt * shape.speed * 2 * math.pi
                target_angle = math.radians(shape.rest_angle) + math.radians(shape.sweep / 2) * math.sin(shape.phase)
                shape.body.angular_velocity = (target_angle - shape.body.angle) / dt
            elif shape.shape_type == "RotatingWall":
                shape.body.angular_velocity = math.radians(shape.speed)
        
        for a in self.attractors:
            current_in_radius = set()
            for body in self.bodies:
                if body.body_type == pymunk.Body.DYNAMIC:
                    delta = a["pos"] - body.position
                    dist_sq = delta.length_squared
                    dist = math.sqrt(dist_sq)
                    if dist_sq > 100:
                        # Include mass in force calculation
                        force_mag = a["strength"] * 100000 * body.mass / (dist_sq ** (a["falloff"]/2))
                        body.apply_force_at_world_point(delta.normalized() * force_mag, body.position)
                    
                    if a.get("trigger_midi", False):
                        # Find the shape associated with this body
                        ball_shape = next((s for s in self.shapes if s.body == body), None)
                        if ball_shape:
                            if dist < a["threshold"]:
                                current_in_radius.add(ball_shape.uid)
                                if ball_shape.uid not in a["in_radius"]:
                                    self.event_bus.post(ProximityEvent(a, body, ball_shape, dist))
            a["in_radius"] = current_in_radius
        self.space.step(dt)

    def select_at(self, pos, radius=20.0, multi=False, zoom=1.0):
        # Scale selection radius by zoom so it's always 'radius' pixels on screen
        world_radius = radius / zoom
        
        # 1. Attractors & Emitters First (Z-Order priority)
        for a in self.attractors + self.emitters:
            dist = (a["pos"] - pymunk.Vec2d(*pos)).length
            if dist < world_radius:
                if multi:
                    if a in self.selected_shapes: self.selected_shapes.remove(a)
                    else: self.selected_shapes.append(a)
                else: self.selected_shapes = [a]
                return [a]
        
        # 2. Shapes
        info = self.space.point_query_nearest(pos, world_radius, pymunk.ShapeFilter())
        if info and info.shape:
            uid = getattr(info.shape, "uid", None)
            
            # Grouping Logic: Only group if UID exists AND is NOT just a generic 'Wall' or 'Ball' 
            # (unless it's a multi-shape object like Hollow Box/Circle)
            # Actually, every object should have a UNIQUE UID unless it's a part of a compound object.
            if uid:
                group = [s for s in self.shapes if getattr(s, "uid", None) == uid]
            else:
                group = [info.shape]
                
            if multi:
                if group and group[0] in self.selected_shapes:
                    for s in group: 
                        if s in self.selected_shapes: self.selected_shapes.remove(s)
                else: 
                    # Add new group without duplicates
                    for s in group:
                        if s not in self.selected_shapes: self.selected_shapes.append(s)
            else: self.selected_shapes = group
            return group
        
        if not multi: self.selected_shapes = []
        return None

    def select_box(self, p1, p2):
        bb = pymunk.BB(min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1]))
        shapes_in_box = self.space.bb_query(bb, pymunk.ShapeFilter())
        uids = set(getattr(s, "uid", None) for s in shapes_in_box if getattr(s, "uid", None))
        
        new_selection = []
        # Add objects with UIDs
        if uids:
            new_selection.extend([s for s in self.shapes if getattr(s, "uid", None) in uids])
        
        # Add objects without UIDs that are inside the box
        new_selection.extend([s for s in shapes_in_box if not getattr(s, "uid", None)])
        
        self.selected_shapes = list(set(new_selection))
        for a in self.attractors + self.emitters:
            if bb.contains_vect(a["pos"]): self.selected_shapes.append(a)

    def get_draw_data(self):
        draw_data = []
        for shape in self.shapes:
            is_selected = (shape in self.selected_shapes)
            if isinstance(shape, pymunk.Segment):
                p1, p2 = shape.body.position + shape.a.rotated(shape.body.angle), shape.body.position + shape.b.rotated(shape.body.angle)
                entry = {"type": "segment", "p1": (p1.x, p1.y), "p2": (p2.x, p2.y), "selected": is_selected, "sensor": shape.sensor, "shape_type": getattr(shape, "shape_type", "Wall")}
                st = getattr(shape, "shape_type", "")
                if st == "RotatingWall":
                    entry["pivot"] = tuple(shape.body.position)
                elif st == "OscillatingWall":
                    entry["pivot"] = tuple(shape.body.position)
                draw_data.append(entry)
            elif isinstance(shape, pymunk.Circle):
                pos = shape.body.position + shape.offset.rotated(shape.body.angle)
                draw_data.append({"type": "circle", "pos": (pos.x, pos.y), "radius": shape.radius, "selected": is_selected, "sensor": shape.sensor})
            elif isinstance(shape, pymunk.Poly):
                verts = [(v.rotated(shape.body.angle) + shape.body.position) for v in shape.get_vertices()]
                draw_data.append({"type": "poly", "verts": [(v.x, v.y) for v in verts], "selected": is_selected, "sensor": shape.sensor})
        for a in self.attractors:
            is_selected = (a in self.selected_shapes)
            draw_data.append({"type": "attractor", "pos": (a["pos"].x, a["pos"].y), "selected": is_selected, "strength": a["strength"], "falloff": a.get("falloff", 2.0), "visible": a.get("visible", True)})
        for e in self.emitters:
            is_selected = (e in self.selected_shapes)
            draw_data.append({"type": "emitter", "pos": (e["pos"].x, e["pos"].y), "selected": is_selected, "angle": e["angle"]})
        return draw_data
