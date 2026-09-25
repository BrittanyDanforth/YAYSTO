"""Shared helpers for the procedural gore head (Blender 5.x).

Everything in this project is generated from code: no downloaded meshes,
textures or add-ons. Works both as the `bpy` Python module
(`python3 build.py`) and inside Blender (`blender -b --python build.py`).
"""
import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
RENDER_DIR = os.path.join(HERE, "renders")

CONTROLS_NAME = "GH_Controls"

# name: (default, min, max, description)
CONTROL_PROPS = {
    "damage":     (1.0, 0.0, 1.0, "Global wound progression. 0 = intact even with hits placed"),
    "bleed":      (0.7, 0.0, 1.0, "Amount of blood: coverage around wounds and drip count/length"),
    "drip_time":  (1.0, 0.0, 1.0, "How far blood drips have run down. Animate 0 -> 1"),
    "wetness":    (0.8, 0.0, 1.0, "Glossiness of blood and exposed tissue"),
    "blood_age":  (0.0, 0.0, 1.0, "0 = fresh bright red, 1 = dried dark brown"),
    "bruising":   (0.6, 0.0, 1.0, "Bruise strength around blunt hits"),
    "swelling":   (0.5, 0.0, 1.0, "Tissue swelling around blunt hits"),
    "skin_tone":  (0.25, 0.0, 1.0, "0 = very light skin, 1 = very dark skin"),
    "pallor":     (0.0, 0.0, 1.0, "Paleness from blood loss"),
}


def reset_scene():
    """Start from an empty file with metric units."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    return scene


def get_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def link_object(obj, collection):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def ensure_controls():
    """Create (or return) the GH_Controls empty that owns every global gore slider."""
    obj = bpy.data.objects.get(CONTROLS_NAME)
    if obj is None:
        obj = bpy.data.objects.new(CONTROLS_NAME, None)
        obj.empty_display_type = 'CUBE'
        obj.empty_display_size = 0.02
        obj.location = (0.0, 0.0, 0.2)
        get_collection("GoreHead").objects.link(obj)
    for name, (default, lo, hi, desc) in CONTROL_PROPS.items():
        if name not in obj:
            obj[name] = default
        ui = obj.id_properties_ui(name)
        ui.update(min=lo, max=hi, soft_min=lo, soft_max=hi, default=default, description=desc)
    return obj


def drive(id_block, data_path, prop, index=-1, expression="v"):
    """Drive `id_block.<data_path>` from GH_Controls[prop] (variable name `v`)."""
    ctrl = ensure_controls()
    fc = id_block.driver_add(data_path, index) if index >= 0 else id_block.driver_add(data_path)
    drv = fc.driver
    drv.type = 'SCRIPTED'
    for v in list(drv.variables):
        drv.variables.remove(v)
    var = drv.variables.new()
    var.name = "v"
    var.type = 'SINGLE_PROP'
    var.targets[0].id_type = 'OBJECT'
    var.targets[0].id = ctrl
    var.targets[0].data_path = f'["{prop}"]'
    drv.expression = expression
    return fc


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


# Camera placements around the head (origin = midpoint between the ear canals,
# face looks toward -Y, Z up).
VIEWS = {
    "front":   ((0.0, -0.85, 0.02),   (0.0, -0.02, 0.0)),
    "three_q": ((-0.55, -0.62, 0.10), (0.0, -0.02, 0.0)),
    "side":    ((-0.85, -0.02, 0.02), (0.0, -0.02, 0.0)),
    "back":    ((0.35, 0.78, 0.18),   (0.0, 0.0, 0.02)),
    "top":     ((0.0, -0.35, 0.80),   (0.0, 0.0, 0.03)),
}


def add_camera(name, location, target=(0.0, 0.0, 0.0), lens=85.0):
    cam_data = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cam = bpy.data.objects.get(name) or bpy.data.objects.new(name, cam_data)
    if cam.name not in bpy.context.scene.collection.all_objects:
        get_collection("Stage").objects.link(cam)
    cam.location = location
    cam.data.lens = lens
    cam.data.clip_start = 0.01
    look_at(cam, target)
    return cam


def _area_light(name, location, target, energy, size, color=(1, 1, 1)):
    data = bpy.data.lights.get(name) or bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.size = size
    data.color = color
    obj = bpy.data.objects.get(name) or bpy.data.objects.new(name, data)
    if obj.name not in bpy.context.scene.collection.all_objects:
        get_collection("Stage").objects.link(obj)
    obj.location = location
    look_at(obj, target)
    return obj


def setup_stage():
    """Studio lighting (key / fill / rim) and a dark neutral world."""
    scene = bpy.context.scene
    _area_light("GH_Key", (-0.55, -0.75, 0.55), (0, 0, 0), 60.0, 0.6, (1.0, 0.96, 0.9))
    _area_light("GH_Fill", (0.8, -0.5, 0.1), (0, 0, 0), 18.0, 0.8, (0.85, 0.9, 1.0))
    _area_light("GH_Rim", (0.3, 0.7, 0.45), (0, 0, 0.05), 45.0, 0.4, (1.0, 0.95, 0.95))
    world = bpy.data.worlds.get("GH_World") or bpy.data.worlds.new("GH_World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.02, 0.022, 0.026, 1.0)
    bg.inputs[1].default_value = 1.0
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    return scene


def configure_render(samples=32, res=(640, 640)):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.max_bounces = 8
    try:
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    except (AttributeError, TypeError):
        pass
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    return scene


def render(path, camera=None, samples=32, res=(640, 640)):
    """Render a still to an absolute path. Returns the path."""
    scene = configure_render(samples, res)
    if camera is not None:
        scene.camera = camera
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def render_views(prefix, views=("front", "three_q", "side"), out_dir=RENDER_DIR,
                 samples=32, res=(640, 640), lens=85.0):
    """Render several named VIEWS; returns list of written file paths."""
    setup_stage()
    paths = []
    for v in views:
        loc, tgt = VIEWS[v]
        cam = add_camera(f"GH_Cam_{v}", loc, tgt, lens)
        paths.append(render(os.path.join(out_dir, f"{prefix}_{v}.png"), cam, samples, res))
    return paths
