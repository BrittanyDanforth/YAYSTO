"""head-frame wrappers for section plots"""
import sys; sys.path.insert(0, '/home/user/YAYSTO/blender/gore_body')
import numpy as np, skeleton as SK, skull as SKL, gb_common as gbc
def skull(x, y, z): return SK._skull_head(x, y, z)
def mand(x, y, z): return SK._mandible_head(x, y, z)
def upteeth(x, y, z): return SKL.teeth_sdf(x, y, z, True)
def loteeth(x, y, z): return SKL.teeth_sdf(x, y, z, False)
def skin(x, y, z):
    import body_skin as BS
    O = gbc.HEAD_OFFSET
    return BS.skin_sdf(x + O[0], y + O[1], z + O[2])
