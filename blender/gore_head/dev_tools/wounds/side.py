"""side.py OUT H f1 f2 ...: images scaled to height H, side by side in rows of 2 (pairs)."""
import sys, os
import bpy, numpy as np
out, H, files = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
def load(f):
    im = bpy.data.images.load(os.path.abspath(f)); w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, 4); bpy.data.images.remove(im)
    W = int(w * H / h); yi = (np.arange(H) * h / H).astype(int); xi = (np.arange(W) * w / W).astype(int)
    return a[yi][:, xi]
ims = [load(f) for f in files]
rows = []
for k in range(0, len(ims), 2):
    pair = ims[k:k + 2]
    rows.append(np.concatenate(pair + [np.zeros((H, 6, 4), np.float32)], 1))
Wm = max(r.shape[1] for r in rows)
rows = [np.pad(r, ((0, 6), (0, Wm - r.shape[1]), (0, 0))) for r in rows]
M = np.concatenate(rows[::-1], 0); M[..., 3] = 1
o = bpy.data.images.new("m", M.shape[1], M.shape[0], alpha=True); o.pixels[:] = M.ravel()
o.filepath_raw = os.path.abspath(out); o.file_format = 'PNG'; o.save()
