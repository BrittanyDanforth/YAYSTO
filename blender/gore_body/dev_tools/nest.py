import sys; sys.path.insert(0, '/home/user/YAYSTO/blender/gore_body')
import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index('--') + 1])
import posetest, gb_common as gbc, skull as SKL
md = posetest.load_meshes(posetest.SKIN + posetest.INNER)
ro = posetest.rest_outside(md)
m = ro["GB_Skeleton"]
v = md["GB_Skeleton"].v[m]
va = gbc.unwarp_points(v) - gbc.HEAD_OFFSET
gu = np.minimum(SKL.gum_sdf(va[:, 0], va[:, 1], va[:, 2], True), SKL.gum_sdf(va[:, 0], va[:, 1], va[:, 2], False))
print("outside", m.sum(), "gum-covered", (gu < 0).sum(), "within 1mm of gum", (gu < 0.001).sum())
A = gbc.import_head().anatomy
ov = A.oral_void(np.abs(va[:, 0]), va[:, 1], va[:, 2])
print("in oral void", (ov < 0).sum(), "near void", (ov < 0.002).sum())
nc = ~((gu < 0.001) | (ov < 0.002))
print("not covered", nc.sum(), va[nc][:10].round(4))
