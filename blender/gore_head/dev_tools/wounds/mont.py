"""mont.py OUT cols f1 f2 ... : grid montage via bpy (rows fill top-down)."""
import sys, os
import bpy, numpy as np
out, cols, files = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
ims = []
for f in files:
    im = bpy.data.images.load(os.path.abspath(f)); w, h = im.size
    ims.append(np.array(im.pixels[:], np.float32).reshape(h, w, 4)); bpy.data.images.remove(im)
H = max(i.shape[0] for i in ims); W = max(i.shape[1] for i in ims)
rows = (len(ims) + cols - 1) // cols
M = np.zeros((rows * H, cols * W, 4), np.float32); M[..., 3] = 1
for k, i in enumerate(ims):
    r, c = divmod(k, cols); r = rows - 1 - r
    M[r*H:r*H+i.shape[0], c*W:c*W+i.shape[1]] = i
o = bpy.data.images.new("m", cols * W, rows * H, alpha=True); o.pixels[:] = M.ravel()
o.filepath_raw = os.path.abspath(out); o.file_format = 'PNG'; o.save()
