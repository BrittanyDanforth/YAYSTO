import sys; sys.path.insert(0,'/home/user/YAYSTO/blender/gore_body')
import numpy as np, neuro
lo,hi=neuro.brain_box(); h=0.0015
xs=np.arange(lo[0],hi[0],h); ys=np.arange(lo[1],hi[1],h); zs=np.arange(lo[2],hi[2],h)
X,Y,Z=np.meshgrid(xs,ys,zs,indexing='ij'); X,Y,Z=X.ravel(),Y.ravel(),Z.ravel()
vb=0
for i in range(0,len(X),300000):
    vb+=(neuro.brain_sdf(X[i:i+300000],Y[i:i+300000],Z[i:i+300000])<0).sum()
print('brain cm3',vb*h**3*1e6)
