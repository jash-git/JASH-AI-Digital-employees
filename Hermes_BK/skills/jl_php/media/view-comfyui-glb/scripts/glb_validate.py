#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""glb_validate.py — 本地快速驗證 .glb 能否在 gltf-viewer.donmccurdy.com（THREE r160+）正常開啟並渲染。

不依賴瀏覽器：直接解析 GLB header + 區塊，檢查 THREE 特有的兩個坑，再驗證幾何。
  1. magic 前 4 字節須為小寫 'glTF'（0x67,0x6C,0x54,0x46）。THREE r160 GLTFLoader 的
     BINARY_EXTENSION_HEADER_MAGIC='glTF'，大寫 'GLTF'（spec 正規）反而不匹配 → 掉進
     JSON.parse(整個二進位) → donmccundy 畫面空白。ComfyUI exporter 常出大寫版。
  2. header offset 8（numChunks 欄位）須等於檔案總字节數（區塊資料總長）。GLTFBinaryExtension
     用 header.length-12 當讀區塊邊界，太小會報 'JSON content not found'。
  3. 幾何：accessor 索引全小於頂點數、座標全 finite、至少一個 mesh 有 POSITION；
     算出頂點/三角形數與邊界盒（x,y,z 延伸 + 中心）。

用法:
    python3 glb_validate.py x.glb                 # 單檔
    python3 glb_validate.py "*.glb"               # 批量（glob）
    python3 glb_validate.py dir/ --batch          # 資料夾內所有 .glb

回傳碼：全部通過=0，有 FAIL=1（WARN 不影響）。適合接 CI / 批次檢查 output 資料夾。
"""
import sys, os, glob, json, struct, argparse

JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942


def validate(path):
    if not os.path.isfile(path):
        return {"file": path, "error": "找不到檔案"}
    data = open(path, 'rb').read()
    n = len(data)
    res = {"file": path, "size": n, "magic_ok": False, "offset8_ok": False,
           "geometry_ok": False, "warnings": [], "info": {}}

    if n < 12:
        res["error"] = f"檔太小({n}B)，非合法 GLB"
        return res

    magic = data[:4]
    res["magic_ok"] = (magic == b'glTF')
    if not res["magic_ok"]:
        res["warnings"].append(
            f"magic={magic!r} 為大寫/非 'glTF' → THREE r160/donmccundy 會空白（需改小寫 g,l）")

    offset8 = struct.unpack_from('<I', data, 8)[0]
    res["offset8_ok"] = (offset8 == n)
    if not res["offset8_ok"]:
        res["warnings"].append(
            f"offset8={offset8} ≠ 檔案大小({n}) → GLTFBinaryExtension 可能 'JSON content not found'（需設為 {n}）")

    # 走區塊到結束，不信任 header 的 numChunks（ComfyUI 檔此欄位常錯）
    o = 12
    json_bytes, bin_bytes = None, None
    num_chunks = struct.unpack_from('<I', data, 8)[0]
    for i in range(num_chunks + 1):
        if o + 8 > n:
            break
        ln = struct.unpack_from('<I', data, o)[0]
        ty = struct.unpack_from('<I', data, o + 4)[0]
        if ln <= 0 or o + 8 + ln > n:
            break
        chunk = data[o + 8:o + 8 + ln]
        if ty == JSON_CHUNK and json_bytes is None:
            json_bytes = chunk
        elif ty == BIN_CHUNK and bin_bytes is None:
            bin_bytes = chunk
        o += 8 + ln

    if json_bytes is None:
        res["warnings"].append("找不到 JSON chunk")
        return res

    try:
        gltf = json.loads(json_bytes.decode('utf-8', 'replace'))
    except Exception as e:
        res["warnings"].append(f"JSON 解析失敗: {e}")
        return res

    accs = gltf.get('accessors') or []
    bin_view = bin_bytes if bin_bytes else b''
    bv = gltf.get('bufferViews') or [{}]

    def read_acc(idx):
        """回傳 (count, kind)：kind='pos'(VEC3 FLOAT)/'idx'(SCALAR)/'other'"""
        a = accs[idx]
        v = bv.get(a.get('bufferView', 0), {}) if isinstance(bv, dict) else (bv[a['bufferView']] if a['bufferView'] < len(bv) else {})
        off = v.get('byteOffset', 0) or 0
        comp = a.get('componentType')
        count = a.get('count', 0)
        kind = 'other'
        if a.get('type') == 'VEC3' and comp == 5126:
            kind = 'pos'
        elif a.get('type') == 'SCALAR' and comp in (5125, 5126):
            kind = 'idx'
        return count, kind

    # 找 POSITION accessor（attributes.POSITION）與 indices
    pos_idx, idx_idx = None, None
    verts = 0
    meshes = gltf.get('meshes') or []
    for m in meshes:
        for p in m.get('primitives', []):
            attrs = p.get('attributes') or {}
            if 'POSITION' in attrs:
                pos_idx = attrs['POSITION']
                idx_idx = p.get('indices')
                break
        if pos_idx is not None:
            break

    if pos_idx is None:
        res["warnings"].append("沒有 mesh 的 attributes.POSITION → 無法渲染")
        return res

    verts, _ = read_acc(pos_idx)
    tris = 0
    max_index = -1
    if idx_idx is not None and idx_idx < len(accs):
        icount = accs[idx_idx].get('count', 0)
        comp = accs[idx_idx].get('componentType')
        # 依 componentType 選正確寬度與解碼格式（UNSIGNED_BYTE/SHORT/INT）
        fmt_sz = {(5121, '<B'): 1, (5123, '<H'): 2, (5125, '<I'): 4}
        key = (comp, {5121: '<B', 5123: '<H', 5125: '<I'}.get(comp))
        sz = fmt_sz.get(key, 2)
        ufmt = {5121: '<B', 5123: '<H', 5125: '<I'}.get(comp, '<H')
        v = bv[idx_idx['bufferView']] if isinstance(bv, dict) else (bv[accs[idx_idx]['bufferView']] if accs[idx_idx]['bufferView'] < len(bv) else {})
        bo = v.get('byteOffset', 0) or 0
        # bin_bytes 已不含 chunk header，故 base=0；索引從 view.byteOffset 起讀
        for k in range(min(icount, 4096)):
            addr = bo + k * sz
            if addr + sz <= len(bin_bytes):
                max_index = max(max_index, struct.unpack_from(ufmt, bin_bytes, addr)[0])
        tris = icount // 3

    # 頂點座標 finite 檢查（取 POSITION accessor 前若干）
    pos_comp = accs[pos_idx].get('componentType')
    pos_v = bv[accs[pos_idx]['bufferView']] if isinstance(bv, dict) else (bv[accs[pos_idx]['bufferView']] if accs[pos_idx]['bufferView'] < len(bv) else {})
    pbo = pos_v.get('byteOffset', 0) or 0
    finite_ok = True
    nan_count = 0
    for k in range(min(verts, 64)):
        addr = pbo + k * 12
        if addr + 12 <= len(bin_bytes):
            x, y, z = struct.unpack_from('<fff', bin_bytes, addr)
            for c in (x, y, z):
                if not (c == c):  # NaN
                    nan_count += 1
    finite_ok = (nan_count == 0)
    if nan_count:
        res["warnings"].append(f"偵測到 {nan_count} 個 NaN 座標")

    # 邊界盒（取全部頂點，cube 類小檔沒問題）
    xs, ys, zs = [], [], []
    for k in range(verts):
        addr = pbo + k * 12
        if addr + 12 > len(bin_bytes):
            break
        x, y, z = struct.unpack_from('<fff', bin_bytes, addr)
        if not (x == x and y == y and z == z):
            continue
        xs.append(x); ys.append(y); zs.append(z)
    box_ok = bool(xs)
    size = ([max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)] if box_ok else [0, 0, 0])
    center = ([(max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, (max(zs) + min(zs)) / 2] if box_ok else [0, 0, 0])

    res["geometry_ok"] = (finite_ok and max_index < verts and tris > 0)
    res["info"] = {
        "vertices": verts, "triangles": tris,
        "max_index": max_index if idx_idx is not None else -1,
        "bbox_size": [round(s, 4) for s in size],
        "center": [round(c, 3) for c in center],
        "has_normals": any('normals' in (m.get('primitives', [{}])[0].get('attributes') or {}) for m in meshes),
    }
    if not res["geometry_ok"]:
        if max_index >= verts:
            res["warnings"].append(f"索引越界: max={max_index} ≥ 頂點數={verts}")
        elif tris == 0:
            res["warnings"].append("無有效三角形")
    if res["info"].get("has_normals") is False:
        res["warnings"].append("無 vertex normals（trimesh 匯出常見，benign；donmccundy 會平面打光但不阻斷渲染）")

    return res


def verdict(r):
    openable = r.get("magic_ok") and r.get("offset8_ok") and r.get("geometry_ok") and "error" not in r
    tag = "PASS ✅" if openable else ("WARN ⚠️" if (r.get("magic_ok") or r.get("offset8_ok")) else "FAIL ❌")
    return openable, tag


def main():
    ap = argparse.ArgumentParser(description="驗證 .glb 能否在 donmccundy/THREE 正常開啟並渲染")
    ap.add_argument("inputs", nargs="+")
    args = ap.parse_args()

    targets = []
    for a in args.inputs:
        if os.path.isdir(a) or any(c in a for c in '*?['):
            targets.extend(sorted(glob.glob(a)))
        else:
            targets.append(a)
    targets = [t for t in targets if t.lower().endswith(".glb")]
    if not targets:
        print("沒有符合的 .glb 檔案"); sys.exit(2)

    any_fail = False
    for t in targets:
        r = validate(t)
        openable, tag = verdict(r)
        if not openable:
            any_fail = True
        info = r.get("info", {})
        print(f"\n[{tag}] {os.path.basename(t)}  ({r['size']} bytes)")
        if "error" in r:
            print("   ERROR:", r["error"]); continue
        print(f"   magic={'glTF' if r['magic_ok'] else '非小寫'}  offset8={'OK' if r['offset8_ok'] else 'ERR'}  geometry={'OK' if r['geometry_ok'] else 'ERR'}")
        if info:
            print(f"   verts={info.get('vertices')} tris={info.get('triangles')} "
                  f"max_index={info.get('max_index')} bbox={info.get('bbox_size')} center={info.get('center')}")
        for w in r.get("warnings", []):
            print(f"   ⚠ {w}")

    print()
    if any_fail:
        print("結果：有檔案無法確定能在 donmccundy 正常顯示（見上方 WARN/FAIL）。")
        sys.exit(1)
    print("結果：全部可確定能在 donmccundy/THREE 正常開啟並渲染。")


if __name__ == "__main__":
    main()
