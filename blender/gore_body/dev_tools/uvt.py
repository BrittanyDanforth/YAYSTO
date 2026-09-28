import sys, os, time, hashlib; sys.path.insert(0, '/home/user/YAYSTO/blender/gore_body')
import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index('--') + 1])
import gb_common as gbc
gbc.CACHE_DIR = '/tmp/claude-0/-home-user-YAYSTO/e2a2594c-08ec-5384-b9ca-fd553ec0f442/scratchpad/body/fix5/uvcache'
import bake
hs = []
for run in range(2):
    t = time.time()
    bake.RECHART = {k: v for k, v in bake.RECHART.items() if k == "GB_Skeleton"}
    bake.prepare_uvs(force=True)
    me = bpy.data.objects["GB_Skeleton"].data
    uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers["atlas"].data.foreach_get("uv", uv)
    hs.append(hashlib.sha256(uv.tobytes()).hexdigest()[:12])
    print("run", run, time.time() - t, bake._RESULTS["uv"].get("GB_Skeleton"), hs[-1])
print("deterministic", hs[0] == hs[1])
