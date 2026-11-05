import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

// ---------------------------------------------------------------------------------------------
// Everything is modelled in the enclosure's coordinates (mm): x right, y away from the typist,
// z up, origin at the front-left-bottom outer corner.  three.js is y-up, so case (x, y, z) -> (x, z, -y).
const C = (x, y, z) => new THREE.Vector3(x, z, -y);
const CENTER = C(90, 38, 9);

const COLORS = [
  ['Neon green', '#39ff14'], ['Purple', '#b026ff'], ['Red', '#ff2442'], ['Blue', '#2d6bff'], ['Cyan', '#00f0ff'],
  ['Pink', '#ff2ec4'], ['Orange', '#ff7a00'], ['Yellow', '#e8ff1a'], ['Ice', '#d8f1ff'], ['Smoke', '#7a7f87'],
];

// ---------------------------------------------------------------------------------------------- renderer
const host = document.getElementById('viewport');
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.9;
host.appendChild(renderer.domElement);

const labels = new CSS2DRenderer();
labels.domElement.style.position = 'absolute';
labels.domElement.style.inset = '0';
labels.domElement.style.pointerEvents = 'none';
host.appendChild(labels.domElement);

const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.55;

const camera = new THREE.PerspectiveCamera(32, 1, 1, 5000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.copy(CENTER);
controls.minDistance = 90;
controls.maxDistance = 900;
camera.position.copy(CENTER).add(new THREE.Vector3(-110, 250, 330));

scene.add(new THREE.HemisphereLight(0xcfe8ff, 0x101418, 0.6));
const key = new THREE.DirectionalLight(0xffffff, 1.1);
key.position.set(-200, 400, 250);
scene.add(key);
const rim = new THREE.DirectionalLight(0x88aaff, 0.8);
rim.position.set(300, 150, -300);
scene.add(rim);

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.55, 0.45, 0.9);
composer.addPass(bloom);
composer.addPass(new OutputPass());

// soft floor glow
const floor = new THREE.Mesh(
  new THREE.CircleGeometry(1600, 96),
  new THREE.MeshBasicMaterial({ color: 0x39ff14, transparent: true, opacity: 0.06, depthWrite: false }));
floor.rotation.x = -Math.PI / 2;
floor.position.set(CENTER.x, -0.5, CENTER.z);
scene.add(floor);

// ---------------------------------------------------------------------------------------------- groups
// each group can be exploded upwards by its own amount
const parts = {
  caseG: new THREE.Group(), bezelG: new THREE.Group(), pcbG: new THREE.Group(), pb2G: new THREE.Group(),
  panelG: new THREE.Group(), switchG: new THREE.Group(), capG: new THREE.Group(), hwG: new THREE.Group(),
};
const EXPLODE = { caseG: 0, pcbG: 14, hwG: 30, pb2G: 46, panelG: 74, bezelG: 96, switchG: 26, capG: 44 };
Object.values(parts).forEach((g) => scene.add(g));

// ---------------------------------------------------------------------------------------------- materials
let caseColor = new THREE.Color(COLORS[0][1]);
const shellMat = new THREE.MeshPhysicalMaterial({
  color: caseColor, roughness: 0.18, metalness: 0, transmission: 0.55, thickness: 2.0, ior: 1.49,
  attenuationColor: caseColor, attenuationDistance: 6, emissive: caseColor, emissiveIntensity: 0.06,
  transparent: true, opacity: 0.35, side: THREE.DoubleSide, depthWrite: false, clearcoat: 0.6, clearcoatRoughness: 0.2,
});
const edgeMat = new THREE.LineBasicMaterial({ color: caseColor, transparent: true, opacity: 0.9 });
const neonEdge = (mesh) => {
  const e = new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry, 28), edgeMat);
  e.matrix.copy(mesh.matrix); e.matrixAutoUpdate = mesh.matrixAutoUpdate;
  e.position.copy(mesh.position); e.rotation.copy(mesh.rotation); e.scale.copy(mesh.scale);
  return e;
};

function setCaseColor(hex) {
  caseColor = new THREE.Color(hex);
  shellMat.color.copy(caseColor);
  shellMat.attenuationColor.copy(caseColor);
  shellMat.emissive.copy(caseColor);
  edgeMat.color.copy(caseColor);
  floor.material.color.copy(caseColor);
  document.documentElement.style.setProperty('--accent', hex);
  screen.accent = hex;
}

// ---------------------------------------------------------------------------------------------- loading
const manager = new THREE.LoadingManager();
manager.onProgress = (_u, done, total) => {
  document.getElementById('loadbar').style.width = `${(100 * done) / total}%`;
};
manager.onLoad = () => document.getElementById('loader').classList.add('done');
const stl = new STLLoader(manager);
const gltf = new GLTFLoader(manager);
gltf.setMeshoptDecoder(MeshoptDecoder);

const stlToCase = (geom) => {           // STL is in case coordinates, z-up
  geom.rotateX(-Math.PI / 2);
  geom.computeVertexNormals();
  return geom;
};

stl.load('assets/case.stl', (g) => {
  const m = new THREE.Mesh(stlToCase(g), shellMat);
  m.renderOrder = 2;
  parts.caseG.add(m, neonEdge(m));
});
stl.load('assets/bezel.stl', (g) => {
  const m = new THREE.Mesh(stlToCase(g), shellMat);
  m.renderOrder = 3;
  parts.bezelG.add(m, neonEdge(m));
});

// KiCad GLB: metres, x = case x, y = height above the board bottom, z = -case y; the board bottom is at z 4.5
gltf.load('assets/pcb.glb', (g) => {
  g.scene.scale.setScalar(1000);
  g.scene.position.y = 4.5;
  g.scene.traverse((o) => { if (o.isMesh) { o.material.side = THREE.DoubleSide; } });
  parts.pcbG.add(g.scene);
});

// Official PocketBeagle 2 STEP (BeagleBoard design/old/pocketbeagle2_v03_21_EVT) via KiCad: glb = (step x, step z + 1.6, -step y).
// Placed exactly as in the SolidCraft assembly: flipped component-side up, USB-C to the left wall, sockets on the PCB.
gltf.load('assets/pocketbeagle2.glb', (g) => {
  g.scene.scale.setScalar(1000);
  g.scene.rotation.z = Math.PI;
  g.scene.position.set(-274.185, 16.2, 194.115);
  // the STEP leaves pads/copper/board uncoloured (white): small ones -> copper, large -> black soldermask
  const copper = new THREE.MeshStandardMaterial({ color: 0xc9a25a, metalness: 1, roughness: 0.35 });
  const mask = new THREE.MeshStandardMaterial({ color: 0x0c0d10, roughness: 0.55, metalness: 0.1 });
  const size = new THREE.Vector3();
  g.scene.traverse((o) => {
    if (!o.isMesh || o.material.color.getHex() !== 0xffffff) return;
    o.geometry.computeBoundingBox();
    o.geometry.boundingBox.getSize(size);
    const mm = Math.max(size.x, size.y, size.z) * 1000;     // glb is in metres
    o.material = mm < 4 ? copper : mask;
  });
  parts.pb2G.add(g.scene);
});

// ---------------------------------------------------------------------------------------------- display panel
// 118.8 x 41.57 x 2.5 panel at x 28.2-147.0, y 75.415-116.985, z 18.6-21.1; active area 110.3 x 36.77 centred (85.65, 96.2)
const panelBody = new THREE.Mesh(new THREE.BoxGeometry(118.8, 2.5, 41.57),
  new THREE.MeshStandardMaterial({ color: 0x0b0c0e, roughness: 0.35, metalness: 0.2 }));
panelBody.position.copy(C(87.6, 96.2, 19.85));
parts.panelG.add(panelBody);

const screen = {
  canvas: document.createElement('canvas'), accent: COLORS[0][1], lines: [], typed: '', t0: performance.now(),
};
screen.canvas.width = 1920; screen.canvas.height = 640;
screen.ctx = screen.canvas.getContext('2d');
screen.tex = new THREE.CanvasTexture(screen.canvas);
screen.tex.colorSpace = THREE.SRGBColorSpace;
screen.tex.anisotropy = 8;
const screenMesh = new THREE.Mesh(new THREE.PlaneGeometry(110.3, 36.77),
  new THREE.MeshBasicMaterial({ map: screen.tex, toneMapped: false }));
screenMesh.rotation.x = -Math.PI / 2;
screenMesh.position.copy(C(85.65, 96.2, 21.12));
parts.panelG.add(screenMesh);

const BOOT = [
  'U-Boot SPL 2025.10 (AM62x)', 'Starting kernel ...', '[    0.000000] Booting Linux on physical CPU 0x0',
  '[    1.204311] tidss 30200000.dss: [drm] panel st7701 320x960 RGB565', '[    1.330102] usb 1-1: new full-speed USB device (bancouver40)',
  '[    1.391876] input: sporewoh bancouver40 as /devices/platform/bus@f0000/31100000.usb/input/input0',
  'Debian GNU/Linux 13 zinemachine ttyGS0', '', 'pocketbeagle2 login: debian', 'Last login: Wed Nov  5 02:18 on tty1',
];
let bootIdx = 0;
function drawScreen(now) {
  const { ctx, canvas } = screen;
  const W = canvas.width, H = canvas.height;
  ctx.fillStyle = '#020403'; ctx.fillRect(0, 0, W, H);
  // scanline sheen
  const grd = ctx.createLinearGradient(0, 0, 0, H);
  grd.addColorStop(0, '#0a120c'); grd.addColorStop(1, '#020403');
  ctx.fillStyle = grd; ctx.fillRect(0, 0, W, H);
  // status bar
  ctx.fillStyle = screen.accent; ctx.globalAlpha = 0.18; ctx.fillRect(0, 0, W, 64); ctx.globalAlpha = 1;
  ctx.font = '600 34px "JetBrains Mono", monospace'; ctx.fillStyle = screen.accent; ctx.textBaseline = 'middle';
  const d = new Date();
  ctx.fillText(' zine machine v0 · am6254 · 512M', 10, 33);
  const cpu = (18 + 14 * Math.sin(now / 900) + 6 * Math.sin(now / 230)).toFixed(0).padStart(2, ' ');
  const right = `cpu ${cpu}%  ${d.toTimeString().slice(0, 8)} `;
  ctx.fillText(right, W - ctx.measureText(right).width - 10, 33);
  // cpu sparkline
  ctx.strokeStyle = screen.accent; ctx.lineWidth = 3; ctx.beginPath();
  for (let i = 0; i < 120; i++) {
    const v = 0.5 + 0.35 * Math.sin((now / 400) - i * 0.25) * Math.sin(i * 0.11 + now / 2000);
    const x = W - 520 + i * 4, y = 64 + 40 + v * 90;
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  }
  ctx.stroke();
  // boot log + prompt
  if (bootIdx < BOOT.length && now - screen.t0 > 350 * (bootIdx + 1)) screen.lines.push(BOOT[bootIdx++]);
  ctx.font = '400 32px "JetBrains Mono", monospace'; ctx.fillStyle = '#c9f7d2';
  const lines = [...screen.lines];
  if (bootIdx >= BOOT.length) {
    const cursor = Math.floor(now / 500) % 2 ? '█' : ' ';
    lines.push(`debian@pocketbeagle2:~$ ${screen.typed}${cursor}`);
  }
  const visible = lines.slice(-13);
  visible.forEach((l, i) => {
    ctx.fillStyle = l.startsWith('debian@') ? screen.accent : '#bfeec9';
    ctx.fillText(l.slice(0, 74), 16, 96 + i * 42);
  });
  screen.tex.needsUpdate = true;
}
function typeKey(label) {
  if (bootIdx < BOOT.length) return;
  if (label === 'ENT') {
    const cmd = screen.typed.trim();
    screen.lines.push(`debian@pocketbeagle2:~$ ${screen.typed}`);
    if (cmd === 'neofetch' || cmd === 'uname') screen.lines.push('Linux pocketbeagle2 6.12.0-bone #1 SMP aarch64 GNU/Linux');
    else if (cmd === 'clear') screen.lines = [];
    else if (cmd) screen.lines.push(`-bash: ${cmd}: hello from the bancouver40`);
    screen.typed = '';
  } else if (label === 'BSP') screen.typed = screen.typed.slice(0, -1);
  else if (label === 'SPC') screen.typed += ' ';
  else if (label.length === 1) screen.typed += label.toLowerCase();
}

// FPC: leaves the panel's east end, folds 180 deg (r ~6) down and returns under the panel into J3
(() => {
  const w = 20.5, yc = 94.175, x1 = 147.0, xJ = 138.5, zTop = 19.6, zBot = 7.4, r = (zTop - zBot) / 2;
  const pts = [new THREE.Vector2(x1 - 1, zTop), new THREE.Vector2(x1 + 1, zTop)];
  for (let i = 1; i < 24; i++) {
    const a = Math.PI / 2 - (Math.PI * i) / 24;
    pts.push(new THREE.Vector2(x1 + 1 + r * Math.cos(a), zBot + r + r * Math.sin(a)));
  }
  pts.push(new THREE.Vector2(x1 + 1, zBot), new THREE.Vector2(xJ, zBot));
  const pos = [], idx = [];
  pts.forEach((p, i) => {
    pos.push(...C(p.x, yc - w / 2, p.y).toArray(), ...C(p.x, yc + w / 2, p.y).toArray());
    if (i) idx.push(2 * i - 2, 2 * i - 1, 2 * i, 2 * i - 1, 2 * i + 1, 2 * i);
  });
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setIndex(idx); geo.computeVertexNormals();
  parts.panelG.add(new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: 0xc8892a, roughness: 0.45, metalness: 0.3, side: THREE.DoubleSide })));
})();

// J3 FPC connector body (Amphenol F32Q): case x 134.755-141.505, y 80.0-108.355, z 6.1-8.1
(() => {
  const j3 = new THREE.Mesh(new THREE.BoxGeometry(6.75, 2.0, 28.35),
    new THREE.MeshStandardMaterial({ color: 0xf1ede3, roughness: 0.6 }));
  j3.position.copy(C(138.13, 94.18, 7.1));
  const act = new THREE.Mesh(new THREE.BoxGeometry(1.4, 2.1, 28.4), new THREE.MeshStandardMaterial({ color: 0x1b1b1b, roughness: 0.5 }));
  act.position.copy(C(141.0, 94.18, 7.15));
  parts.hwG.add(j3, act);
})();

// M2x15 brass hex standoffs
const brass = new THREE.MeshStandardMaterial({ color: 0xd4a94a, metalness: 1, roughness: 0.32 });
[[16.225, 114.975], [164.225, 114.975], [164.225, 76.475]].forEach(([x, y]) => {
  const s = new THREE.Mesh(new THREE.CylinderGeometry(2.0, 2.0, 15, 6), brass);
  s.position.copy(C(x, y, 6.1 + 7.5));
  parts.hwG.add(s);
});

// ---------------------------------------------------------------------------------------------- keys
// 4 x 10 at 17 mm, bottom-left key centre (11.095, 11.105); Kailh Choc v1 + CFX 16.5 mm low-profile caps
const LEGENDS = [
  ['ESC', 'TAB', 'CTL', 'ALT', 'SPC', 'SPC', 'BSP', 'ENT', 'FN', '↑'],
  ['Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/'],
  ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';'],
  ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
];
const capGeo = new RoundedBoxGeometry(16.5, 3.6, 16.5, 3, 1.3);
const capMat = new THREE.MeshPhysicalMaterial({ color: 0xc9c5bb, roughness: 0.6, clearcoat: 0.1 });
const capAccent = new THREE.MeshPhysicalMaterial({ color: 0x1d1f22, roughness: 0.5, clearcoat: 0.2 });
const swBottom = new THREE.BoxGeometry(13.8, 2.2, 13.8), swTop = new THREE.BoxGeometry(15, 2.8, 15), swStem = new THREE.BoxGeometry(10, 0.9, 4.5);
const swMat = new THREE.MeshStandardMaterial({ color: 0x2a2b2e, roughness: 0.6 });
const stemMat = new THREE.MeshStandardMaterial({ color: 0xc23b2e, roughness: 0.5 });
const keys = new Map();
function legendTexture(text, dark) {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d');
  g.fillStyle = dark ? '#e9e5da' : '#26282c';
  g.font = `700 ${text.length > 1 ? 34 : 52}px "JetBrains Mono", monospace`;
  g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText(text, 64, 66);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  return t;
}
for (let j = 0; j < 4; j++) {
  for (let i = 0; i < 10; i++) {
    const x = 11.095 + 17 * i, y = 11.105 + 17 * j, label = LEGENDS[j][i];
    const sw = new THREE.Group();
    const b = new THREE.Mesh(swBottom, swMat); b.position.copy(C(x, y, 6.1 + 1.1));
    const t = new THREE.Mesh(swTop, swMat); t.position.copy(C(x, y, 8.3 + 1.4));
    sw.add(b, t);
    parts.switchG.add(sw);
    const cap = new THREE.Group();
    const dark = j === 0 && (label === 'ESC' || label === 'ENT');
    const body = new THREE.Mesh(capGeo, dark ? capAccent : capMat); body.position.copy(C(x, y, 12 + 1.8));
    const stem = new THREE.Mesh(swStem, stemMat); stem.position.copy(C(x, y, 11.1 + 0.45));
    const leg = new THREE.Mesh(new THREE.PlaneGeometry(11, 11),
      new THREE.MeshBasicMaterial({ map: legendTexture(label, dark), transparent: true }));
    leg.rotation.x = -Math.PI / 2; leg.position.copy(C(x, y, 15.62));
    cap.add(body, stem, leg);
    cap.userData = { label, press: 0 };
    parts.capG.add(cap);
    keys.set(`${i},${j}`, cap);
  }
}
const KEYMAP = {};
LEGENDS.forEach((row, j) => row.forEach((l, i) => { if (l.length === 1) KEYMAP[l.toLowerCase()] = `${i},${j}`; }));
Object.assign(KEYMAP, { escape: '0,0', tab: '1,0', control: '2,0', alt: '3,0', ' ': '4,0', backspace: '6,0', enter: '7,0', arrowup: '9,0' });
function press(cap) { cap.userData.press = 1; typeKey(cap.userData.label); }
window.addEventListener('keydown', (e) => {
  const k = KEYMAP[e.key.toLowerCase()];
  if (!k) return;
  if (e.key === ' ' || e.key === 'Tab' || e.key === 'Backspace') e.preventDefault();
  if (e.key === ' ') { press(keys.get('4,0')); keys.get('5,0').userData.press = 1; return; }
  press(keys.get(k));
});

// click a key to press it
const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
renderer.domElement.addEventListener('pointerdown', (e) => {
  const r = renderer.domElement.getBoundingClientRect();
  mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const hit = ray.intersectObjects(parts.capG.children, true)[0];
  if (hit) { let o = hit.object; while (o.parent !== parts.capG) o = o.parent; press(o); }
});

// ---------------------------------------------------------------------------------------------- scale references
// Poker deck 63.5 x 88.9 mm, ~16 mm for 54 cards; BIC Round Stic 150 mm long, 8 mm barrel (bicgraphic.com spec).
const scaleG = new THREE.Group();
scene.add(scaleG);
(() => {
  // --- deck of cards: face-up ace of spades on top, striped card edges on the sides
  const top = document.createElement('canvas'); top.width = 508; top.height = 711;
  const g = top.getContext('2d');
  g.fillStyle = '#fbfaf6'; g.fillRect(0, 0, 508, 711);
  g.strokeStyle = '#d8d4c8'; g.lineWidth = 6; g.strokeRect(14, 14, 480, 683);
  g.fillStyle = '#111';
  g.font = '700 70px Georgia, serif'; g.textAlign = 'center';
  g.fillText('A', 52, 92); g.font = '56px Georgia, serif'; g.fillText('♠', 52, 150);
  g.save(); g.translate(456, 619); g.rotate(Math.PI); g.font = '700 70px Georgia, serif'; g.fillText('A', 0, 0);
  g.font = '56px Georgia, serif'; g.fillText('♠', 0, 58); g.restore();
  g.font = '300px Georgia, serif'; g.textBaseline = 'middle'; g.fillText('♠', 254, 370);
  const topTex = new THREE.CanvasTexture(top); topTex.colorSpace = THREE.SRGBColorSpace; topTex.anisotropy = 8;
  const edge = document.createElement('canvas'); edge.width = 8; edge.height = 256;
  const e = edge.getContext('2d');
  for (let y = 0; y < 256; y += 4) { e.fillStyle = y % 8 ? '#eeebe2' : '#d9d5ca'; e.fillRect(0, y, 8, 4); }
  const edgeTex = new THREE.CanvasTexture(edge); edgeTex.colorSpace = THREE.SRGBColorSpace;
  const edgeMatC = new THREE.MeshStandardMaterial({ map: edgeTex, color: 0xbdb8ae, roughness: 0.8 });
  const back = new THREE.MeshStandardMaterial({ color: 0x9c1c22, roughness: 0.7 });
  const deck = new THREE.Mesh(new RoundedBoxGeometry(63.5, 16, 88.9, 2, 2.5),
    [edgeMatC, edgeMatC, new THREE.MeshStandardMaterial({ map: topTex, color: 0xbdb8ae, roughness: 0.6 }), back, edgeMatC, edgeMatC]);
  deck.position.copy(C(-58, 112, 8));
  deck.rotation.y = THREE.MathUtils.degToRad(16);
  scaleG.add(deck);

  // --- BIC Round Stic: frosted barrel, blue cap with clip, blue end plug, ink tube, brass/steel tip
  const pen = new THREE.Group();
  const frosted = new THREE.MeshPhysicalMaterial({ color: 0xeef3f6, roughness: 0.45, transmission: 0.7, thickness: 1.2, transparent: true, opacity: 0.85 });
  const blue = new THREE.MeshStandardMaterial({ color: 0x1d3fbf, roughness: 0.4 });
  const steel = new THREE.MeshStandardMaterial({ color: 0xc9c9c9, metalness: 1, roughness: 0.25 });
  const add = (geo, mat, x) => { const m = new THREE.Mesh(geo, mat); m.rotation.z = Math.PI / 2; m.position.x = x; pen.add(m); return m; };
  // the pen lies along +x, writing end at x=0; total 150 mm with the cap on
  add(new THREE.CylinderGeometry(4, 4, 112, 32), frosted, 38 + 56);                 // barrel 38..150 (end plug inside)
  add(new THREE.CylinderGeometry(1.5, 1.5, 120, 16), blue, 26 + 60);               // ink tube
  add(new THREE.CylinderGeometry(3.6, 3.6, 4, 24), blue, 148);                       // end plug
  add(new THREE.CylinderGeometry(4.3, 3.6, 52, 32), blue, 26);                       // cap 0..52
  add(new THREE.CylinderGeometry(4.3, 4.3, 0.6, 32), blue, 51.7);
  const clip = new THREE.Mesh(new THREE.BoxGeometry(34, 1.4, 2.2), blue);
  clip.position.set(30, 4.8, 0); pen.add(clip);
  add(new THREE.ConeGeometry(0.6, 3, 12), steel, 1.0).rotation.z = Math.PI / 2;       // tip (inside the cap)
  pen.position.copy(C(12, -34, 4.3));
  pen.rotation.y = THREE.MathUtils.degToRad(6);
  scaleG.add(pen);
})();

// ---------------------------------------------------------------------------------------------- hotspots
const info = document.getElementById('info');
const HOTSPOTS = [
  ['PocketBeagle 2', C(36, 92.8, 19.5), 'TI AM6254 quad Cortex-A53, 512 MB LPDDR4 — official BeagleBoard 3D model. Sits on its own 8.5 mm sockets over male pins from below the keyboard PCB; USB-C exits the left wall.'],
  ['4.58″ 320×960 display', C(110, 104, 23), 'ST7701S IPS bar panel, RGB565 over VOUT0 (DPI) + 3-wire SPI init. Glued under the bezel inside a locating frame.'],
  ['FPC fold + J3', C(152, 94.2, 12), 'The panel’s 40-pin flex folds 180° under it into an Amphenol F32Q 0.5 mm ZIF connector (F32R if your tail has bottom contacts).'],
  ['Backlight boost', C(165, 84, 8), 'TPS61165: 5 V → ~12 V for 2×4 white LEDs at 39 mA (0.2 V / 5.1 Ω), PWM-dimmed from P2.01.'],
  ['ATmega32U4', C(39.4, 50.8, 4), 'The original bancouver40 controller (QMK/Vial). Its USB-C is gone: D+/D− run to the PocketBeagle’s USB1 host port.'],
  ['Kailh Choc + CFX caps', C(75, 28, 17), '40 low-profile switches, hot-swap sockets on the PCB, 16.5 mm CFX caps on a 17 mm grid. Try typing.'],
  ['For scale: poker deck', C(-58, 112, 17), 'A standard 63.5 × 88.9 mm poker deck next to the keyboard.'],
  ['For scale: BIC Round Stic', C(70, -38, 9), 'A 150 mm BIC Round Stic ballpoint (8 mm barrel).'],
  ['Neon case', C(4, 30, 13), '3D-printed translucent shell: 12.5 mm keyboard deck stepping up to a 22.6 mm display deck. 3 × M2×15 standoffs clamp PCB, case and bezel.'],
];
const spotObjs = HOTSPOTS.map(([title, pos, text]) => {
  const el = document.createElement('div');
  el.className = 'hotspot';
  el.innerHTML = `<i></i><span>${title}</span>`;
  el.addEventListener('mouseenter', () => { info.querySelector('h4').textContent = title; info.querySelector('p').textContent = text; info.classList.add('show'); });
  el.addEventListener('mouseleave', () => info.classList.remove('show'));
  const o = new CSS2DObject(el); o.position.copy(pos); o.userData.base = pos.clone();
  o.visible = false; el.style.display = 'none';   // labels start hidden
  scene.add(o);
  return o;
});

// ---------------------------------------------------------------------------------------------- UI
const sw = document.getElementById('swatches');
COLORS.forEach(([name, hex], i) => {
  const b = document.createElement('button');
  b.title = name; b.style.setProperty('--c', hex);
  if (!i) b.classList.add('on');
  b.onclick = () => { sw.querySelectorAll('button').forEach((x) => x.classList.remove('on')); b.classList.add('on'); setCaseColor(hex); };
  sw.appendChild(b);
});
document.getElementById('opacity').oninput = (e) => {
  const v = +e.target.value;
  shellMat.opacity = v * 0.64; shellMat.transmission = 1 - v * 0.6;
};
document.getElementById('glow').oninput = (e) => {
  const v = +e.target.value;
  bloom.strength = 0.55 * v; shellMat.emissiveIntensity = 0.06 * v; edgeMat.opacity = Math.min(1, 0.5 + 0.4 * v);
};

const state = { explode: 0, explodeTarget: 0, spin: false };
document.querySelectorAll('[data-toggle]').forEach((b) => b.addEventListener('click', () => {
  b.classList.toggle('on');
  const on = b.classList.contains('on');
  switch (b.dataset.toggle) {
    case 'explode': state.explodeTarget = on ? 1 : 0; break;
    case 'bezel': parts.bezelG.visible = on; break;
    case 'caps': parts.capG.visible = on; break;
    case 'case': parts.caseG.visible = on; break;
    case 'labels': spotObjs.forEach((o) => { o.visible = on; o.element.style.display = on ? '' : 'none'; }); break;
    case 'scale': scaleG.visible = on; break;
    case 'spin': state.spin = on; controls.autoRotate = on; controls.autoRotateSpeed = 0.8; break;
  }
}));
const VIEWS = {
  hero: new THREE.Vector3(-110, 250, 330), top: new THREE.Vector3(0.01, 420, 0.01),
  side: new THREE.Vector3(0, 70, 360), back: new THREE.Vector3(-330, 90, -60),
};
let camTween = null;
document.querySelectorAll('[data-view]').forEach((b) => b.addEventListener('click', () => {
  camTween = { from: camera.position.clone(), to: CENTER.clone().add(VIEWS[b.dataset.view]), t: 0 };
}));

// ---------------------------------------------------------------------------------------------- loop
function resize() {
  const w = host.clientWidth, h = host.clientHeight;
  renderer.setSize(w, h); composer.setSize(w, h); labels.setSize(w, h);
  bloom.resolution.set(w, h);
  camera.aspect = w / h;
  if (w > 900) camera.setViewOffset(w, h, -w * 0.07, 0, w, h); else camera.clearViewOffset();
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
resize();

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
renderer.setAnimationLoop((now) => {
  state.explode += (state.explodeTarget - state.explode) * 0.08;
  for (const [k, g] of Object.entries(parts)) g.position.y = EXPLODE[k] * state.explode;
  spotObjs.forEach((o, i) => {
    const lift = [EXPLODE.pb2G, EXPLODE.panelG, EXPLODE.hwG, EXPLODE.pcbG, EXPLODE.pcbG, EXPLODE.capG, 0, 0, 0][i];
    o.position.y = o.userData.base.y + lift * state.explode;
  });
  for (const cap of parts.capG.children) {
    const p = cap.userData.press;
    cap.position.y = -3 * p;               // 3 mm travel
    cap.userData.press = Math.max(0, p - 0.08);
  }
  if (camTween) {
    camTween.t = Math.min(1, camTween.t + 0.025);
    camera.position.lerpVectors(camTween.from, camTween.to, ease(camTween.t));
    if (camTween.t >= 1) camTween = null;
  }
  drawScreen(now);
  controls.update();
  composer.render();
  labels.render(scene, camera);
});
