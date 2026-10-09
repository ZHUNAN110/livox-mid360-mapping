import numpy as np, sys, os
from PIL import Image
from scipy import ndimage

src, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)

# ---------- 参数 ----------
RES     = 0.1      # 分辨率 m
Z_LO, Z_HI   = -2.5, 13.0   # 去掉下层 + 高层杂点
OBS_LO, OBS_HI = 1.0, 8.0   # 障碍高度带
THR     = 2        # 每格点数阈值
MIN_COMP = 5       # 去掉 <5 格的孤立噪声
DILATE  = 1        # 墙加粗/闭合断点 迭代次数

# ---------- 读点 ----------
raw = open(src,'rb').read()
he = raw.find(b'DATA binary'); hdr = raw[:he].decode('latin1')
fields = [l.split()[1:] for l in hdr.splitlines() if l.startswith('FIELDS')][0]
n = int([l.split()[1] for l in hdr.splitlines() if l.startswith('POINTS')][0])
ds = raw.find(b'\n', he)+1
arr = np.frombuffer(raw[ds:ds+n*len(fields)*4], np.float32).reshape(n,len(fields))
xi,yi,zi = fields.index('x'),fields.index('y'),fields.index('z')
x,y,z = arr[:,xi],arr[:,yi],arr[:,zi]

keep = (z>=Z_LO)&(z<=Z_HI)
x,y,z = x[keep],y[keep],z[keep]

xmin,xmax = np.floor(x.min()/RES)*RES, np.ceil(x.max()/RES)*RES
ymin,ymax = np.floor(y.min()/RES)*RES, np.ceil(y.max()/RES)*RES
nx = int(round((xmax-xmin)/RES))+1; ny = int(round((ymax-ymin)/RES))+1
ci = ((x-xmin)/RES).astype(np.int32); rj = ((ymax-y)/RES).astype(np.int32)
ci = np.clip(ci,0,nx-1); rj = np.clip(rj,0,ny-1)

obs_g = np.zeros((ny,nx), np.int32)
om = (z>=OBS_LO)&(z<=OBS_HI)
np.add.at(obs_g,(rj,ci), om.astype(np.int32))

occ = obs_g >= THR
print(f"原始障碍格: {int(occ.sum())}")

# 去噪：去掉 <MIN_COMP 格的孤立连通块
lab, nl = ndimage.label(occ)
sizes = ndimage.sum(occ, lab, range(1, nl+1))
rm = np.isin(lab, np.where(sizes < MIN_COMP)[0]+1)
occ[rm] = False
print(f"去噪后障碍格: {int(occ.sum())} (去掉 {int(rm.sum())} 格孤立噪声)")

# 墙加粗 + 闭合断点
occ = ndimage.binary_dilation(occ, iterations=DILATE)
print(f"加粗后障碍格: {int(occ.sum())}")

# 黑墙白底：障碍=0(黑)，其余=254(白，可通行)
img = np.full((ny,nx), 254, np.uint8)
img[occ] = 0
print(f"总格 {nx}x{ny} | 障碍 {int(occ.sum())} ({100*occ.sum()/(nx*ny):.1f}%) | 可通行 {int((~occ).sum())} ({100*(~occ).sum()/(nx*ny):.1f}%)")

with open(os.path.join(outdir,"map.pgm"),"wb") as f:
    f.write(f"P5\n{nx} {ny}\n255\n".encode()); f.write(img.tobytes())
with open(os.path.join(outdir,"map.yaml"),"w") as f:
    f.write("image: map.pgm\n")
    f.write(f"resolution: {RES}\n")
    f.write(f"origin: [{xmin:.4f}, {ymin:.4f}, 0.0]\n")
    f.write("negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n")
# 彩色预览（放大3x）
rgb=np.zeros((ny,nx,3),np.uint8)
rgb[occ]=(20,30,60); rgb[~occ]=(245,245,245)
Image.fromarray(rgb).resize((nx*3,ny*3), Image.NEAREST).save(os.path.join(outdir,"map_preview.png"))
print("已输出 map.pgm / map.yaml / map_preview.png")
