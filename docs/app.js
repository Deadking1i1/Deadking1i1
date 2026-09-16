import * as THREE from "three";

const canvas = document.querySelector("#scene");
const fallback = document.querySelector("#webgl-fallback");
const reducedNote = document.querySelector(".reduced-note");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

let renderer;
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" });
} catch (error) {
  showFallback();
  throw error;
}

if (!renderer.capabilities.isWebGL2 && !renderer.getContext()) showFallback();

renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.15;

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x020303, 0.048);
const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
camera.position.set(0, 0.15, 11.6);

scene.add(new THREE.AmbientLight(0x6c727b, 1.35));
const key = new THREE.DirectionalLight(0xe5e7eb, 4.2);
key.position.set(-3, 5, 6);
scene.add(key);
const crimson = new THREE.PointLight(0xdc143c, 38, 15, 2);
crimson.position.set(0, 0, 2.5);
scene.add(crimson);

const root = new THREE.Group();
scene.add(root);

const globe = buildGlobe();
const crystal = buildCrystal();
root.add(globe.group, crystal.group);

const dustGeometry = new THREE.BufferGeometry();
const dust = new Float32Array(360 * 3);
for (let i = 0; i < dust.length; i += 3) {
  dust[i] = (Math.random() - 0.5) * 18;
  dust[i + 1] = (Math.random() - 0.5) * 10;
  dust[i + 2] = (Math.random() - 0.5) * 8 - 2;
}
dustGeometry.setAttribute("position", new THREE.BufferAttribute(dust, 3));
scene.add(new THREE.Points(dustGeometry, new THREE.PointsMaterial({ color: 0x7d8590, size: 0.018, transparent: true, opacity: 0.28 })));

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2(9, 9);
const parallax = new THREE.Vector2();
const drag = { active: false, target: null, x: 0, y: 0, distance: 0, lastInteraction: 0 };
const touchPoints = new Map();
let pinchDistance = 0;
const velocity = { globe: new THREE.Vector2(), crystal: new THREE.Vector2() };
const pulses = [];
let fragmentImpulse = 0;
let hovered = null;

canvas.addEventListener("pointerdown", onPointerDown);
canvas.addEventListener("pointermove", onPointerMove);
canvas.addEventListener("pointerup", onPointerUp);
canvas.addEventListener("pointercancel", onPointerUp);
canvas.addEventListener("wheel", onWheel, { passive: true });
canvas.addEventListener("keydown", onKeyDown);
window.addEventListener("resize", resize);
reducedMotion.addEventListener?.("change", updateMotionPreference);

resize();
updateMotionPreference();
document.documentElement.dataset.webglReady = "true";
renderer.setAnimationLoop(render);

function buildGlobe() {
  const group = new THREE.Group();
  group.userData.kind = "globe";
  const body = new THREE.Mesh(
    new THREE.SphereGeometry(1.55, 64, 48),
    new THREE.MeshPhysicalMaterial({ color: 0x08090b, roughness: 0.72, metalness: 0.72, clearcoat: 0.28 })
  );
  group.add(body);

  const grid = new THREE.Group();
  const gridMaterial = new THREE.LineBasicMaterial({ color: 0xc0c0c0, transparent: true, opacity: 0.3 });
  [-60, -30, 0, 30, 60].forEach(lat => grid.add(makeLatitude(1.565, lat, gridMaterial)));
  for (let lon = 0; lon < 180; lon += 20) grid.add(makeLongitude(1.565, lon, gridMaterial));
  group.add(grid);

  const coordinates = [
    [35,-10], [48,8], [42,28], [24,35], [5,22], [-21,28], [-34,18],
    [51,-102], [38,-77], [20,-99], [-5,-72], [-24,-58], [-37,-69],
    [36,139], [22,114], [8,78], [-7,112], [-25,133]
  ];
  const nodeMaterial = new THREE.MeshBasicMaterial({ color: 0xff1744 });
  const nodes = new THREE.Group();
  const positions = coordinates.map(([lat, lon]) => latLon(1.59, lat, lon));
  positions.forEach((position, index) => {
    const node = new THREE.Mesh(new THREE.SphereGeometry(index % 4 === 0 ? 0.045 : 0.032, 10, 10), nodeMaterial.clone());
    node.position.copy(position);
    node.userData.kind = "node";
    nodes.add(node);
  });
  const connectionMaterial = new THREE.LineBasicMaterial({ color: 0x8b0000, transparent: true, opacity: 0.72 });
  [[0,1],[1,2],[2,3],[3,4],[4,5],[7,8],[8,9],[9,10],[10,11],[11,12],[14,15],[15,16],[16,17],[1,14],[4,16]].forEach(([a,b]) => {
    nodes.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([positions[a], positions[b]]), connectionMaterial));
  });
  group.add(nodes);

  const orbits = new THREE.Group();
  const orbitA = ringLine(2.08, 0xdc143c, 0.75);
  orbitA.scale.y = 0.32;
  orbitA.rotation.x = 0.34;
  const orbitB = ringLine(2.25, 0x8b0000, 0.65);
  orbitB.scale.y = 0.25;
  orbitB.rotation.set(1.1, 0.18, 0.68);
  const orbitC = ringLine(1.93, 0xff1744, 0.45);
  orbitC.scale.y = 0.42;
  orbitC.rotation.set(-0.45, 0.6, -0.35);
  orbits.add(orbitA, orbitB, orbitC);
  group.add(orbits);

  const glow = new THREE.Mesh(new THREE.SphereGeometry(1.7, 32, 24), new THREE.MeshBasicMaterial({ color: 0x8b0000, transparent: true, opacity: 0.06, side: THREE.BackSide }));
  group.add(glow);
  return { group, body, nodes, orbits, glow };
}

function buildCrystal() {
  const group = new THREE.Group();
  group.userData.kind = "crystal";
  const geometry = new THREE.OctahedronGeometry(1.22, 0);
  geometry.scale(0.72, 2.1, 0.72);
  geometry.rotateY(Math.PI / 4);
  const shell = new THREE.Mesh(geometry, new THREE.MeshPhysicalMaterial({
    color: 0x111318, metalness: 0.58, roughness: 0.2, transmission: 0.28,
    transparent: true, opacity: 0.8, thickness: 0.9, ior: 1.8, side: THREE.DoubleSide
  }));
  shell.userData.kind = "crystal";
  group.add(shell);

  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geometry), new THREE.LineBasicMaterial({ color: 0xd5d9df, transparent: true, opacity: 0.86 }));
  group.add(edges);

  const core = new THREE.Mesh(new THREE.OctahedronGeometry(0.54, 0), new THREE.MeshStandardMaterial({ color: 0x8b0000, emissive: 0xdc143c, emissiveIntensity: 2.4, roughness: 0.28, metalness: 0.25 }));
  core.scale.y = 2;
  group.add(core);
  const aura = new THREE.Mesh(new THREE.OctahedronGeometry(0.72, 0), new THREE.MeshBasicMaterial({ color: 0xff1744, transparent: true, opacity: 0.08, side: THREE.BackSide }));
  aura.scale.y = 2.05;
  group.add(aura);

  const veinMaterial = new THREE.LineBasicMaterial({ color: 0xff1744, transparent: true, opacity: 0.9 });
  const veins = [
    [[0,1.65,.48],[-.22,.7,.58],[.16,.18,.62],[-.3,-.65,.45],[0,-1.7,.18]],
    [[-.48,1.2,.08],[.1,.58,.7],[-.08,-.1,.72],[.34,-.9,.25]],
    [[.5,.85,.1],[.22,.25,.72],[.45,-.42,.22],[.08,-1.15,.5]]
  ];
  veins.forEach(points => group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points.map(p => new THREE.Vector3(...p))), veinMaterial)));

  const fragments = new THREE.Group();
  const fragmentPositions = [[-1.7,1.2,.1],[1.62,.92,-.15],[-1.58,-.85,.2],[1.76,-.72,.08],[-.75,2.15,-.3],[.86,-2.15,.2]];
  fragmentPositions.forEach((position, index) => {
    const fragment = new THREE.Mesh(new THREE.TetrahedronGeometry(0.2 + (index % 3) * 0.045, 0), new THREE.MeshStandardMaterial({ color: index % 2 ? 0x26030b : 0x1a1c20, metalness: 0.78, roughness: 0.22, emissive: 0x8b0000, emissiveIntensity: 0.35 }));
    fragment.position.set(...position);
    fragment.rotation.set(index, index * .7, index * .35);
    fragment.userData.home = fragment.position.clone();
    fragment.userData.phase = index * 0.9;
    fragments.add(fragment);
  });
  group.add(fragments);

  const rings = new THREE.Group();
  const r1 = ringLine(1.86, 0xff1744, 0.72); r1.scale.y = .3; r1.rotation.set(.28,0,.12);
  const r2 = ringLine(2.05, 0x8b0000, 0.62); r2.scale.y = .24; r2.rotation.set(1.02,.32,.7);
  const r3 = ringLine(1.62, 0xdc143c, 0.42); r3.scale.y = .4; r3.rotation.set(-.72,.4,-.42);
  rings.add(r1, r2, r3);
  group.add(rings);
  return { group, shell, core, aura, fragments, rings };
}

function makeLatitude(radius, degrees, material) {
  const latitude = THREE.MathUtils.degToRad(degrees);
  const y = Math.sin(latitude) * radius;
  const ringRadius = Math.cos(latitude) * radius;
  const points = Array.from({ length: 97 }, (_, i) => {
    const a = i / 96 * Math.PI * 2;
    return new THREE.Vector3(Math.cos(a) * ringRadius, y, Math.sin(a) * ringRadius);
  });
  return new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), material);
}

function makeLongitude(radius, degrees, material) {
  const longitude = THREE.MathUtils.degToRad(degrees);
  const points = Array.from({ length: 97 }, (_, i) => {
    const a = i / 96 * Math.PI * 2;
    return new THREE.Vector3(Math.cos(a) * Math.cos(longitude) * radius, Math.sin(a) * radius, Math.cos(a) * Math.sin(longitude) * radius);
  });
  return new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), material);
}

function latLon(radius, latitude, longitude) {
  const phi = THREE.MathUtils.degToRad(90 - latitude);
  const theta = THREE.MathUtils.degToRad(longitude + 180);
  return new THREE.Vector3(-radius * Math.sin(phi) * Math.cos(theta), radius * Math.cos(phi), radius * Math.sin(phi) * Math.sin(theta));
}

function ringLine(radius, color, opacity) {
  const points = Array.from({ length: 129 }, (_, i) => {
    const a = i / 128 * Math.PI * 2;
    return new THREE.Vector3(Math.cos(a) * radius, 0, Math.sin(a) * radius);
  });
  return new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), new THREE.LineBasicMaterial({ color, transparent: true, opacity }));
}

function onPointerDown(event) {
  if (event.pointerType === "touch") {
    touchPoints.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (touchPoints.size === 2) {
      pinchDistance = pointerDistance([...touchPoints.values()]);
      drag.active = false;
      canvas.setPointerCapture(event.pointerId);
      return;
    }
  }
  drag.active = true;
  drag.target = pickTarget(event);
  drag.x = event.clientX;
  drag.y = event.clientY;
  drag.distance = 0;
  drag.lastInteraction = performance.now();
  canvas.setPointerCapture(event.pointerId);
}

function onPointerMove(event) {
  const rect = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  parallax.set(pointer.x, pointer.y);
  if (event.pointerType === "touch" && touchPoints.has(event.pointerId)) {
    touchPoints.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (touchPoints.size >= 2) {
      const distance = pointerDistance([...touchPoints.values()]);
      camera.position.z = THREE.MathUtils.clamp(camera.position.z - (distance - pinchDistance) * .012, 8.7, 14.2);
      pinchDistance = distance;
      drag.lastInteraction = performance.now();
      return;
    }
  }
  if (!drag.active || !drag.target) return;
  const dx = event.clientX - drag.x;
  const dy = event.clientY - drag.y;
  drag.distance += Math.abs(dx) + Math.abs(dy);
  const object = drag.target === "globe" ? globe.group : crystal.group;
  object.rotation.y += dx * 0.007;
  object.rotation.x += dy * 0.0045;
  object.rotation.x = THREE.MathUtils.clamp(object.rotation.x, -0.85, 0.85);
  velocity[drag.target].set(dy * 0.00065, dx * 0.0011);
  drag.x = event.clientX;
  drag.y = event.clientY;
  drag.lastInteraction = performance.now();
  fragmentImpulse = Math.min(1, fragmentImpulse + Math.abs(dx + dy) * .006);
}

function onPointerUp(event) {
  touchPoints.delete(event.pointerId);
  if (!drag.active) return;
  if (drag.distance < 10 && drag.target) createPulse(drag.target);
  drag.active = false;
  drag.lastInteraction = performance.now();
  try { canvas.releasePointerCapture(event.pointerId); } catch { /* pointer already released */ }
}

function onWheel(event) {
  camera.position.z = THREE.MathUtils.clamp(camera.position.z + event.deltaY * .004, 8.7, 14.2);
  drag.lastInteraction = performance.now();
}

function pointerDistance(points) {
  return Math.hypot(points[0].x - points[1].x, points[0].y - points[1].y);
}

function onKeyDown(event) {
  const target = event.shiftKey ? "crystal" : "globe";
  const object = target === "globe" ? globe.group : crystal.group;
  if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Enter", " "].includes(event.key)) event.preventDefault();
  if (event.key === "ArrowLeft") object.rotation.y -= .12;
  if (event.key === "ArrowRight") object.rotation.y += .12;
  if (event.key === "ArrowUp") object.rotation.x -= .1;
  if (event.key === "ArrowDown") object.rotation.x += .1;
  if (event.key === "Enter" || event.key === " ") createPulse(target);
}

function pickTarget(event) {
  const rect = canvas.getBoundingClientRect();
  if (window.innerWidth <= 800) return event.clientY - rect.top < rect.height / 2 ? "globe" : "crystal";
  return event.clientX - rect.left < rect.width / 2 ? "globe" : "crystal";
}

function createPulse(kind) {
  const source = kind === "globe" ? globe.group : crystal.group;
  const geometry = kind === "globe" ? new THREE.SphereGeometry(1.7, 28, 20) : new THREE.OctahedronGeometry(1.35, 0);
  const mesh = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ color: 0xff1744, transparent: true, opacity: .34, wireframe: true }));
  if (kind === "crystal") mesh.scale.y = 2;
  mesh.position.copy(source.position);
  root.add(mesh);
  pulses.push({ mesh, life: 0 });
  fragmentImpulse = 1;
}

function resize() {
  const width = canvas.clientWidth || canvas.parentElement.clientWidth;
  const height = canvas.clientHeight || canvas.parentElement.clientHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  const stacked = width <= 800;
  globe.group.position.set(stacked ? 0 : -2.85, stacked ? 2.05 : 0, 0);
  crystal.group.position.set(stacked ? 0 : 2.85, stacked ? -2.05 : 0, 0);
  globe.group.scale.setScalar(stacked ? .88 : 1);
  crystal.group.scale.setScalar(stacked ? .82 : 1);
}

function updateMotionPreference() {
  reducedNote.hidden = !reducedMotion.matches;
}

function render(timeMs) {
  const time = timeMs * .001;
  const motion = reducedMotion.matches ? 0 : 1;
  const idle = !drag.active && performance.now() - drag.lastInteraction > 900;

  if (idle) {
    globe.group.rotation.y += .0016 * motion;
    crystal.group.rotation.y -= .00135 * motion;
    crystal.group.rotation.z = THREE.MathUtils.lerp(crystal.group.rotation.z, Math.sin(time * .42) * .025 * motion, .025);
    globe.group.rotation.x = THREE.MathUtils.lerp(globe.group.rotation.x, -.08, .008);
    crystal.group.rotation.x = THREE.MathUtils.lerp(crystal.group.rotation.x, .05, .008);
  }
  for (const kind of ["globe", "crystal"]) {
    const object = kind === "globe" ? globe.group : crystal.group;
    object.rotation.x += velocity[kind].x * motion;
    object.rotation.y += velocity[kind].y * motion;
    velocity[kind].multiplyScalar(.93);
  }

  globe.orbits.children[0].rotation.y = time * .15 * motion;
  globe.orbits.children[1].rotation.z = -time * .11 * motion;
  globe.orbits.children[2].rotation.y = -time * .09 * motion;
  crystal.rings.children[0].rotation.y = time * .18 * motion;
  crystal.rings.children[1].rotation.z = -time * .13 * motion;
  crystal.rings.children[2].rotation.y = time * .1 * motion;
  crystal.group.position.y += Math.sin(time * .55) * .0007 * motion;
  crystal.core.scale.set(1 + Math.sin(time * 2) * .035 * motion, 2 + Math.sin(time * 2) * .06 * motion, 1 + Math.sin(time * 2) * .035 * motion);
  crystal.core.material.emissiveIntensity = (hovered === "crystal" ? 3.5 : 2.4) + Math.sin(time * 2) * .22 * motion;
  globe.glow.material.opacity = hovered === "globe" ? .12 : .06;

  crystal.fragments.children.forEach((fragment, index) => {
    const phase = fragment.userData.phase;
    fragment.position.x = fragment.userData.home.x * (1 + fragmentImpulse * .07) + Math.sin(time * .46 + phase) * .035 * motion;
    fragment.position.y = fragment.userData.home.y + Math.sin(time * .62 + phase) * .09 * motion;
    fragment.rotation.y += (.002 + index * .0002) * motion;
  });
  fragmentImpulse *= .94;

  root.rotation.y = THREE.MathUtils.lerp(root.rotation.y, parallax.x * .045, .03);
  root.rotation.x = THREE.MathUtils.lerp(root.rotation.x, -parallax.y * .026, .03);
  camera.position.x = THREE.MathUtils.lerp(camera.position.x, parallax.x * .18, .025);
  camera.position.y = THREE.MathUtils.lerp(camera.position.y, .15 + parallax.y * .1, .025);
  camera.lookAt(0, 0, 0);

  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects([globe.body, ...globe.nodes.children.filter(child => child.isMesh), crystal.shell, crystal.core], false);
  hovered = hits.length ? (hits[0].object.userData.kind === "crystal" || hits[0].object === crystal.core ? "crystal" : "globe") : null;
  canvas.style.cursor = drag.active ? "grabbing" : hovered ? "pointer" : "grab";
  globe.nodes.children.filter(child => child.isMesh).forEach(node => {
    node.material.color.setHex(hovered === "globe" ? 0xff486a : 0xff1744);
    node.scale.setScalar(hovered === "globe" ? 1.3 : 1);
  });

  for (let i = pulses.length - 1; i >= 0; i--) {
    const pulse = pulses[i];
    pulse.life += .022;
    pulse.mesh.scale.multiplyScalar(1.025);
    pulse.mesh.material.opacity = Math.max(0, .34 * (1 - pulse.life));
    if (pulse.life >= 1) {
      pulse.mesh.geometry.dispose();
      pulse.mesh.material.dispose();
      root.remove(pulse.mesh);
      pulses.splice(i, 1);
    }
  }
  renderer.render(scene, camera);
}

function showFallback() {
  canvas.hidden = true;
  fallback.hidden = false;
}
