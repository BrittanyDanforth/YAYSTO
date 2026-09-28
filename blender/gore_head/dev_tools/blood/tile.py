"""python3 tile.py OUT COLS img1 img2 ... -> grid (numpy + bpy image IO, no PIL)."""
import sys, numpy as np, bpy
import os
out, cols, files = os.path.abspath(sys.argv[1]), int(sys.argv[2]), [os.path.abspath(f) for f in sys.argv[3:]]
ims = []
for f in files:
    im = bpy.data.images.load(f); w, h = im.size
    ims.append(np.array(im.pixels[:], np.float32).reshape(h, w, 4)); bpy.data.images.remove(im)
h = max(i.shape[0] for i in ims); w = max(i.shape[1] for i in ims)
rows = (len(ims) + cols - 1) // cols
G = np.zeros((rows * h + (rows - 1) * 4, cols * w + (cols - 1) * 4, 4), np.float32); G[..., 3] = 1
for k, im in enumerate(ims):
    r, c = divmod(k, cols); r = rows - 1 - r
    G[r*(h+4):r*(h+4)+im.shape[0], c*(w+4):c*(w+4)+im.shape[1]] = im
o = bpy.data.images.new("t", G.shape[1], G.shape[0], alpha=True); o.pixels[:] = G.ravel()
o.filepath_raw = out; o.file_format = 'PNG'; o.save()
