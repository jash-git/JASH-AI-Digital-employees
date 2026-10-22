#!/usr/bin/env python3
"""
boundary_check.py -- 判斷 ComfyUI image-to-3D GLB 是「封閉流形（有背面/可包覆）」還是「單面（開網格，無背面）」。

為什麼需要：glb_validate.py 確認「能否開啟 + 幾何有效」，但不區分封閉與否。單圖重建典型分成兩類：
  - front-facing / 2.5D 方法（如 MoGe）        -> 開網格（背面有邊界），只有正面。
  - voxel / occupancy 方法（如 Hunyuan3D v2.1）-> 封閉流形（等表層包一圈，有後臉、可包覆）。
判定法：解三角形，統計每條無向邊被使用的次數；只被一個三角形使用的邊 = 邊界邊。
  boundary_edges == 0 -> 封閉（watertight，可包覆）
  boundary_edges  > 0 -> 開網格（單面，有開口/背面缺失）

ComfyUI SaveGLB 的坑：BIN chunk 類型寫成 'BIN\0'（null 結尾），不是 spec 的 'BIN '（空格）。
所以 chunk type 要當 little-endian int 讀（0x004E4942 == 'BIN\0'），不能用字串 'BIN ' 比對。
本腳本與 skills/media/view-comfyui-glb/scripts/glb_validate.py 用相同區塊解析，可直接互補。

用法：
  python3 scripts/boundary_check.py "*.glb"   # 批次（預設掃描 cwd）
  python3 scripts/boundary_check.py <dir>      # 遞掃目錄
  python3 scripts/boundary_check.py a.glb b.glb  # 指定檔
回傳：全部能解析 -> 0；有解析失敗 -> 1（可接 CI）。幾何開/封閉本身不影響回傳碼。
"""
import sys, glob, os, json, struct

JSON_CHUNK = struct.unpack('<I', b'JSON')[0]
BIN_CHUNK  = 0x004E4942   # 'BIN\0' little-endian（ComfyUI exporter 用 null 結尾，非 spec 的 'BIN '）

def parse(path):
    """回傳 (json_bytes, bin_bytes)。不信任 header 的 numChunks，走區塊到結束。"""
    d = open(path, 'rb').read(); n = len(d); o = 12
    jb = bb = None
    for _ in range(min(struct.unpack_from('<I', d, 8)[0] + 1, 4096)):
        if o + 8 > n: break
        ln = struct.unpack_from('<I', d, o)[0]
        ty = struct.unpack_from('<I', d, o + 4)[0]
        if ln <= 0 or o + 8 + ln > n: break
        c = d[o + 8:o + 8 + ln]
        if ty == JSON_CHUNK and jb is None: jb = c
        elif ty == BIN_CHUNK and bb is None: bb = c
        o += 8 + ln   # 此格式 length 皆 %4==0，無 padding
    return jb, bb

def analyze(path):
    jb, bb = parse(path)
    if not jb: return None
    js = json.loads(jb.decode('utf-8', 'replace'))
    accs = js.get('accessors', [])
    bv = js.get('bufferViews', [{}])
    pos_idx = idx_idx = None
    for m in js.get('meshes', []):
        for pr in m.get('primitives', []):
            a = pr.get('attributes') or {}
            if 'POSITION' in a:
                pos_idx = a['POSITION']; idx_idx = pr.get('indices'); break
        if pos_idx is not None: break
    if pos_idx is None: return None
    pa = accs[pos_idx]; pv = bv[pa['bufferView']]; pbo = pv.get('byteOffset', 0) or 0
    V = pa['count']
    P = [struct.unpack_from('<fff', bb, pbo + k*12) for k in range(V) if pbo + k*12 + 12 <= len(bb)]
    tris = []
    if idx_idx is not None and idx_idx < len(accs):
        ia = accs[idx_idx]; iv = bv[ia['bufferView']]; bo = iv.get('byteOffset', 0) or 0
        comp = ia.get('componentType'); sz = {5121:1, 5123:2, 5125:4}.get(comp, 2)
        uf = {5121:'<B', 5123:'<H', 5125:'<I'}.get(comp, '<H')
        idxs = [struct.unpack_from(uf, bb, bo + k*sz)[0] for k in range(ia['count']) if bo + k*sz + sz <= len(bb)]
        for k in range(0, len(idxs) - 2, 3):
            tris.append((idxs[k], idxs[k+1], idxs[k+2]))
    else:
        for i in range(0, len(P) - 2, 3):
            tris.append((i, i+1, i+2))   # 非索引化：連續三點即三角形
    edges = {}
    for (a, b, c) in tris:
        for u, v in ((a,b),(b,c),(c,a)):
            e = (min(u,v), max(u,v)); edges[e] = edges.get(e, 0) + 1
    bnd = sum(1 for cnt in edges.values() if cnt == 1)
    return V, len(tris), bnd, (bnd == 0)

def iter_paths(args):
    paths = []
    for a in args:
        if os.path.isdir(a):
            paths += glob.glob(os.path.join(a, '**', '*.glb'), recursive=True)
        elif any(ch in a for ch in '*?['):
            paths += glob.glob(a)
        else:
            paths.append(a)
    return sorted(set(paths))

def main():
    args = sys.argv[1:] or ['*.glb']
    paths = iter_paths(args)
    if not paths:
        print("no .glb files matched"); return 1
    print(f"{'file':34s} {'verts':>6} {'tris':>7} {'boundary_edges':>15} {'closed':>6}")
    rc = 0
    for p in paths:
        r = analyze(p)
        if not r:
            print(f"{os.path.basename(p):34s} -> UNPARSEABLE"); rc = 1; continue
        V, T, bnd, closed = r
        print(f"{os.path.basename(p):34s} {V:6d} {T:7d} {bnd:15d} {str(closed):>6}")
    return rc

if __name__ == '__main__':
    sys.exit(main())
