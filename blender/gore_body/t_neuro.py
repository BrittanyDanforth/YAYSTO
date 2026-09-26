import sys, time; sys.path.insert(0,'/home/user/YAYSTO/blender/gore_body')
import numpy as np, bpy, gb_common as gbc, neuro as N
gbc.reset_scene(); gbc.collections()
t=time.time(); c=N.build_cord_only(); print('cord tris', gbc.tri_count(c.data), round(time.time()-t,1))
u,v=gbc.read_codes_uv(c); print('codes', np.unique(u))
t=time.time(); b=N.build_brain(); print('brain', {k:gbc.tri_count(o.data) for k,o in b.items()}, round(time.time()-t,1))
bpy.ops.wm.save_as_mainfile(filepath='/tmp/claude-0/-home-user-YAYSTO/e2a2594c-08ec-5384-b9ca-fd553ec0f442/scratchpad/body/B4/neuro_test.blend')
