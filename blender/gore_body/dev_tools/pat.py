import sys, os; sys.path.insert(0, '/home/user/YAYSTO/blender/gore_body')
import bpy, numpy as np, gb_common as gbc, skeleton as SK
out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
for nm, (fn, box) in (("pat", SK.patella_sdf()[:2]), ("clav", SK.clavicle_sdf()[:2])):
    v, f = SK.mesh_sdf(fn, box, 0.0007)
    me = gbc.mesh_from_arrays(nm, v, f); o = bpy.data.objects.new(nm, me); bpy.context.scene.collection.objects.link(o); me.shade_smooth()
    print(nm, "extent mm", ((v.max(0) - v.min(0)) * 1000).round(1))
gbc.setup_stage()
V = {"pat_front": ((0.09, -0.25, 0.50), (0.09, -0.02, 0.50), 100), "pat_side": ((0.30, -0.02, 0.50), (0.09, -0.02, 0.50), 100),
     "clav_top": ((0.10, -0.02, 1.80), (0.10, -0.02, 1.455), 60)}
for k, (l, t, fl) in V.items():
    gbc.render(os.path.join(out, k + ".png"), gbc.add_camera(k, l, t, fl), 12, (300, 300))
