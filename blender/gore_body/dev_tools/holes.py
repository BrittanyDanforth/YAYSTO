import sys; sys.path.insert(0, '/home/user/YAYSTO/blender/gore_body')
import bpy
bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index('--') + 1])
import gb_geom as gg, gb_common as gbc
for n in ("GB_Head", "GB_Head_LOD1", "GB_Head_HR", "GB_Body", "GB_Body_LOD1", "GB_Body_HR"):
    o = bpy.data.objects.get(n)
    if o is None: continue
    before = [len(l) for l in gg.boundary_loops(o.data)]
    k = gg.close_small_holes(o)
    after = [len(l) for l in gg.boundary_loops(o.data)]
    print(n, "before", sorted(before)[:12], len(before), "filled edges", k, "after", sorted(after)[:12], len(after))
