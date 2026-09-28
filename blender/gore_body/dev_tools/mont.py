import sys, numpy as np, bpy
# montage PNGs (rows of pairs) using Blender image API
out = sys.argv[sys.argv.index('--') + 1]; files = sys.argv[sys.argv.index('--') + 2:]
cols = 2
imgs = [bpy.data.images.load(f) for f in files]
w, h = imgs[0].size
rows = (len(imgs) + cols - 1) // cols
canvas = np.zeros((rows * h, cols * w, 4), np.float32)
for i, im in enumerate(imgs):
    a = np.array(im.pixels[:], np.float32).reshape(h, w, 4)
    r, c = i // cols, i % cols
    canvas[(rows - 1 - r) * h:(rows - r) * h, c * w:(c + 1) * w] = a
res = bpy.data.images.new("m", cols * w, rows * h, alpha=True)
res.pixels = canvas.ravel(); res.filepath_raw = out; res.file_format = 'PNG'; res.save()
