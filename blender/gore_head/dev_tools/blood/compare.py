"""python3 compare.py OUT HEIGHT img1 img2 ... -> one row, each resized to HEIGHT (numpy + bpy IO)."""
import sys, os, numpy as np, bpy
out, H = os.path.abspath(sys.argv[1]), int(sys.argv[2])
cells = []
for f in sys.argv[3:]:
    im = bpy.data.images.load(os.path.abspath(f)); w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, 4); bpy.data.images.remove(im)
    W = max(1, int(w * H / h))
    ys = (np.arange(H) * h / H).astype(int); xs = (np.arange(W) * w / W).astype(int)
    a = a[ys][:, xs]; a[..., 3] = 1
    cells.append(a); cells.append(np.ones((H, 4, 4), np.float32) * [0, 0, 0, 1])
G = np.concatenate(cells[:-1], 1)
o = bpy.data.images.new("c", G.shape[1], G.shape[0], alpha=True); o.pixels[:] = G.ravel()
o.filepath_raw = out; o.file_format = 'PNG'; o.save()
