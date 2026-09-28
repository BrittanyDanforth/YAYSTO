import bpy
from mathutils import Vector
import gh_common as ghc
import build

def cam_for(hit, view, dist):
    """Close-up cameras around a hit (straight / 45 / graze / wide) or a build camera."""
    if view in build.CAMERAS:
        return bpy.data.objects["GH_Cam_" + view]
    m = hit.matrix_world.to_3x3().normalized()
    z = (m @ Vector((0.0, 0.0, 1.0))).normalized()
    tgt = hit.matrix_world.translation + Vector((0, 0, -0.006))
    horiz = Vector((0, 0, 1)).cross(z).normalized()
    if view == "straight":
        d = z
    elif view == "45":
        d = (z + horiz * 1.0).normalized()
    elif view == "graze":
        d = (z * 0.26 + (horiz * 0.7 + Vector((0, 0, -0.7))).normalized() * 0.97).normalized()
    elif view == "wide":
        d = (z + horiz * 0.5 + Vector((0, 0, 0.2))).normalized()
        dist = dist * 2.6
        tgt = tgt + Vector((0, 0, -0.03))
    return ghc.add_camera(f"DEV_{view}", tgt + d * dist, tgt, 85.0)
