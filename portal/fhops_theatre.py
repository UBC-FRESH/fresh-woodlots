"""Tree-scale machine theatre for one FHOPS block."""

from __future__ import annotations

import html

THEATRE_CSS = """<style>
  :root { color-scheme: dark; --ink: #e2e8f0; --muted: #94a3b8;
           --line: rgba(148, 163, 184, .22);
           --panel: #08121c; --accent: #f97316; }
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; }
  body { background: #050b12; color: var(--ink);
         font: 15px/1.45 system-ui, -apple-system, Segoe UI, sans-serif;
         overflow: hidden; }
  #theatre-canvas { position: fixed; inset: 0; z-index: 0;
                    width: 100%; height: 100%; display: block;
                    background: #050b12; }
  .theatre-head { position: fixed; z-index: 5; top: 1rem; left: 1rem;
                  right: 1rem; display: flex; justify-content: space-between;
                  gap: 1rem; align-items: flex-start; pointer-events: none; }
  .theatre-title { background: var(--panel); border: 1px solid var(--line);
                   border-radius: 14px; padding: .75rem 1rem;
                   pointer-events: auto; }
  .theatre-kicker { margin: 0 0 .2rem; color: var(--accent);
                    font-size: .7rem; font-weight: 800; letter-spacing: .12em;
                    text-transform: uppercase; }
  .theatre-title h1 { margin: 0; font-size: clamp(1.1rem, 2.2vw, 1.6rem); }
  .theatre-title p { margin: .2rem 0 0; color: var(--muted); font-size: .82rem; }
  .theatre-actions { display: flex; gap: .5rem; flex-wrap: wrap;
                     justify-content: flex-end; pointer-events: auto; }
  .theatre-actions a, .theatre-actions select { border: 1px solid var(--line);
      background: var(--panel); color: var(--ink); border-radius: 10px;
      padding: .55rem .8rem; text-decoration: none; font: inherit;
      font-weight: 700; cursor: pointer; }
  .theatre-actions a:hover { border-color: #64748b; }
  .theatre-panel { position: fixed; z-index: 5; left: 1rem; right: 1rem;
                   bottom: 1rem; background: var(--panel);
                   border: 1px solid var(--line); border-radius: 16px;
                   padding: .85rem 1rem; }
  .theatre-controls { display: flex; align-items: center; gap: .65rem;
                      flex-wrap: wrap; }
  .theatre-controls button, .theatre-controls select {
      border: 1px solid var(--line); background: rgba(15, 23, 42, .9);
      color: var(--ink); border-radius: 9px; padding: .45rem .7rem;
      font: inherit; cursor: pointer; }
  .theatre-controls button.primary { background: var(--accent);
      border-color: var(--accent); color: #111827; font-weight: 800; }
  .theatre-hud { display: flex; gap: 1rem; flex-wrap: wrap; margin-top: .55rem;
                 color: var(--muted); font-size: .8rem; }
  .theatre-hud strong { color: var(--ink); }
  .theatre-legend { position: fixed; z-index: 4; right: 1rem; bottom: 8.2rem;
                    background: var(--panel); border: 1px solid var(--line);
                    border-radius: 12px; padding: .65rem .8rem;
                    font-size: .76rem; }
  .theatre-legend div { display: flex; align-items: center; gap: .4rem;
                        margin: .25rem 0; }
  .swatch { width: .7rem; height: .7rem; border-radius: 2px;
            display: inline-block; }
  .theatre-note { margin: .45rem 0 0; color: var(--muted); font-size: .7rem; }
  #theatre-loading { position: fixed; inset: 0; z-index: 10; display: flex;
      align-items: center; justify-content: center; background: #050b12;
      color: var(--muted); font: 600 1rem system-ui, sans-serif; }
  #theatre-loading[hidden] { display: none; }
  @media (max-width: 760px) {
    .theatre-head { flex-direction: column; }
    .theatre-actions { justify-content: flex-start; }
    .theatre-legend { display: none; }
  }
</style>"""

THEATRE_JS = """<script type="importmap">
{
  "imports": {
    "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
    "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
  }
}
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const SLUG = '__SLUG__';
const $ = (id) => document.getElementById(id);
const canvas = $('theatre-canvas');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.15;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0c1b18);
scene.fog = new THREE.Fog(0x0c1b18, 220, 700);

const camera = new THREE.PerspectiveCamera(
  52, window.innerWidth / window.innerHeight, 0.1, 1200
);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.maxPolarAngle = Math.PI * 0.48;
controls.minDistance = 8;
controls.maxDistance = 900;

scene.add(new THREE.HemisphereLight(0xbfd7ff, 0x1b2a20, 1.0));
const sun = new THREE.DirectionalLight(0xffe2b8, 2.2);
sun.position.set(180, 260, 140);
scene.add(sun);
const fill = new THREE.DirectionalLight(0x7dd3fc, 0.65);
fill.position.set(-160, 90, -180);
scene.add(fill);

const state = {
  block: null,
  trees: [],
  trunk: null,
  crown: null,
  logs: null,
  stumps: null,
  feller: null,
  skidder: null,
  processor: null,
  felled: 0,
  skidded: 0,
  processed: 0,
  deck: 0,
  simTime: 0,
  playing: true,
  speed: 2,
  fellInterval: 0.16,
  nextSkid: 0,
  nextProcess: 0,
  falling: [],
  lastStats: 0,
};
const clock = new THREE.Clock();
const dummy = new THREE.Object3D();
const palette = {
  Fd: new THREE.Color('#2f7d4a'),
  Cw: new THREE.Color('#1f6f4a'),
  Hw: new THREE.Color('#3c8f5a'),
  Pl: new THREE.Color('#4d8f5e'),
};

function labelSprite(text, color) {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 64;
  const context = canvas.getContext('2d');
  context.fillStyle = 'rgba(8,18,28,0.9)';
  context.roundRect(4, 4, 248, 56, 12);
  context.fill();
  context.strokeStyle = color;
  context.lineWidth = 3;
  context.stroke();
  context.fillStyle = '#f8fafc';
  context.font = '700 26px system-ui, sans-serif';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText(text, 128, 32);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: texture, depthTest: false })
  );
  sprite.scale.set(26, 6.5, 1);
  return sprite;
}

function machine(color, name) {
  const group = new THREE.Group();
  const body = new THREE.Mesh(
    new THREE.BoxGeometry(4.2, 2.1, 2.6),
    new THREE.MeshStandardMaterial({ color, roughness: 0.6 })
  );
  body.position.y = 1.3;
  group.add(body);
  const cab = new THREE.Mesh(
    new THREE.BoxGeometry(1.8, 1.7, 2.0),
    new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.4 })
  );
  cab.position.set(-0.8, 2.9, 0);
  group.add(cab);
  const boom = new THREE.Mesh(
    new THREE.BoxGeometry(0.45, 0.45, 4.2),
    new THREE.MeshStandardMaterial({ color: 0xfacc15, roughness: 0.5 })
  );
  boom.position.set(1.6, 2.8, 0);
  boom.rotation.x = -0.55;
  group.add(boom);
  const head = new THREE.Mesh(
    new THREE.CylinderGeometry(0.55, 0.55, 0.8, 10),
    new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.4 })
  );
  head.position.set(1.6, 1.4, 2.0);
  group.add(head);
  const label = labelSprite(name, '#f97316');
  label.position.set(0, 6.5, 0);
  group.add(label);
  return group;
}

function buildGround(block) {
  const ring = block.rings[0];
  const shape = new THREE.Shape();
  ring.forEach(([x, z], index) => {
    if (index === 0) shape.moveTo(x, z);
    else shape.lineTo(x, z);
  });
  shape.closePath();
  const geometry = new THREE.ShapeGeometry(shape);
  geometry.rotateX(Math.PI / 2);
  const mesh = new THREE.Mesh(
    geometry,
    new THREE.MeshStandardMaterial({
      color: 0x173a2a, roughness: 1, metalness: 0,
      polygonOffset: true, polygonOffsetFactor: 1,
    })
  );
  mesh.position.y = 0.03;
  scene.add(mesh);

  const points = ring.map(([x, z]) => new THREE.Vector3(x, 0.12, z));
  const line = new THREE.LineLoop(
    new THREE.BufferGeometry().setFromPoints(points),
    new THREE.LineBasicMaterial({ color: 0x7dd3fc, transparent: true, opacity: 0.6 })
  );
  scene.add(line);

  const landing = block.landing;
  const deckLabel = labelSprite('Unprocessed deck', '#b45309');
  deckLabel.position.set(landing[0] - 22, 7, landing[1] - 8);
  scene.add(deckLabel);
  const logLabel = labelSprite('Processed logs', '#d6a45c');
  logLabel.position.set(landing[0] - 12, 7, landing[1] + 12);
  scene.add(logLabel);
  const pad = new THREE.Mesh(
    new THREE.CircleGeometry(11, 32),
    new THREE.MeshStandardMaterial({ color: 0x5b3a24, roughness: 1 })
  );
  pad.rotation.x = -Math.PI / 2;
  pad.position.set(landing[0], 0.08, landing[1]);
  scene.add(pad);
}

function buildTrees(block) {
  const count = block.trees.length;
  const trunkGeo = new THREE.CylinderGeometry(0.18, 0.3, 1, 5);
  trunkGeo.translate(0, 0.5, 0);
  const crownGeo = new THREE.ConeGeometry(1, 1, 7);
  crownGeo.translate(0, 0.5, 0);
  const trunk = new THREE.InstancedMesh(
    trunkGeo,
    new THREE.MeshStandardMaterial({ color: 0x7c4a2d, roughness: 0.9 }),
    count
  );
  const crown = new THREE.InstancedMesh(
    crownGeo,
    new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.9 }),
    count
  );
  trunk.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  crown.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  state.trunk = trunk;
  state.crown = crown;
  for (let index = 0; index < count; index += 1) {
    const tree = block.trees[index];
    const color = palette[tree.sp] || palette.Fd;
    crown.setColorAt(index, color);
    setTree(index, 0);
  }
  crown.instanceColor.needsUpdate = true;
  scene.add(trunk, crown);
}

function setTree(index, angle) {
  const tree = state.block.trees[index];
  const direction = tree.dir || { x: 1, z: 0 };
  const axis = new THREE.Vector3(direction.z, 0, -direction.x).normalize();
  const quaternion = new THREE.Quaternion().setFromAxisAngle(axis, angle);
  const trunkMatrix = new THREE.Matrix4().compose(
    new THREE.Vector3(tree.x, 0, tree.z),
    quaternion,
    new THREE.Vector3(1, tree.h, 1)
  );
  state.trunk.setMatrixAt(index, trunkMatrix);
  const crownMatrix = new THREE.Matrix4()
    .makeTranslation(tree.x, 0, tree.z)
    .multiply(new THREE.Matrix4().makeRotationFromQuaternion(quaternion))
    .multiply(new THREE.Matrix4().makeTranslation(0, tree.h * 0.55, 0))
    .multiply(new THREE.Matrix4().makeScale(tree.c, tree.h * 0.45, tree.c));
  state.crown.setMatrixAt(index, crownMatrix);
  state.trunk.instanceMatrix.needsUpdate = true;
  state.crown.instanceMatrix.needsUpdate = true;
}

function buildLogs(block) {
  const count = block.trees.length * 3;
  const geometry = new THREE.CylinderGeometry(0.28, 0.34, 1, 6);
  geometry.rotateZ(Math.PI / 2);
  const logs = new THREE.InstancedMesh(
    geometry,
    new THREE.MeshStandardMaterial({ color: 0xb45309, roughness: 0.9 }),
    count
  );
  logs.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  for (let index = 0; index < count; index += 1) {
    dummy.position.set(0, -10, 0);
    dummy.scale.set(0, 0, 0);
    dummy.updateMatrix();
    logs.setMatrixAt(index, dummy.matrix);
  }
  scene.add(logs);
  state.logs = logs;

  const deck = new THREE.InstancedMesh(
    geometry.clone(),
    new THREE.MeshStandardMaterial({ color: 0x8b5a2b, roughness: 0.9 }),
    count
  );
  deck.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  for (let index = 0; index < count; index += 1) {
    dummy.position.set(0, -10, 0);
    dummy.scale.set(0, 0, 0);
    dummy.updateMatrix();
    deck.setMatrixAt(index, dummy.matrix);
  }
  scene.add(deck);
  state.deckMesh = deck;
}

function buildStumps(block) {
  const count = block.trees.length;
  const geometry = new THREE.CylinderGeometry(0.36, 0.42, 0.6, 6);
  const stumps = new THREE.InstancedMesh(
    geometry,
    new THREE.MeshStandardMaterial({ color: 0x5b3a24, roughness: 1 }),
    count
  );
  for (let index = 0; index < count; index += 1) {
    dummy.position.set(0, -10, 0);
    dummy.scale.set(0, 0, 0);
    dummy.updateMatrix();
    stumps.setMatrixAt(index, dummy.matrix);
  }
  scene.add(stumps);
  state.stumps = stumps;
}

function buildMachines(block) {
  state.feller = machine(0xf59e0b, 'Feller-buncher');
  state.skidder = machine(0x38bdf8, 'Grapple skidder');
  state.processor = machine(0x34d399, 'Processor');
  const landing = block.landing;
  state.processor.position.set(landing[0] - 12, 0, landing[1] + 8);
  state.skidder.position.set(landing[0] + 4, 0, landing[1] + 4);
  state.feller.position.set(block.trees[0].x, 0, block.trees[0].z);
  for (const item of [state.feller, state.skidder, state.processor]) {
    scene.add(item);
  }
  const pile = new THREE.Mesh(
    new THREE.BoxGeometry(8, 1.2, 8),
    new THREE.MeshStandardMaterial({ color: 0x3f2a1a, roughness: 1 })
  );
  pile.position.set(landing[0] - 12, 0.6, landing[1] + 12);
  scene.add(pile);
}

function prepareTrees(block) {
  const row = 22;
  block.trees.sort((left, right) => {
    const rowLeft = Math.floor((left.z + 10000) / row);
    const rowRight = Math.floor((right.z + 10000) / row);
    if (rowLeft !== rowRight) return rowLeft - rowRight;
    return rowLeft % 2
      ? right.x - left.x
      : left.x - right.x;
  });
  for (let index = 0; index < block.trees.length; index += 1) {
    const tree = block.trees[index];
    const angle = Math.atan2(tree.z, tree.x);
    tree.dir = { x: Math.cos(angle), z: Math.sin(angle) };
  }
}

function updateLogPile(delivered) {
  if (!state.logs) return;
  const landing = state.block.landing;
  const logsPerStem = 3;
  const total = Math.min(delivered * logsPerStem, state.logs.count);
  for (let index = 0; index < total; index += 1) {
    const row = Math.floor(index / 9);
    const column = index % 9;
    dummy.position.set(
      landing[0] - 16 + (column % 3) * 2.6,
      0.5 + row * 0.65,
      landing[1] + 10 + Math.floor(column / 3) * 2.6
    );
    dummy.rotation.set(0, 0.2 * (index % 4), 0);
    dummy.scale.set(3.2 + (index % 3), 1, 1);
    dummy.updateMatrix();
    state.logs.setMatrixAt(index, dummy.matrix);
  }
  state.logs.instanceMatrix.needsUpdate = true;
}

function updateDeck(count) {
  if (!state.deckMesh) return;
  const landing = state.block.landing;
  for (let index = 0; index < state.deckMesh.count; index += 1) {
    if (index >= count) {
      dummy.position.set(0, -10, 0);
      dummy.scale.set(0, 0, 0);
    } else {
      const row = Math.floor(index / 6);
      const column = index % 6;
      dummy.position.set(
        landing[0] - 26 + column * 3.2,
        0.45 + row * 0.55,
        landing[1] - 8 + row * 2.4
      );
      dummy.rotation.set(Math.PI / 2, 0.08 * index, 0);
      dummy.scale.set(1, 5.5, 1);
    }
    dummy.updateMatrix();
    state.deckMesh.setMatrixAt(index, dummy.matrix);
  }
  state.deckMesh.instanceMatrix.needsUpdate = true;
}

function hideTree(index) {
  const hidden = new THREE.Matrix4().makeScale(0, 0, 0);
  state.trunk.setMatrixAt(index, hidden);
  state.crown.setMatrixAt(index, hidden);
  state.trunk.instanceMatrix.needsUpdate = true;
  state.crown.instanceMatrix.needsUpdate = true;
}

function setStump(index) {
  const tree = state.block.trees[index];
  dummy.position.set(tree.x, 0.3, tree.z);
  dummy.rotation.set(0, 0, 0);
  dummy.scale.set(1, 1, 1);
  dummy.updateMatrix();
  state.stumps.setMatrixAt(index, dummy.matrix);
  state.stumps.instanceMatrix.needsUpdate = true;
}

function startFall(index) {
  const tree = state.block.trees[index];
  state.falling.push({ index, angle: 0, done: false });
  setStump(index);
  const direction = tree.dir || { x: 1, z: 0 };
  state.feller.userData.target = new THREE.Vector3(tree.x, 0, tree.z);
}

function updateAnimation(delta) {
  if (!state.block) return;
  if (state.playing) state.simTime += delta * state.speed;
  const total = state.block.trees.length;
  const target = Math.min(total, Math.floor(state.simTime / state.fellInterval));
  while (state.felled < target) {
    startFall(state.felled);
    state.felled += 1;
  }
  for (const fall of state.falling) {
    if (fall.done) continue;
    fall.angle = Math.min(Math.PI / 2, fall.angle + delta * state.speed * 3.2);
    setTree(fall.index, fall.angle);
    if (fall.angle >= Math.PI / 2) fall.done = true;
  }
  const skidTarget = Math.floor(state.felled / 6) * 6;
  if (skidTarget > state.skidded && state.simTime >= state.nextSkid) {
    while (state.skidded < skidTarget) {
      hideTree(state.skidded);
      state.skidded += 1;
    }
    state.deck += 6;
    state.nextSkid = state.simTime + 1.4;
    updateDeck(state.deck);
  }
  if (state.deck > 0 && state.simTime >= state.nextProcess) {
    state.deck -= 1;
    state.processed += 1;
    state.nextProcess = state.simTime + 0.55;
    updateDeck(state.deck);
    updateLogPile(state.processed * 3);
  }
  const current = Math.min(state.felled, total - 1);
  const tree = state.block.trees[current];
  if (tree && state.feller) {
    state.feller.position.lerp(
      new THREE.Vector3(tree.x, 0, tree.z), Math.min(1, delta * 3.2)
    );
  }
  if (state.skidder) {
    const landing = state.block.landing;
    const phase = (state.simTime * 0.65) % 2;
    const toTree = phase < 1;
    const source = toTree
      ? new THREE.Vector3(landing[0] + 4, 0, landing[1] + 4)
      : new THREE.Vector3(tree.x, 0, tree.z);
    const goal = toTree
      ? new THREE.Vector3(tree.x, 0, tree.z)
      : new THREE.Vector3(landing[0] + 4, 0, landing[1] + 4);
    const t = toTree ? phase : 2 - phase;
    state.skidder.position.lerpVectors(source, goal, t);
  }
  if (state.processor) {
    state.processor.rotation.y = Math.sin(state.simTime * 2.4) * 0.25;
  }
  const phaseLabel = state.processed >= total
    ? 'Complete'
    : state.deck > 0 ? 'Felling / skidding / processing' : 'Felling';
  $('phase-label').textContent = phaseLabel;
  $('felled-label').textContent = state.felled + ' / ' + total + ' trees felled';
  $('ground-label').textContent =
    Math.max(0, state.felled - state.skidded) + ' on ground';
  $('delivered-label').textContent = state.deck + ' stems on deck';
  $('logs-label').textContent = state.processed * 3 + ' logs processed';
  if (state.felled >= total && state.playing) {
    state.playing = false;
    $('play-button').textContent = '▶ Play';
  }
}

function resetAnimation() {
  state.simTime = 0;
  state.felled = 0;
  state.skidded = 0;
  state.processed = 0;
  state.deck = 0;
  state.nextSkid = 0;
  state.nextProcess = 0;
  state.falling = [];
  state.playing = true;
  $('play-button').textContent = '❚❚ Pause';
  for (let index = 0; index < state.block.trees.length; index += 1) {
    setTree(index, 0);
    state.stumps.setMatrixAt(index, new THREE.Matrix4().makeScale(0, 0, 0));
    for (let log = 0; log < 3; log += 1) {
      const logIndex = index * 3 + log;
      if (logIndex < state.logs.count) {
        dummy.position.set(0, -10, 0);
        dummy.scale.set(0, 0, 0);
        dummy.updateMatrix();
        state.logs.setMatrixAt(logIndex, dummy.matrix);
      }
    }
  }
  state.stumps.instanceMatrix.needsUpdate = true;
  state.logs.instanceMatrix.needsUpdate = true;
  updateLogPile(0);
  updateDeck(0);
}

function buildBlock(block) {
  state.block = block;
  window.__theatre = { camera, controls, state, scene };
  const extent = block.rings[0].reduce(
    (value, point) => Math.max(value, Math.abs(point[0]), Math.abs(point[1])),
    0
  );
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(extent * 12, extent * 12),
    new THREE.MeshStandardMaterial({ color: 0x0b1d16, roughness: 1 })
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.15;
  scene.add(ground);
  window.__theatre = { camera, controls, state, scene };
  prepareTrees(block);
  buildGround(block);
  buildTrees(block);
  buildLogs(block);
  buildStumps(block);
  buildMachines(block);
  const distance = Math.max(60, extent * 0.55);
  camera.position.set(distance * 0.55, distance * 0.65, distance * 0.55);
  controls.target.set(0, 8, 0);
  controls.maxDistance = Math.max(140, distance * 2.8);
  controls.update();
  $('block-label').textContent = block.label;
  $('area-label').textContent = block.area_ha.toFixed(1) + ' ha';
  $('theatre-loading').hidden = true;
}

function animate() {
  requestAnimationFrame(animate);
  const delta = Math.min(clock.getDelta(), 0.05);
  updateAnimation(delta);
  controls.update();
  renderer.render(scene, camera);
}

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

$('play-button').addEventListener('click', () => {
  state.playing = !state.playing;
  $('play-button').textContent = state.playing ? '❚❚ Pause' : '▶ Play';
});
$('restart-button').addEventListener('click', resetAnimation);
$('speed-select').addEventListener('change', (event) => {
  state.speed = Number(event.target.value) || 2;
});
$('orbit-button').addEventListener('click', () => {
  controls.autoRotate = !controls.autoRotate;
  controls.autoRotateSpeed = 0.7;
  $('orbit-button').textContent = controls.autoRotate
    ? 'Stop orbit' : 'Orbit';
});

fetch('/fhops/' + SLUG + '/theatre.json')
  .then((response) => response.json())
  .then((data) => {
    const select = $('block-select');
    for (const block of data.blocks) {
      const option = document.createElement('option');
      option.value = block.label;
      option.textContent = block.label + ' · ' + block.area_ha.toFixed(1) + ' ha';
      select.appendChild(option);
    }
    const requested = new URLSearchParams(window.location.search).get('block');
    const block = data.blocks.find((item) => item.label === requested)
      || data.blocks[0];
    select.value = block.label;
    select.addEventListener('change', () => {
      const url = new URL(window.location.href);
      url.searchParams.set('block', select.value);
      window.location.href = url.toString();
    });
    buildBlock(block);
    animate();
  })
  .catch(() => {
    $('theatre-loading').textContent = 'Tree-scale theatre data is not available.';
  });
</script>"""


def render_theatre(
    *,
    slug: str,
    label: str,
    file_id: str,
    subtitle: str,
) -> str:
    """Return the full-screen tree-scale theatre page for one FHOPS instance."""
    safe_slug = html.escape(slug)
    safe_label = html.escape(label)
    safe_file_id = html.escape(file_id)
    safe_subtitle = html.escape(subtitle)
    script = THEATRE_JS.replace("__SLUG__", safe_slug)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tree-scale theatre · {safe_label}</title>
  {THEATRE_CSS}
</head>
<body>
  <canvas id="theatre-canvas" aria-label="Tree-scale harvest theatre"></canvas>
  <div id="theatre-loading">Loading trees and machines…</div>
  <header class="theatre-head">
    <div class="theatre-title">
      <p class="theatre-kicker">FHOPS · tree-scale theatre</p>
      <h1>{safe_label}</h1>
      <p>{safe_file_id} · {safe_subtitle} · <span id="block-label">—</span> ·
      <span id="area-label">—</span></p>
    </div>
    <div class="theatre-actions">
      <select id="block-select" aria-label="Choose a block"></select>
      <a href="/fhops/{safe_slug}/studio">3D block studio</a>
      <a href="/fhops/{safe_slug}">FHOPS summary</a>
      <a href="/">All woodlots</a>
    </div>
  </header>
  <aside class="theatre-legend">
    <div><span class="swatch" style="background:#2f7d4a"></span> Standing tree</div>
    <div><span class="swatch" style="background:#b45309"></span> Unprocessed deck</div>
    <div><span class="swatch" style="background:#5b3a24"></span> Processed logs</div>
    <div><span class="swatch" style="background:#f59e0b"></span> Feller-buncher</div>
    <div><span class="swatch" style="background:#38bdf8"></span> Grapple skidder</div>
    <div><span class="swatch" style="background:#34d399"></span> Processor</div>
  </aside>
  <section class="theatre-panel">
    <div class="theatre-controls">
      <button id="play-button" class="primary" type="button">❚❚ Pause</button>
      <button id="restart-button" type="button">Restart</button>
      <button id="orbit-button" type="button">Orbit</button>
      <label for="speed-select">Speed</label>
      <select id="speed-select">
        <option value="1">1×</option>
        <option value="2" selected>2×</option>
        <option value="4">4×</option>
      </select>
      <span id="phase-label">Felling</span>
    </div>
    <div class="theatre-hud">
      <span><strong id="felled-label">0 trees felled</strong></span>
      <span><strong id="ground-label">0 on ground</strong></span>
      <span><strong id="delivered-label">0 stems on deck</strong></span>
      <span><strong id="logs-label">0 logs processed</strong></span>
      <span><strong>Illustrative machine choreography</strong></span>
    </div>
    <p class="theatre-note">Synthetic tree layout inside the real block polygon.
    The machine movements are illustrative, not a FHOPS solve. No ALS terrain
    or step map is included. Drag to orbit, scroll to zoom.</p>
  </section>
  {script}
</body>
</html>"""
