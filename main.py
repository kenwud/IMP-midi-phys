import dearpygui.dearpygui as dpg
import time, traceback, os, math, json
from icons import setup_fonts, bind_icon_font, ICONS
from logger import get_logger
from scales import midi_to_note_name, normalize_notes, parse_notes
from scene import SceneManager

log = get_logger("Main")

WIDTH  = 1280
HEIGHT = 800
FPS    = 60
DT     = 1.0 / FPS

TOPBAR_H      = 24   # font(13) + FramePadding*2(6) + WindowPadding*2(4) = 23, round up
TOOL_RAIL_W   = 52
TOOL_DEF_W    = 210
GLOBAL_W      = 210
RIGHT_PROP_W  = 260

SLOT_DIR  = "scenes/quicksave"
NUM_SLOTS = 5


class Camera:
    def __init__(self):
        self.pan  = [0.0, 0.0]
        self.zoom = 1.0
        self.ox   = TOOL_RAIL_W
        self.oy   = 0

    def w2s(self, world_pos, canvas_h, ox=None, oy=None):
        ox = ox if ox is not None else self.ox
        oy = oy if oy is not None else self.oy
        sx = (world_pos[0] + self.pan[0]) * self.zoom + ox
        sy = (canvas_h - oy) - ((world_pos[1] + self.pan[1]) * self.zoom) + oy
        return (sx, sy)

    def s2w(self, mouse_pos, canvas_h, ox=None, oy=None):
        ox = ox if ox is not None else self.ox
        oy = oy if oy is not None else self.oy
        cx = mouse_pos[0] - ox
        cy = (canvas_h - oy) - (mouse_pos[1] - oy)
        wx = (cx / self.zoom) - self.pan[0]
        wy = (cy / self.zoom) - self.pan[1]
        return (wx, wy)


def _prop_widget(prop, parent, callback, use_tag=False):
    t    = prop["type"]
    key  = prop["key"]
    val  = prop.get("value", prop.get("default", 0))
    kw   = dict(label=f"##{key}", default_value=val,
                callback=callback, user_data=key, parent=parent, width=-1)
    if use_tag:
        kw["tag"] = f"##{key}"
    if t == "float":
        if "min"  in prop: kw["min_value"]  = prop["min"]
        if "max"  in prop: kw["max_value"]  = prop["max"]
        if "step" in prop: kw["step"]       = prop["step"]
        dpg.add_text(prop["label"], parent=parent)
        dpg.add_input_float(**kw)
    elif t == "int":
        if "min"  in prop: kw["min_value"]  = prop["min"]
        if "max"  in prop: kw["max_value"]  = prop["max"]
        if "step" in prop: kw["step"]       = prop["step"]
        dpg.add_text(prop["label"], parent=parent)
        # Note name hint: shown for any int field whose key suggests a MIDI note
        is_note_field = any(tok in key for tok in ("note", "root", "midi"))
        note_label_tag = f"NoteHint_{key}_{parent}" if is_note_field else None
        if is_note_field and callback is not None:
            _tag = note_label_tag
            _ocb = callback
            def _cb_with_hint(sender, app_data, user_data, _t=_tag, _ocb=_ocb):
                if _ocb is not None:
                    _ocb(sender, app_data, user_data)
                try:
                    dpg.configure_item(_t, default_value=midi_to_note_name(int(app_data)))
                except Exception:
                    pass
            kw["callback"] = _cb_with_hint
        dpg.add_input_int(**kw)
        if is_note_field:
            dpg.add_text(midi_to_note_name(int(val)),
                         tag=note_label_tag, parent=parent,
                         color=(160, 220, 160))
    elif t == "bool":
        bool_kw = {k: v for k, v in kw.items()
                   if k not in ("label", "width", "step", "min_value", "max_value")}
        bool_kw["default_value"] = bool(val)
        dpg.add_checkbox(label=prop["label"], **bool_kw)
    elif t == "text":
        dpg.add_text(prop["label"], parent=parent)
        dpg.add_input_text(**kw)
    elif t == "combo":
        dpg.add_text(prop["label"], parent=parent)
        combo_kw = dict(label=f"##{key}", default_value=str(val),
                        items=prop.get("options", []),
                        callback=callback, user_data=key, parent=parent, width=-1)
        if use_tag:
            combo_kw["tag"] = f"##{key}"
        dpg.add_combo(**combo_kw)


class UIManager:
    def __init__(self):
        self.ui_visible = True
        self.tags = {
            "top": "TopBar",
            "tool_rail": "ToolRail",
            "tool_defaults": "ToolDefaultsPanel",
            "global": "GlobalPanel",
            "props": "PropsPanel",
        }

    def toggle_ui(self):
        self.ui_visible = not self.ui_visible
        for tag in self.tags.values():
            if dpg.does_item_exist(tag):
                dpg.configure_item(tag, show=self.ui_visible)

    def show_tool_defaults(self, show: bool):
        if dpg.does_item_exist(self.tags["tool_defaults"]):
            dpg.configure_item(self.tags["tool_defaults"], show=show and self.ui_visible)

    def show_props(self, show: bool):
        if dpg.does_item_exist(self.tags["props"]):
            dpg.configure_item(self.tags["props"], show=show and self.ui_visible)

    def layout_chrome(self, client_w, client_h):
        if not self.ui_visible:
            return
        # Measure actual rendered top bar height rather than relying on the constant
        if dpg.does_item_exist(self.tags["top"]):
            dpg.configure_item(self.tags["top"], width=client_w, height=TOPBAR_H, pos=(0, 0))
            actual_top_h = dpg.get_item_rect_size(self.tags["top"])[1]
        else:
            actual_top_h = TOPBAR_H
        if dpg.does_item_exist(self.tags["tool_rail"]):
            dpg.configure_item(self.tags["tool_rail"],
                               pos=(0, actual_top_h),
                               width=TOOL_RAIL_W,
                               height=client_h - actual_top_h)
        if dpg.does_item_exist(self.tags["tool_defaults"]):
            dpg.configure_item(self.tags["tool_defaults"],
                               pos=(TOOL_RAIL_W, actual_top_h),
                               width=TOOL_DEF_W,
                               height=client_h - actual_top_h)
        if dpg.does_item_exist(self.tags["global"]):
            dpg.configure_item(self.tags["global"],
                               pos=(TOOL_RAIL_W + TOOL_DEF_W, actual_top_h),
                               width=GLOBAL_W,
                               height=client_h - actual_top_h)
        if dpg.does_item_exist(self.tags["props"]):
            dpg.configure_item(self.tags["props"],
                               pos=(client_w - RIGHT_PROP_W, actual_top_h),
                               width=RIGHT_PROP_W,
                               height=client_h - actual_top_h)


def main():
    try:
        import pymunk
        from world import PhysicsWorld
        from transport import Transport
        from midi_output import MidiOutput
        from midi_engine import MidiEngine
        from event_bus import EventBus
    except ImportError as e:
        log.error(f"Missing dependency: {e.name}")
        return

    global_defaults = {
        "notes": "60",  # unified note/melody field (comma-separated)
        "channel": 0,
        "elasticity": 0.8,
        "friction": 0.1,
        "trigger_midi": True,
    }
    world_settings = {
        "gravity_y":   -900,
        "damping":      1.0,
        "substeps":     16,
        "time_scale":   1.0,
        "var_substeps": False,
        "var_sub_max":  64,
    }
    midi_settings  = {"dynamic_velocity": True, "sensitivity": 0.5, "fixed_velocity": 100}

    cam           = Camera()
    bus           = EventBus()
    midi_out      = MidiOutput()
    midi_engine   = MidiEngine(midi_out, bus)
    world         = PhysicsWorld(event_bus=bus, gravity=(0, world_settings["gravity_y"]))
    transport     = Transport(bus=bus, bpm=120)
    scene_manager = SceneManager(world)
    ui_manager    = UIManager()

    main.last_midi_time = 0
    frame_count   = 0
    last_mouse    = [None, None]
    is_drawing    = False

    os.makedirs(SLOT_DIR, exist_ok=True)

    # parse_notes_field removed — use parse_notes() from scales directly

    def notes_to_field(notes):
        return ",".join(str(int(max(0, min(127, n)))) for n in notes)

    def load_tools():
        import importlib.util, inspect
        from tools.base import BaseTool
        tools_dir = os.path.join(os.path.dirname(__file__), "tools")
        priority  = ["select.py", "move.py", "wall.py", "ball.py"]
        files     = sorted([f for f in os.listdir(tools_dir)
                            if f.endswith(".py") and f != "base.py" and not f.startswith("__")])
        for p in reversed(priority):
            if p in files:
                files.remove(p)
                files.insert(0, p)
        result = []
        for filename in files:
            try:
                mod_name = f"tools.{filename[:-3]}"
                spec     = importlib.util.spec_from_file_location(mod_name, os.path.join(tools_dir, filename))
                mod      = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                from tools.base import BaseTool
                for _, obj in inspect.getmembers(mod):
                    if (inspect.isclass(obj) and issubclass(obj, BaseTool)
                            and obj is not BaseTool):
                        tool_defaults = {**global_defaults}
                        for p in obj.placement_props:
                            if p["key"] not in tool_defaults:
                                tool_defaults[p["key"]] = p["default"]
                        result.append(obj(tool_defaults))
                        break
            except Exception as e:
                log.error(f"Failed to load tool {filename}: {e}")
        return result

    tools = load_tools()
    current_tool_idx = [0]

    def current_tool():
        idx = current_tool_idx[0]
        if idx is None or not isinstance(idx, int):
            idx = 0
        idx = max(0, min(idx, len(tools) - 1))
        return tools[idx]

    def set_status(msg, color=(180, 180, 180)):
        if dpg.does_item_exist("StatusText"):
            dpg.set_value("StatusText", msg)
            dpg.configure_item("StatusText", color=color)

    def toggle_play():
        if transport.playing:
            transport.stop()
        else:
            transport.play()
        set_status("Playing" if transport.playing else "Stopped")

    def quick_save(slot):
        if not isinstance(slot, int) or slot < 1:
            return
        path = os.path.join(SLOT_DIR, f"slot_{slot}.imp")
        if scene_manager.save(path, world_settings, global_defaults, camera=cam):
            set_status(f"Saved slot {slot}", (100, 255, 100))
            tag = f"LoadSlot{slot}"
            if dpg.does_item_exist(tag):
                dpg.configure_item(tag, enabled=True)

    def quick_load(slot):
        path = os.path.join(SLOT_DIR, f"slot_{slot}.imp")
        if not os.path.exists(path):
            set_status(f"Slot {slot} empty", (255, 200, 100))
            return
        data = scene_manager.load(path)
        if data and "objects" in data:
            rebuild_world_from_data(data)
            set_status(f"Loaded slot {slot}", (100, 200, 255))

    def build_properties_panel():
        if not dpg.does_item_exist("PropsGroup"):
            return
        dpg.delete_item("PropsGroup", children_only=True)
        sel = world.selected_shapes
        if not sel:
            ui_manager.show_props(False)
            return

        obj = sel[0]

        from tools.base import BaseTool
        props = []
        for tool in tools:
            p = tool.get_properties(obj)
            if p:
                props = p
                break

        # All runtime objects carry notes: list[int] — no fallback chains needed
        if isinstance(obj, dict):
            notes = obj.get("notes") or [60]
        else:
            notes = list(getattr(obj, "notes", [60])) or [60]

        field_value = notes_to_field(notes)

        with dpg.group(parent="PropsGroup"):
            dpg.add_text("Properties", color=(140, 140, 180))
            dpg.add_separator()
        with dpg.group(parent="PropsGroup"):
            dpg.add_text("Note / Melody", color=(200, 200, 255))
            with dpg.group(horizontal=True):
                dpg.add_input_text(label="##PropNotes",
                                   default_value=field_value,
                                   callback=on_prop_notes_field,
                                   user_data="notes",
                                   width=120)
                dpg.add_text(f"{notes[0]} ({midi_to_note_name(notes[0])})",
                             tag="PropNoteDisplay", color=(180, 180, 255))
            with dpg.group(horizontal=True):
                for step in [-12, -7, -5, -3, +3, +5, +7, +12]:
                    dpg.add_button(label=f"{step:+}",
                                   width=32,
                                   callback=transpose_notes,
                                   user_data=step)

        # channel
        chan = obj.get("channel", 0) if isinstance(obj, dict) else getattr(obj, "channel", 0)
        dpg.add_text("Channel (1-16):", parent="PropsGroup")
        dpg.add_input_int(label="##PropChan",
                          default_value=chan + 1,
                          callback=on_prop_change,
                          user_data="channel",
                          parent="PropsGroup",
                          width=-1,
                          min_value=1,
                          max_value=16)

        # filter out any tool-provided "note"/"melody" props to avoid duplicates
        filtered_props = [p for p in props if p["key"] not in ("note", "melody", "notes")]

        if filtered_props:
            dpg.add_separator(parent="PropsGroup")
            for prop in filtered_props:
                _prop_widget(prop, "PropsGroup", on_prop_change)

        dpg.add_spacer(height=6, parent="PropsGroup")
        dpg.add_button(label="DELETE  (Del)", callback=delete_selected,
                       width=-1, parent="PropsGroup")

        ui_manager.show_props(True)

    def on_prop_notes_field(sender, app_data, user_data):
        try:
            sel = world.selected_shapes
            if not sel:
                return
            notes = parse_notes(app_data)
            for obj in sel:
                if isinstance(obj, dict):
                    obj["notes"] = notes
                else:
                    obj.notes = notes
            if dpg.does_item_exist("PropNoteDisplay"):
                dpg.set_value("PropNoteDisplay",
                              f"{notes[0]} ({midi_to_note_name(notes[0])})")
        except:
            log.error(traceback.format_exc())

    def transpose_notes(sender, app_data, user_data):
        try:
            sel = world.selected_shapes
            if not sel:
                return
            step = int(user_data)

            # Each object transposes independently from its own current notes
            for o in sel:
                cur = o.get("notes", [60]) if isinstance(o, dict) else list(getattr(o, "notes", [60]))
                new_notes = [max(0, min(127, n + step)) for n in cur]
                if isinstance(o, dict):
                    o["notes"] = new_notes
                else:
                    o.notes = new_notes

            # Props panel shows first selected object's result
            first = sel[0]
            display_notes = first.get("notes", [60]) if isinstance(first, dict) else list(getattr(first, "notes", [60]))
            field_value = notes_to_field(display_notes)
            if dpg.does_item_exist("##PropNotes"):
                dpg.set_value("##PropNotes", field_value)
            if dpg.does_item_exist("PropNoteDisplay"):
                dpg.set_value("PropNoteDisplay",
                              f"{display_notes[0]} ({midi_to_note_name(display_notes[0])})")
        except:
            log.error(traceback.format_exc())

    def on_prop_change(sender, app_data, user_data):
        try:
            import pymunk
            sel = world.selected_shapes
            if not sel:
                return
            key = user_data
            val = app_data

            for obj in sel:
                if isinstance(obj, dict):
                    if key == "channel":
                        obj[key] = max(0, min(15, int(val) - 1))
                    else:
                        obj[key] = val
                else:
                    if key == "channel":
                        obj.channel = max(0, min(15, int(val) - 1))
                    elif key in ("friction", "elasticity"):
                        v = max(0.0, float(val))
                        setattr(obj, key, v)
                    elif key in ("trigger_midi", "sensor"):
                        setattr(obj, key, bool(val))
                    elif key == "ball_radius" and getattr(obj, "is_ball", False):
                        r = max(1.0, float(val))
                        obj.body.moment = pymunk.moment_for_circle(obj.body.mass, 0, r)
                        obj.unsafe_set_radius(r)
                        world.space.reindex_shape(obj)
                    elif key == "ball_mass" and getattr(obj, "is_ball", False):
                        m = max(0.01, float(val))
                        obj.body.moment = pymunk.moment_for_circle(m, 0, obj.radius)
                        obj.body.mass = m
                    elif key == "speed" and getattr(obj, "shape_type", "") == "RotatingWall":
                        obj.speed = float(val)
                        obj.body.angular_velocity = math.radians(obj.speed)
                    elif key in ("speed", "sweep", "rest_angle") and getattr(obj, "shape_type", "") == "OscillatingWall":
                        setattr(obj, key, float(val))
                    else:
                        setattr(obj, key, val)
        except:
            log.error(traceback.format_exc())

    def build_defaults_panel():
        if not dpg.does_item_exist("DefaultsGroup"):
            return
        dpg.delete_item("DefaultsGroup", children_only=True)
        tool = current_tool()
        dpg.add_text(f"[ {tool.name} defaults ]",
                     color=(180, 180, 255), parent="DefaultsGroup")
        dpg.add_separator(parent="DefaultsGroup")

        # unified notes default
        dpg.add_text("Note / Melody (comma-separated):", parent="DefaultsGroup")
        dpg.add_input_text(label="##DefNotes",
                           default_value=global_defaults["notes"],
                           callback=on_global_notes_default,
                           user_data="notes",
                           parent="DefaultsGroup",
                           width=-1)

        dpg.add_text("Channel (1-16):", parent="DefaultsGroup")
        dpg.add_input_int(label="##DefChan",
                          default_value=global_defaults["channel"] + 1,
                          callback=None,  # sync_defaults_from_widgets() reads ##DefChan before placement
                          parent="DefaultsGroup",
                          width=-1,
                          min_value=1,
                          max_value=16)

        dpg.add_text("Elasticity:", parent="DefaultsGroup")
        dpg.add_input_float(label="##DefElast",
                            default_value=global_defaults["elasticity"],
                            callback=on_global_default,
                            user_data="elasticity",
                            parent="DefaultsGroup",
                            width=-1,
                            step=0.05,
                            min_value=0.0)

        dpg.add_text("Friction:", parent="DefaultsGroup")
        dpg.add_input_float(label="##DefFrict",
                            default_value=global_defaults["friction"],
                            callback=on_global_default,
                            user_data="friction",
                            parent="DefaultsGroup",
                            width=-1,
                            step=0.05,
                            min_value=0.0)

        dpg.add_checkbox(label="Trigger MIDI",
                         tag="##DefTriggerMidi",
                         default_value=global_defaults["trigger_midi"],
                         callback=on_global_default,
                         user_data="trigger_midi",
                         parent="DefaultsGroup")

        if tool.placement_props:
            dpg.add_separator(parent="DefaultsGroup")
            for prop in tool.placement_props:
                if prop["key"] in ("note", "melody", "notes"):
                    continue
                p = dict(prop)
                p["value"] = tool.defaults.get(prop["key"], prop["default"])
                _prop_widget(p, "DefaultsGroup",
                             lambda s, a, u=prop["key"]: _update_tool_default(current_tool(), u, a),
                             use_tag=True)

    def sync_defaults_from_widgets():
        """
        Single bridge between UI and defaults dicts.
        Called before every placement — guarantees tools read consistent
        data from self.defaults regardless of DPG callback timing.

        Order is important:
          1. Read global widgets → write global_defaults
          2. Push global_defaults into ALL tool.defaults
          3. Read current tool's placement prop widgets → write current tool.defaults
             (tool-specific values applied last so they override globals if keys overlap)

        Tool placement prop widgets only exist for the active tool — DPG only holds
        widgets for the currently displayed panel — so we can only sync the active
        tool's placement props, which is correct behavior.
        """
        # --- Step 1 & 2: Global fields → global_defaults → all tool.defaults ---
        global_map = [
            ("##DefChan",        "channel",      lambda v: max(0, min(15, int(v) - 1))),
            ("##DefElast",       "elasticity",   lambda v: float(v)),
            ("##DefFrict",       "friction",     lambda v: float(v)),
            ("##DefTriggerMidi", "trigger_midi", lambda v: bool(v)),
        ]
        for tag, key, coerce in global_map:
            if dpg.does_item_exist(tag):
                try:
                    v = dpg.get_value(tag)
                    if v is not None:
                        global_defaults[key] = coerce(v)
                except Exception:
                    pass

        # Push all global_defaults into every tool — guarantees consistency
        # even for tools that haven't been the active tool this session
        for t in tools:
            t.defaults.update(global_defaults)

        # --- Step 3: Current tool's placement prop widgets ---
        # These widgets only exist for the active tool (DPG only renders active panel)
        tool = current_tool()
        for prop in tool.placement_props:
            key = prop["key"]
            if key in ("note", "melody", "notes"):
                continue
            tag = f"##{key}"
            if not dpg.does_item_exist(tag):
                continue
            try:
                v = dpg.get_value(tag)
                if v is not None:
                    tool.defaults[key] = v
                    # Keep note-hint text in sync
                    if prop["type"] == "int":
                        hint_tag = f"NoteHint_{key}_DefaultsGroup"
                        if dpg.does_item_exist(hint_tag):
                            dpg.configure_item(hint_tag,
                                               default_value=midi_to_note_name(int(v)))
            except Exception:
                pass

    def _update_tool_default(tool, key, val):
        if tool is None:
            return
        tool.defaults[key] = val

    def on_global_notes_default(sender, app_data, user_data):
        text = str(app_data)
        global_defaults["notes"] = text
        for t in tools:
            t.defaults["notes"] = text

    def on_global_default(sender, app_data, user_data):
        global_defaults[user_data] = app_data
        for t in tools:
            t.defaults[user_data] = app_data

    def switch_tool(idx):
        if idx is None:
            idx = 0
        idx = max(0, min(int(idx), len(tools) - 1))
        current_tool_idx[0] = idx
        for i, t in enumerate(tools):
            tag = f"ToolBtn{i}"
            active_tag = f"ToolBtnTheme{i}"
            if dpg.does_item_exist(tag):
                if i == idx:
                    if not dpg.does_item_exist(active_tag):
                        with dpg.theme(tag=active_tag):
                            with dpg.theme_component(dpg.mvButton):
                                dpg.add_theme_color(dpg.mvThemeCol_Button,        [80, 80, 180, 255])
                                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [100, 100, 210, 255])
                                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,  [60, 60, 150, 255])
                    dpg.bind_item_theme(tag, active_tag)
                else:
                    dpg.bind_item_theme(tag, 0)
        build_defaults_panel()
        ui_manager.show_tool_defaults(True)
        set_status(f"Tool: {tools[idx].name}")

    def delete_selected():
        if world.selected_shapes:
            world.delete_shapes(list(world.selected_shapes))
            world.selected_shapes = []
            build_properties_panel()

    def delete_all_balls():
        world.delete_all_balls()
        build_properties_panel()

    def purge_offscreen():
        n = world.cleanup_offscreen(bound=50000)
        if n:
            set_status(f"Purged {n} balls", (255, 200, 100))

    def reset_camera():
        cam.pan  = [0.0, 0.0]
        cam.zoom = 1.0
        set_status("Camera reset")

    def clear_scene():
        nonlocal world, scene_manager
        transport.stop()
        midi_engine.panic()
        world = PhysicsWorld(event_bus=bus, gravity=(0, world_settings["gravity_y"]))
        world.set_damping(world_settings["damping"])
        scene_manager.world = world
        world.selected_shapes = []
        build_properties_panel()
        set_status("Scene cleared", (255, 100, 100))

    def rebuild_world_from_data(data):
        nonlocal world, scene_manager
        transport.stop()
        midi_engine.panic()
        cd = data.get("camera", {})
        cam.pan  = cd.get("pan", [0, 0])
        cam.zoom = cd.get("zoom", 1.0)
        global_defaults.update(data.get("defaults", {}))
        world_settings.update(data.get("global", {}))
        world = PhysicsWorld(event_bus=bus, gravity=(0, world_settings["gravity_y"]))
        world.set_damping(world_settings["damping"])
        scene_manager.world = world
        for obj in data.get("objects", []):
            try:
                t   = obj["type"]
                uid = obj["uid"]
                # Normalize at load time — handles new (notes list), legacy (note int), legacy emitter (melody str)
                raw_notes = obj.get("notes") or obj.get("melody") or obj.get("note", 60)
                notes = normalize_notes(raw_notes)
                chan  = obj.get("channel", 0)
                f     = obj.get("friction", 0.1)
                e     = obj.get("elasticity", 0.8)
                tr    = obj.get("trigger_midi", True)
                sen   = obj.get("sensor", False)
                ns    = []
                if t == "Ball":
                    ns = world.add_ball(obj["position"], obj["radius"],
                                        mass=obj.get("mass", 1.0),
                                        friction=f, elasticity=e,
                                        notes=notes, channel=chan, uid=uid)
                elif t == "Wall":
                    ns = world.add_wall(obj["p1"], obj["p2"], friction=f, elasticity=e,
                                        notes=notes, channel=chan, trigger_midi=tr, uid=uid)
                elif t == "HollowCircle":
                    ns = world.add_hollow_circle(obj["center"], obj["radius"],
                                                 friction=f, elasticity=e,
                                                 notes=notes, channel=chan, trigger_midi=tr, uid=uid)
                elif t == "HollowBox":
                    ns = world.add_hollow_box(obj["p1"], obj["p2"], friction=f, elasticity=e,
                                              notes=notes, channel=chan, trigger_midi=tr, uid=uid)
                elif t == "RotatingWall":
                    ns = world.add_rotating_wall(obj["pivot"], obj["arm_length"],
                                                 speed=obj.get("speed", 90),
                                                 friction=f, elasticity=e,
                                                 notes=notes, channel=chan, trigger_midi=tr, uid=uid)
                elif t == "OscillatingWall":
                    ns = world.add_oscillating_wall(obj["center"], obj["arm_length"],
                                                    sweep=obj.get("sweep", 90),
                                                    speed=obj.get("speed", 0.5),
                                                    rest_angle=obj.get("rest_angle", 0),
                                                    friction=f, elasticity=e,
                                                    notes=notes, channel=chan, trigger_midi=tr, uid=uid)
                elif t == "Attractor":
                    a = world.add_attractor(obj["pos"], strength=obj.get("strength", 20),
                                            falloff=obj.get("falloff", 2.0), uid=uid)
                    a.update({k: obj.get(k, v) for k, v in
                              [("visible", True), ("trigger_midi", False),
                               ("threshold", 50.0), ("channel", 0)]})
                    a["notes"] = notes  # already normalized above
                elif t == "Emitter":
                    world.add_emitter(obj["pos"],
                                      interval_ms=obj.get("interval_ms", 1000),
                                      angle=obj.get("angle", 90),
                                      speed=obj.get("speed", 200),
                                      spread=obj.get("spread", 10),
                                      max_balls=obj.get("max_balls", 10),
                                      notes=notes,
                                      friction=f, elasticity=e, uid=uid)
                for s in ns:
                    s.notes = notes
                    s.trigger_midi = tr
                    s.sensor = sen
            except:
                log.error(traceback.format_exc())
        world.selected_shapes = []
        build_properties_panel()
        set_status("Scene loaded", (100, 255, 100))

    def on_save_dialog(sender, app_data):
        fp = app_data["file_path_name"]
        if not fp.endswith(".imp"):
            fp += ".imp"
        if scene_manager.save(fp, world_settings, global_defaults, camera=cam):
            set_status(f"Saved: {os.path.basename(fp)}", (100, 255, 100))

    def on_load_dialog(sender, app_data):
        data = scene_manager.load(app_data["file_path_name"])
        if data and "objects" in data:
            rebuild_world_from_data(data)
        else:
            set_status("Load failed", (255, 100, 100))

    def nudge_selected(dx, dy):
        mult = 20.0 if (dpg.is_key_down(dpg.mvKey_LShift) or dpg.is_key_down(dpg.mvKey_RShift)) else 2.0
        dx *= mult
        dy *= mult
        processed = set()
        has_static = False
        for s in list(world.selected_shapes):
            if isinstance(s, dict):
                s["pos"] += (dx, dy)
                continue
            if not s.body:
                continue
            btype = s.body.body_type
            if btype == 0:  # DYNAMIC
                if s.body not in processed:
                    s.body.position += (dx, dy)
                    processed.add(s.body)
                world.space.reindex_shape(s)
            elif btype == 1:  # KINEMATIC — arrow keys move body only, pivot stays
                if s.body not in processed:
                    s.body.position += (dx, dy)
                    processed.add(s.body)
                world.space.reindex_shape(s)
            else:  # STATIC
                has_static = True
                if hasattr(s, "a") and hasattr(s, "b"):
                    s.unsafe_set_endpoints(s.a + (dx, dy), s.b + (dx, dy))
                if hasattr(s, "circle_center"):
                    s.circle_center = (s.circle_center[0] + dx, s.circle_center[1] + dy)
                if hasattr(s, "box_p1"):
                    s.box_p1 = (s.box_p1[0] + dx, s.box_p1[1] + dy)
                    s.box_p2 = (s.box_p2[0] + dx, s.box_p2[1] + dy)
                world.space.reindex_shape(s)
        if has_static:
            world.space.reindex_static()

    def on_key_press(sender, app_data):
        k = app_data
        if   k == dpg.mvKey_Up:       nudge_selected(0, 1)
        elif k == dpg.mvKey_Down:     nudge_selected(0, -1)
        elif k == dpg.mvKey_Left:     nudge_selected(-1, 0)
        elif k == dpg.mvKey_Right:    nudge_selected(1, 0)
        elif k == dpg.mvKey_Delete:   delete_selected()
        elif k == dpg.mvKey_Spacebar: toggle_play()
        elif k == dpg.mvKey_Escape:
            world.selected_shapes = []
            build_properties_panel()
        elif k == dpg.mvKey_F:
            ui_manager.toggle_ui()

    def on_mouse_wheel(sender, app_data):
        canvas_h = dpg.get_item_height("Canvas")
        mx, my   = dpg.get_mouse_pos(local=True)
        crm      = dpg.get_item_rect_min("Canvas")
        cox, coy = crm[0], crm[1]
        if mx < cox:
            return
        wx, wy   = cam.s2w((mx, my), canvas_h, cox, coy)
        factor   = 1.1 if app_data > 0 else 0.9
        cam.zoom = max(0.01, min(50.0, cam.zoom * factor))
        cam.pan[0] = (mx - cox) / cam.zoom - wx
        cam.pan[1] = (canvas_h - coy - (my - coy)) / cam.zoom - wy

    dpg.create_context()
    _icons_loaded = setup_fonts(dpg)

    # --- Global compact theme (Blender-style tight layout) ---
    # Applied to mvAll so every window inherits it unless overridden.
    with dpg.theme(tag="GlobalCompactTheme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding,  4, 4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,   3, 2)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,    4, 3)
            dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 4, 3)
    dpg.bind_theme("GlobalCompactTheme")

    # TopBar: ultra-tight — buttons are 28px tall, no spare vertical space
    with dpg.theme(tag="TopBarTheme"):
        with dpg.theme_component(dpg.mvWindowAppItem):
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 2, 2)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,  3, 3)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,   3, 0)

    # Sidebar panels: small padding, content fills width
    with dpg.theme(tag="PanelTheme"):
        with dpg.theme_component(dpg.mvWindowAppItem):
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 6, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,  3, 2)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,   4, 4)

    # PrimaryWindow / Canvas: zero padding so drawlist fills edge-to-edge
    with dpg.theme(tag="PrimaryWindowTheme"):
        with dpg.theme_component(dpg.mvWindowAppItem):
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 0, 0)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,   0, 0)

    with dpg.window(tag="TopBar", no_title_bar=True, no_scrollbar=True,
                    no_scroll_with_mouse=True,
                    no_move=True, no_close=True, no_resize=True,
                    pos=(0, 0), width=WIDTH, height=TOPBAR_H):
        with dpg.group(horizontal=True):
            dpg.add_button(label=ICONS.get("play", ">"), tag="BtnPlay", width=32, callback=transport.play)
            bind_icon_font(dpg, "BtnPlay")
            dpg.add_button(label=ICONS.get("stop", "[]"), tag="BtnStop", width=32, callback=transport.stop)
            bind_icon_font(dpg, "BtnStop")
            dpg.add_input_text(tag="MidiLight", default_value="---",
                               width=148, readonly=True,
                               hint="", label="##MidiLight")
            dpg.add_separator()
            ports = midi_out.get_ports()
            dpg.add_combo(items=ports, label="##Port", width=140,
                          callback=lambda s, a: [midi_out.open_port(i)
                                                 for i, n in enumerate(midi_out.get_ports()) if n == a])
            dpg.add_separator()
            for i in range(1, NUM_SLOTS + 1):
                dpg.add_button(label=f"S{i}", width=24,
                               callback=lambda s, a, u=i: quick_save(u))
            dpg.add_separator()
            for i in range(1, NUM_SLOTS + 1):
                slot_exists = os.path.exists(os.path.join(SLOT_DIR, f"slot_{i}.imp"))
                dpg.add_button(label=f"L{i}", width=24, tag=f"LoadSlot{i}",
                               callback=lambda s, a, u=i: quick_load(u),
                               enabled=slot_exists)
            dpg.add_separator()
            dpg.add_button(label="SAVE", width=44,
                           callback=lambda: dpg.show_item("SaveDialog"))
            dpg.add_button(label="LOAD", width=44,
                           callback=lambda: dpg.show_item("LoadDialog"))
            dpg.add_separator()
            dpg.add_button(label="CLR BALLS", width=70, callback=delete_all_balls)
            dpg.add_button(label="PURGE", width=52, callback=purge_offscreen)
            dpg.add_button(label="CLEAR", width=60, callback=clear_scene)
            dpg.add_button(label="HOME", width=48, callback=reset_camera)
            dpg.add_separator()
            dpg.add_text("Balls: 0", tag="BallCount", color=(150, 150, 150))
            dpg.add_separator()
            dpg.add_text("", tag="StatusText", color=(180, 180, 180))

    def _on_tool_btn(sender, app_data, user_data):
        switch_tool(user_data)

    with dpg.window(tag="ToolRail", no_title_bar=True, no_scrollbar=True,
                    no_move=True, no_close=True, no_resize=True,
                    pos=(0, TOPBAR_H), width=TOOL_RAIL_W, height=HEIGHT - TOPBAR_H):
        for i, tool in enumerate(tools):
            btn_label = ICONS.get(tool.icon, tool.icon)
            dpg.add_button(label=btn_label, tag=f"ToolBtn{i}",
                           width=TOOL_RAIL_W - 8, height=32,
                           callback=_on_tool_btn, user_data=i)
            bind_icon_font(dpg, f"ToolBtn{i}")

    with dpg.window(tag="ToolDefaultsPanel", no_title_bar=True, no_scrollbar=True,
                    no_move=True, no_close=True, no_resize=True,
                    pos=(TOOL_RAIL_W, TOPBAR_H), width=TOOL_DEF_W, height=HEIGHT - TOPBAR_H,
                    show=True):
        dpg.add_group(tag="DefaultsGroup")

    with dpg.window(tag="GlobalPanel", no_title_bar=True,
                    no_move=True, no_close=True, no_resize=True,
                    pos=(TOOL_RAIL_W + TOOL_DEF_W, TOPBAR_H),
                    width=GLOBAL_W, height=HEIGHT - TOPBAR_H, no_scrollbar=True):
        dpg.add_text("World / MIDI", color=(140, 140, 180))
        dpg.add_separator()
        dpg.add_text("Physics", color=(160, 160, 220))
        dpg.add_separator()
        dpg.add_text("Gravity Y:")
        dpg.add_input_float(label="##GravY", default_value=world_settings["gravity_y"],
                            callback=lambda s, a: (world.set_gravity(0, a),
                                                   world_settings.update({"gravity_y": a})),
                            tag="WorldGravY", width=-1, step=100)
        dpg.add_text("Damping:")
        dpg.add_input_float(label="##Damping", default_value=world_settings["damping"],
                            callback=lambda s, a: (world.set_damping(a),
                                                   world_settings.update({"damping": a})),
                            tag="WorldDamping", width=-1, step=0.01)
        dpg.add_text("Substeps:")
        dpg.add_input_int(label="##Substeps", default_value=world_settings["substeps"],
                          callback=lambda s, a: world_settings.update({"substeps": max(1, a)}),
                          tag="WorldSubsteps", width=-1, min_value=1)
        dpg.add_text("Time Scale:")
        dpg.add_slider_float(label="##TimeScale", default_value=world_settings["time_scale"],
                             min_value=0.05, max_value=4.0,
                             callback=lambda s, a: world_settings.update({"time_scale": a}),
                             tag="WorldTimeScale", width=-1)
        dpg.add_checkbox(label="Variable Substeps",
                         default_value=world_settings["var_substeps"],
                         callback=lambda s, a: world_settings.update({"var_substeps": a}),
                         tag="VarSubsteps")
        dpg.add_text("Max Substeps:")
        dpg.add_input_int(label="##VarSubMax", default_value=world_settings["var_sub_max"],
                          callback=lambda s, a: world_settings.update({"var_sub_max": max(world_settings["substeps"], a)}),
                          tag="VarSubMax", width=-1, min_value=1)
        dpg.add_spacer(height=8)
        dpg.add_text("MIDI Velocity", color=(200, 200, 255))
        dpg.add_separator()
        dpg.add_checkbox(label="Dynamic Velocity", default_value=midi_settings["dynamic_velocity"],
                         callback=lambda s, a: setattr(midi_engine, "dynamic_velocity", a),
                         tag="DynVelToggle")
        dpg.add_text("Velocity Sens:")
        dpg.add_slider_float(label="##VelSens", default_value=midi_settings["sensitivity"],
                             min_value=0.0, max_value=1.0,
                             callback=lambda s, a: setattr(midi_engine, "velocity_sensitivity", a),
                             tag="VelSens", width=-1)
        dpg.add_text("Base Velocity:")
        dpg.add_input_int(label="##FixedVel", default_value=midi_settings["fixed_velocity"],
                          callback=lambda s, a: setattr(midi_engine, "fixed_velocity", a),
                          tag="FixedVel", width=-1)
        dpg.add_spacer(height=8)
        dpg.add_text("Note Sustain", color=(200, 200, 255))
        dpg.add_separator()
        dpg.add_text("Duration (ms):")
        dpg.add_slider_int(label="##SustainMs", default_value=80,
                           min_value=10, max_value=2000,
                           callback=lambda s, a: setattr(midi_engine, "sustain_ms", a),
                           tag="SustainMs", width=-1)
        dpg.add_combo(["fixed", "velocity"], label="##SustainMode", default_value="fixed",
                      callback=lambda s, a: setattr(midi_engine, "sustain_mode", a),
                      tag="SustainMode", width=-1)
        dpg.add_spacer(height=8)
        dpg.add_text("Collision MIDI", color=(200, 200, 255))
        dpg.add_separator()
        dpg.add_checkbox(label="Ball-Ball MIDI",
                         default_value=False,
                         callback=lambda s, a: setattr(midi_engine, "ball_ball_midi", a),
                         tag="BallBallMidi")

    with dpg.window(tag="PropsPanel", no_title_bar=True,
                    no_move=True, no_close=True, no_resize=True,
                    pos=(WIDTH - RIGHT_PROP_W, TOPBAR_H),
                    width=RIGHT_PROP_W, height=HEIGHT - TOPBAR_H,
                    show=False, no_scrollbar=False):
        dpg.add_group(tag="PropsGroup")

    with dpg.window(tag="PrimaryWindow", no_title_bar=True, no_scrollbar=True):
        dpg.add_drawlist(tag="Canvas", width=WIDTH, height=HEIGHT)

    dpg.bind_item_theme("PrimaryWindow", "PrimaryWindowTheme")
    dpg.bind_item_theme("TopBar",            "TopBarTheme")
    dpg.bind_item_theme("ToolRail",          "PanelTheme")
    dpg.bind_item_theme("ToolDefaultsPanel", "PanelTheme")
    dpg.bind_item_theme("GlobalPanel",       "PanelTheme")
    dpg.bind_item_theme("PropsPanel",        "PanelTheme")

    with dpg.file_dialog(directory_selector=False, show=False,
                         callback=on_save_dialog, tag="SaveDialog",
                         width=600, height=400, default_path="scenes"):
        dpg.add_file_extension(".imp", color=(100, 255, 100, 255))
    with dpg.file_dialog(directory_selector=False, show=False,
                         callback=on_load_dialog, tag="LoadDialog",
                         width=600, height=400, default_path="scenes"):
        dpg.add_file_extension(".imp", color=(100, 255, 100, 255))

    with dpg.handler_registry():
        dpg.add_key_press_handler(callback=on_key_press)
        dpg.add_mouse_wheel_handler(callback=on_mouse_wheel)

    dpg.create_viewport(title="IMP - Interactive MIDI Physics v3",
                        width=WIDTH, height=HEIGHT)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("PrimaryWindow", True)
    from icons import _font_tag as _ft
    if _ft:
        try:
            dpg.bind_font(_ft)
        except:
            pass

    bus.subscribe(lambda e: setattr(main, "last_midi_time", time.time()))

    switch_tool(0)
    build_defaults_panel()

    while dpg.is_dearpygui_running():
        current_time = time.time()
        frame_count += 1

        client_w = dpg.get_viewport_client_width()
        client_h = dpg.get_viewport_client_height()
        dpg.set_item_width("Canvas",  client_w)
        dpg.set_item_height("Canvas", client_h)
        canvas_h = dpg.get_item_height("Canvas")
        _crm = dpg.get_item_rect_min("Canvas")
        canvas_ox = _crm[0]
        canvas_oy = _crm[1]
        cam.ox = canvas_ox
        cam.oy = canvas_oy

        ui_manager.layout_chrome(client_w, client_h)

        if frame_count % 30 == 0:
            ball_count = sum(1 for s in world.shapes if getattr(s, "is_ball", False))
            if dpg.does_item_exist("BallCount"):
                dpg.set_value("BallCount", f"Balls: {ball_count}")

        if frame_count % 300 == 0:  # auto-purge offscreen balls every ~5 seconds
            world.cleanup_offscreen(bound=50000)

        if current_time - getattr(main, "last_midi_time", 0) < 0.1:
            if dpg.does_item_exist("MidiLight"):
                dpg.set_value("MidiLight", midi_engine.last_event_info)
        else:
            if dpg.does_item_exist("MidiLight"):
                dpg.set_value("MidiLight", "---")

        mx, my = dpg.get_mouse_pos(local=True)
        if mx < -9999 or my < -9999:
            # Window lost focus — invalidate last position so the next
            # middle-click doesn't produce a massive bogus delta.
            last_mouse[0] = None
            last_mouse[1] = None
            mx, my = 0, 0

        if dpg.is_mouse_button_down(dpg.mvMouseButton_Middle):
            if last_mouse[0] is not None and last_mouse[1] is not None:
                dx = mx - last_mouse[0]
                dy = my - last_mouse[1]
                # Ignore implausibly large deltas (e.g. first frame after refocus)
                if abs(dx) < 200 and abs(dy) < 200:
                    cam.pan[0] += dx / cam.zoom
                    cam.pan[1] -= dy / cam.zoom
        last_mouse[0] = mx
        last_mouse[1] = my

        w_pos = cam.s2w((mx, my), canvas_h, canvas_ox, canvas_oy)

        left_limit  = TOOL_RAIL_W + TOOL_DEF_W + GLOBAL_W
        right_limit = client_w - (RIGHT_PROP_W if ui_manager.ui_visible else 0)

        if dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
            if mx > left_limit and mx < right_limit and my > TOPBAR_H:
                if not is_drawing:
                    try:
                        sync_defaults_from_widgets()
                        current_tool().on_mouse_click(world, w_pos, cam=cam)
                        is_drawing = True
                    except:
                        log.error(traceback.format_exc())
                else:
                    try:
                        current_tool().on_mouse_drag(world, w_pos, cam=cam)
                    except:
                        log.error(traceback.format_exc())
        else:
            if is_drawing:
                try:
                    current_tool().on_mouse_release(world, w_pos, cam=cam)
                except:
                    log.error(traceback.format_exc())
                is_drawing = False
                build_properties_panel()

        if transport.playing:
            ss  = world_settings["substeps"]
            ts  = world_settings.get("time_scale", 1.0)
            if world_settings.get("var_substeps", False):
                # Scale substeps to fastest ball: ball shouldn't move more than
                # its own radius in one substep. floor at manual substeps setting.
                balls = [s for s in world.shapes if getattr(s, "is_ball", False)]
                if balls:
                    max_speed  = max((s.body.velocity.length for s in balls), default=0)
                    min_radius = min((s.radius for s in balls), default=10)
                    import math as _math
                    needed = max(ss, min(world_settings["var_sub_max"],
                                        _math.ceil(max_speed * DT * ts / max(min_radius, 1))))
                    ss = needed
            step_dt = DT * ts / ss
            for _ in range(ss):
                world.step(step_dt)
        midi_engine.tick()

        dpg.delete_item("Canvas", children_only=True)
        dpg.draw_rectangle((0, 0), (client_w, canvas_h),
                           color=(15, 15, 20), fill=(15, 15, 20), parent="Canvas")

        for item in world.get_draw_data():
            sel_color = (100, 255, 100)
            color = sel_color if item["selected"] else (200, 200, 200)
            alpha = 100 if item.get("sensor") else 255
            ca    = (*color, alpha)

            if item["type"] == "segment":
                p1 = cam.w2s(item["p1"], canvas_h, canvas_ox, canvas_oy)
                p2 = cam.w2s(item["p2"], canvas_h, canvas_ox, canvas_oy)
                dpg.draw_line(p1, p2, color=ca,
                              thickness=max(1, int(4 * cam.zoom)), parent="Canvas")
                # Draw pivot point for kinematic walls
                if "pivot" in item:
                    pv = cam.w2s(item["pivot"], canvas_h, canvas_ox, canvas_oy)
                    st = item.get("shape_type", "")
                    pcol = (255, 100, 255, 220) if st == "RotatingWall" else (100, 200, 255, 220)
                    pfill = (255, 100, 255, 80) if st == "RotatingWall" else (100, 200, 255, 80)
                    pr = max(4, int(7 * cam.zoom))
                    dpg.draw_circle(pv, pr, color=pcol, fill=pfill, parent="Canvas")
                    # crosshair inside pivot circle
                    dpg.draw_line((pv[0]-pr+2, pv[1]), (pv[0]+pr-2, pv[1]), color=pcol, thickness=1, parent="Canvas")
                    dpg.draw_line((pv[0], pv[1]-pr+2), (pv[0], pv[1]+pr-2), color=pcol, thickness=1, parent="Canvas")

            elif item["type"] == "circle":
                pos = cam.w2s(item["pos"], canvas_h, canvas_ox, canvas_oy)
                r   = max(1, int(item["radius"] * cam.zoom))
                fill = (100, 100, 150, 150 if not item.get("sensor") else 50)
                dpg.draw_circle(pos, r, color=ca, fill=fill, parent="Canvas")

            elif item["type"] == "poly":
                verts = [cam.w2s(v, canvas_h, canvas_ox, canvas_oy) for v in item["verts"]]
                dpg.draw_polyline(verts, color=ca,
                                  thickness=max(1, int(4 * cam.zoom)),
                                  parent="Canvas", closed=True)

            elif item["type"] == "attractor":
                if not item.get("visible", True) and not item["selected"]:
                    continue
                pos    = cam.w2s(item["pos"], canvas_h, canvas_ox, canvas_oy)
                pulse  = (10 + 5 * math.sin(current_time * 10)) * cam.zoom
                dpg.draw_circle(pos, pulse,
                                color=(255, 200, 100, 200), fill=(255, 200, 100, 100), parent="Canvas")
                strength = item.get("strength", 20)
                falloff  = item.get("falloff", 2.0)
                for i in range(1, 6):
                    r     = i * 80
                    alpha = int(255 * (strength / 50.0) / (i ** (falloff / 2.0)))
                    alpha = max(10, min(150, alpha))
                    dpg.draw_circle(pos, r * cam.zoom,
                                    color=(255, 200, 100, alpha), thickness=1, parent="Canvas")

            elif item["type"] == "emitter":
                pos   = cam.w2s(item["pos"], canvas_h, canvas_ox, canvas_oy)
                ecol  = (100, 255, 100) if item["selected"] else (255, 150, 50)
                r     = 10 * cam.zoom
                verts = [(pos[0], pos[1] - r), (pos[0] + r, pos[1]),
                         (pos[0], pos[1] + r), (pos[0] - r, pos[1])]
                dpg.draw_polyline(verts, color=ecol, thickness=2,
                                  parent="Canvas", closed=True)
                angle = math.radians(item["angle"])
                ex    = pos[0] + 30 * math.cos(angle) * cam.zoom
                ey    = pos[1] - 30 * math.sin(angle) * cam.zoom
                dpg.draw_line(pos, (ex, ey), color=ecol, thickness=2, parent="Canvas")

        try:
            current_tool().draw_preview("Canvas", canvas_h, cam)
        except:
            pass

        if dpg.does_item_exist("Canvas"):
            ox, oy = cam.w2s((0, 0), canvas_h, canvas_ox, canvas_oy)
            dpg.draw_line((ox - 10, oy), (ox + 10, oy),
                          color=(255, 50, 50, 180), thickness=1, parent="Canvas")
            dpg.draw_line((ox, oy - 10), (ox, oy + 10),
                          color=(255, 50, 50, 180), thickness=1, parent="Canvas")

        dpg.render_dearpygui_frame()
        elapsed = time.time() - current_time
        if elapsed < DT:
            time.sleep(DT - elapsed)

    midi_out.close()
    dpg.destroy_context()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.critical(f"FATAL: {e}")
        traceback.print_exc()
    input("\nEnter to exit...")