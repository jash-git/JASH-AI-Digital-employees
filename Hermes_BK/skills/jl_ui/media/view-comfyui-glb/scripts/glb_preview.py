#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""glb_preview.py -- 把任何 .glb 轉成「單檔案自包含 HTML」預覽頁（模型 base64 內嵌）。

雙擊即可用瀏覽器開啟，不需伺服器、不受 gltf-viewer.donmccurdy.com 的 magic/numChunks 坑影響。
three.js 手勢解析 GLB + 自動對焦相機 + 打光 + 滑鼠互動（拖動旋轉/滾輪縮放/右鍵平移）。
材質用預設單色（金色），清楚顯示網格形狀；模型內嵌的紋理會在 donmccundy 等真 glTF 檢視器中呈現。

用法:
    python3 glb_preview.py input.glb                 -> 輸出 input_預覽.html
    python3 glb_preview.py input.glb out.html        -> 指定輸出檔名
    python3 glb_preview.py "*.glb"                   -> 批量（glob）為每個 glb 產生 _預覽.html

實作方式: 用 .replace() 填入 base64，不用 str.format()（避免 JS/CSS 的花括号被誤判）。
"""
import sys, os, base64, glob, argparse

HTML = r'''<!doctype html>
<html><head><meta charset="utf-8"><title>__TITLE__ 3D 預覽</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#1d1f22;font-family:sans-serif}
#info{position:absolute;left:10px;top:8px;color:#eee;font:13px sans-serif;z-index:10;max-width:60ch}
#hint{position:absolute;left:10px;bottom:8px;color:#888;font:12px sans-serif}</style>
<script type="importmap">{ "imports": {
  "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
  "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
}}</script>
</head><body>
<div id="info">載入中…</div>
<div id="hint">拖動旋轉 · 滾輪縮放 · 右鍵平移</div>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// 手勢解析 GLB：從 offset 12 走區塊到結束，不信任 header 的 numChunks（ComfyUI 檔此欄位常錯）。
async function loadGLB(){
  const buf = await (await fetch("data:model/glb;base64,__B64__")).arrayBuffer();
  const dv = new DataView(buf); let o=12; const jsonCh=[], binCh=[];
  const numChunks=dv.getUint32(8,true);          // 讀取但不依賴它做邊界
  for(let i=0;i<numChunks+1;i++){                 // +1 容錯：走到資料結束
    if(o+8>buf.byteLength) break;
    const len=dv.getUint32(o,true), typ=dv.getUint32(o+4,true);
    if(len<=0 || o+8+len>buf.byteLength) break;
    const chunk=new Uint8Array(buf,o+8,len); o+=8+len;
    (typ===0x4e4f534a?jsonCh:binCh).push(chunk);
  }
  if(jsonCh.length===0) throw new Error("找不到 JSON chunk");
  const glb=JSON.parse(new TextDecoder().decode(jsonCh[0]));
  const bin=binCh[0], bv=glb.bufferViews, acc=glb.accessors;
  function rd(i){ const v=bv[acc[i].bufferView], off=v.byteOffset||0; const t=acc[i].componentType, n=acc[i].count;
    if(t===5126) return new Float32Array(bin.buffer,bin.byteOffset+off,v.byteLength/4);
    if(t===5125) return new Uint32Array(bin.buffer,bin.byteOffset+off,n);
    return new Uint16Array(bin.buffer,bin.byteOffset+off,n); }
  const pos=rd(0), idx=rd(1);
  const g=new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos,3));
  if(idx) g.setIndex(new THREE.BufferAttribute(idx,1));
  g.computeVertexNormals();
  return g;
}

const scene=new THREE.Scene(); scene.background=new THREE.Color(0x2b2f36);
const camera=new THREE.PerspectiveCamera(50,innerWidth/innerHeight,0.01,100);
const renderer=new THREE.WebGLRenderer({antialias:true});
renderer.setSize(innerWidth,innerHeight); document.body.appendChild(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement); controls.enableDamping=true;
scene.add(new THREE.AmbientLight(0xffffff,0.85));
const d1=new THREE.DirectionalLight(0xffffff,1.4); d1.position.set(2,3,2); scene.add(d1);
const d2=new THREE.DirectionalLight(0x9ab,0.6); d2.position.set(-2,-1,-3); scene.add(d2);

loadGLB().then(g=>{
  const p=g.getAttribute('position').array;
  let minx=1e9,maxx=-1e9,miny=1e9,maxy=-1e9,minz=1e9,maxz=-1e9;
  for(let i=0;i<p.length;i+=3){ if(p[i]<minx)minx=p[i]; if(p[i]>maxx)maxx=p[i]; if(p[i+1]<miny)miny=p[i+1]; if(p[i+1]>maxy)maxy=p[i+1]; if(p[i+2]<minz)minz=p[i+2]; if(p[i+2]>maxz)maxz=p[i+2]; }
  const sx=maxx-minx,sy=maxy-miny,sz=maxz-minz;
  for(let i=0;i<p.length;i+=3){ p[i]-=(minx+maxx)/2; p[i+1]-=(miny+maxy)/2; p[i+2]-=(minz+maxz)/2; }
  const maxDim=Math.max(sx,sy,sz);
  camera.position.set(0,0,(maxDim/2/Math.tan(THREE.MathUtils.degToRad(camera.fov/2)))*1.4);
  controls.target.set(0,0,0); controls.update();
  scene.add(new THREE.Mesh(g,new THREE.MeshStandardMaterial({roughness:0.85,metalness:0.0,color:0xd9a441})));
  document.getElementById('info').textContent='\u2705 \u6A21\u578B\u5DF2\u6E32\u67D3 \u2014 '+sx.toFixed(2)+' x '+sy.toFixed(2)+' x '+sz.toFixed(2)+' m';
}).catch(e=>{ document.getElementById('info').textContent='\u274C \u984F\u8AA4: '+e; console.error(e); });

(function loop(){ requestAnimationFrame(loop); renderer.render(scene,camera); })();
addEventListener('resize',()=>{ camera.aspect=innerWidth/innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth,innerHeight); });
</script></body></html>'''


def generate(inp, out=None):
    if not os.path.isfile(inp):
        raise SystemExit(f"找不到檔案: {inp}")
    b64 = base64.b64encode(open(inp, 'rb').read()).decode()
    title = os.path.splitext(os.path.basename(inp))[0]
    if out is None:
        out = os.path.splitext(inp)[0] + '_預覽.html'
    html = HTML.replace("__TITLE__", title).replace("__B64__", b64)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"WROTE {out}  ({os.path.getsize(out)} bytes)  from  {inp}")


def main():
    ap = argparse.ArgumentParser(description="把 .glb 轉成單檔案自包含 HTML 預覽頁")
    ap.add_argument("inputs", nargs="+", help=".glb 路徑；含 * ? [ 時當 glob 批量處理")
    args = ap.parse_args()

    targets = []
    for a in args.inputs:
        if os.path.isdir(a) or any(c in a for c in '*?['):
            targets.extend(sorted(glob.glob(a)))
        else:
            targets.append(a)
    targets = [t for t in targets if t.lower().endswith(".glb")]  # 過濾 _預覽.html 等
    if not targets:
        raise SystemExit("沒有符合的 .glb 檔案")
    for t in targets:
        generate(t)


if __name__ == "__main__":
    main()
