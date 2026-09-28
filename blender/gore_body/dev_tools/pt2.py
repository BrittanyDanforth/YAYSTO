import sys; sys.path.insert(0, '/home/user/YAYSTO/blender/gore_body')
import bpy, numpy as np
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
import posetest
md = posetest.load_meshes(posetest.SKIN + posetest.INNER + ("GB_Shorts",))
res = posetest.run_tests(a[1].split(","), md=md, quiet=True)
for k, v in res.items():
    print("RES", k, v.get("ok"), {kk: vv for kk, vv in v.items() if kk not in ("layers",)})
