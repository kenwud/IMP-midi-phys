"""
IMP Icon System
===============
Loads Font Awesome solid icons for use in DPG buttons.

Setup:
    1. Put 'fa-free-solid-900.otf' (or similar) in a fonts/ subfolder
    2. Optionally put FA's icons.json in fonts/ for auto codepoint lookup
    3. Call setup_fonts() before creating any DPG windows
    4. Use ICONS["name"] to get the character for a button label

Font file search order (first found wins):
    fonts/Font Awesome 7 Free-Solid-900.otf
    fonts/Font Awesome 6 Free-Solid-900.otf
    fonts/fa-solid-900.otf
    fonts/FontAwesome.otf
"""

import os
import json

# ── Known codepoints (FA 5/6/7 solid — stable across versions) ────────
_KNOWN = {
    # UI / tools
    "arrow-pointer":       0xF245,   # select cursor
    "up-down-left-right":  0xF0B2,   # move
    "minus":               0xF068,   # wall (horizontal line)
    "circle":              0xF111,   # ball / hollow circle
    "square":              0xF0C8,   # box
    "rotate":              0xF2F1,   # rotating wall
    "water":               0xF773,   # oscillating wall (wave-ish)
    "asterisk":            0xF069,   # array
    "magnet":              0xF076,   # attractor
    "circle-dot":          0xF192,   # emitter
    "trash":               0xF1F8,   # delete
    "play":                0xF04B,
    "stop":                0xF04D,
    "floppy-disk":         0xF0C7,   # save
    "folder-open":         0xF07C,   # load
    "gear":                0xF013,   # settings
    "music":               0xF001,
    "wave-square":         0xF83E,
    "circle-nodes":        0xE4E2,   # physics/nodes
    "expand":              0xF065,   # fullscreen
    "compress":            0xF066,
    "eye":                 0xF06E,
    "eye-slash":           0xF070,
}

# Will be populated by setup_fonts()
ICONS = {}
_font_tag = None
_icon_font_tag = None


def _find_font_file(base_dir):
    candidates = [
        "Font Awesome 7 Free-Solid-900.otf",
        "Font Awesome 6 Free-Solid-900.otf",
        "fa-solid-900.otf",
        "FontAwesome.otf",
    ]
    for name in candidates:
        p = os.path.join(base_dir, name)
        if os.path.exists(p):
            return p
    # Try any otf/ttf in the folder
    for f in os.listdir(base_dir):
        if "solid" in f.lower() and f.endswith(".otf"):
            return os.path.join(base_dir, f)
    return None


def _load_codepoints_from_json(fonts_dir):
    """Try to load codepoints from FA's icons.json metadata file."""
    json_path = os.path.join(fonts_dir, "icons.json")
    if not os.path.exists(json_path):
        return {}
    try:
        with open(json_path) as f:
            data = json.load(f)
        result = {}
        for name, info in data.items():
            cp = info.get("unicode")
            if cp:
                result[name] = int(cp, 16)
        return result
    except Exception:
        return {}


def setup_fonts(dpg, base_dir=None, ui_size=14, icon_size=14):
    """
    Call once after dpg.create_context(), before creating windows.
    
    base_dir: folder containing the .otf file (default: fonts/ next to main.py)
    ui_size:  pt size for the main UI font
    icon_size: pt size for icons (match ui_size for inline icons)
    
    Returns True if icon font loaded, False if falling back to ASCII.
    """
    global ICONS, _font_tag, _icon_font_tag

    if base_dir is None:
        base_dir = os.path.join(os.path.dirname(__file__), "fonts")

    if not os.path.isdir(base_dir):
        _build_ascii_fallback()
        return False

    icon_file = _find_font_file(base_dir)

    # Load codepoints — prefer icons.json, fallback to known list
    codepoints = _load_codepoints_from_json(base_dir)
    if not codepoints:
        codepoints = _KNOWN

    with dpg.font_registry():
        # Try to load a UI font if one exists (Roboto, Inter, etc.)
        ui_candidates = ["Roboto-Regular.ttf", "Inter-Regular.ttf",
                         "OpenSans-Regular.ttf", "NotoSans-Regular.ttf"]
        for uc in ui_candidates:
            ui_path = os.path.join(base_dir, uc)
            if os.path.exists(ui_path):
                _font_tag = dpg.add_font(ui_path, ui_size)
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Default,
                                        parent=_font_tag)
                break

        if icon_file:
            _icon_font_tag = dpg.add_font(icon_file, icon_size)
            # Load the FA private use range
            dpg.add_font_range(0xE000, 0xF8FF, parent=_icon_font_tag)
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Default,
                                    parent=_icon_font_tag)

    if _font_tag:
        dpg.bind_font(_font_tag)

    # Build ICONS dict: name -> character string
    for name, cp in codepoints.items():
        ICONS[name] = chr(cp)
    for name, cp in _KNOWN.items():
        if name not in ICONS:
            ICONS[name] = chr(cp)

    if not icon_file:
        _build_ascii_fallback()
        return False

    return True


def _build_ascii_fallback():
    """Populate ICONS with readable ASCII when no font is available."""
    global ICONS
    fallback = {
        "arrow-pointer":      "SEL",
        "up-down-left-right": "MOV",
        "minus":              "---",
        "circle":             "(o)",
        "square":             "[ ]",
        "rotate":             "ROT",
        "water":              "OSC",
        "asterisk":           ":::",
        "magnet":             "ATT",
        "circle-dot":         "EMT",
        "trash":              "DEL",
        "play":               ">",
        "stop":               "[]",
        "floppy-disk":        "SAV",
        "folder-open":        "LDD",
        "gear":               "CFG",
        "music":              "MUS",
        "eye":                "VIS",
        "eye-slash":          "HID",
    }
    ICONS.update(fallback)


def bind_icon_font(dpg, item):
    """Bind the icon font to a specific DPG item (button etc.)."""
    if _icon_font_tag:
        dpg.bind_item_font(item, _icon_font_tag)
