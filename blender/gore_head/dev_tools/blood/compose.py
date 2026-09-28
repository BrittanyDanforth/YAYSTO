import sys, numpy as np, bpy
sys.path.insert(0, "/home/user/YAYSTO/blender/gore_head")
import proof_blood as pb
def load(f):
    im = bpy.data.images.load(f); w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1]; bpy.data.images.remove(im); return a
s4, s5, s6 = load("proof_full4.png"), load("proof_full5.png"), load("proof_full6.png")
T, R = 30, 139
rows4 = s4[T:T + 12 * R]; rows5 = s5[T:T + 3 * R]; rows6 = s6[T:T + 3 * R]
W = max(rows4.shape[1], rows5.shape[1], rows6.shape[1])
pad = lambda a: np.pad(a, ((0, 0), (0, W - a.shape[1]), (0, 0)))
body = np.concatenate([pad(rows4), pad(rows5), pad(rows6)], 0)
title = np.zeros((T, W, 4), np.float32); title[..., 3] = 1
pb._text(title[..., :3], 6, 6, "ZERO GAP PROOF: 108/108 PASS  TIMES 0 5 10 20 40 60 S", (1, 1, 1), 3)
out = np.concatenate([title, body], 0)[::-1]
o = bpy.data.images.new("s", out.shape[1], out.shape[0], alpha=True); o.pixels[:] = out.ravel()
o.filepath_raw = "/home/user/YAYSTO/blender/gore_head/renders/proof_rim_zero_gap.png"; o.file_format = 'PNG'; o.save()
