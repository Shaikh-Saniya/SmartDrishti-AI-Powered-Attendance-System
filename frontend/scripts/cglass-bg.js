/**
 * SmartDrishti — CGlass Background (Three.js)
 * Lightweight floating crystal particles — subtle, 60fps.
 * Loaded ONLY on pages that include this script.
 */
(function () {
  'use strict';

  // Bail out if Three.js isn't loaded yet (will be retried by main.js)
  if (typeof THREE === 'undefined') return;

  const canvas = document.createElement('canvas');
  canvas.id = 'cglass-bg-canvas';
  Object.assign(canvas.style, {
    position: 'fixed',
    inset: '0',
    width: '100%',
    height: '100%',
    zIndex: '-10',
    pointerEvents: 'none',
  });
  document.body.prepend(canvas);

  /* ── Scene setup ─────────────────────────────── */
  const renderer = new THREE.WebGLRenderer({
    canvas,
    alpha: true,           // transparent so CSS bg shows through
    antialias: false,      // off for performance
    powerPreference: 'low-power',
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(0x000000, 0);

  const scene  = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);
  camera.position.z = 6;

  /* ── Crystal particle geometry ───────────────── */
  // Low-poly icosahedra for a "cut crystal" look
  const geos = [
    new THREE.IcosahedronGeometry(0.28, 0),
    new THREE.OctahedronGeometry(0.22, 0),
    new THREE.TetrahedronGeometry(0.20, 0),
  ];

  const goldenPalette = [0xC9A97A, 0x987E5D, 0xF0C060, 0x7EACB5, 0xD4B896];

  const crystals = [];
  const COUNT    = 14; // Enough to populate without crowding

  for (let i = 0; i < COUNT; i++) {
    const geoIndex = Math.floor(Math.random() * geos.length);
    const color    = goldenPalette[Math.floor(Math.random() * goldenPalette.length)];

    const mat = new THREE.MeshPhongMaterial({
      color,
      transparent: true,
      opacity:     0.18 + Math.random() * 0.14,
      wireframe:   false,
      shininess:   120,
      specular:    new THREE.Color(0xffffff),
      flatShading: true,
    });

    const mesh = new THREE.Mesh(geos[geoIndex], mat);

    // Random spread across the viewport
    mesh.position.set(
      (Math.random() - 0.5) * 10,
      (Math.random() - 0.5) * 7,
      (Math.random() - 0.5) * 3 - 1
    );
    mesh.rotation.set(
      Math.random() * Math.PI * 2,
      Math.random() * Math.PI * 2,
      Math.random() * Math.PI * 2
    );

    const speed = {
      rotX: (Math.random() - 0.5) * 0.006,
      rotY: (Math.random() - 0.5) * 0.008,
      floatY: (Math.random() - 0.5) * 0.0012,
      phase: Math.random() * Math.PI * 2,
    };

    scene.add(mesh);
    crystals.push({ mesh, speed });
  }

  /* ── Lighting ──────────────────────────────── */
  const ambient = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambient);

  const dirLight = new THREE.DirectionalLight(0xF0C060, 0.9); // Golden light
  dirLight.position.set(3, 5, 3);
  scene.add(dirLight);

  const dirLight2 = new THREE.DirectionalLight(0x7EACB5, 0.4); // Teal fill
  dirLight2.position.set(-4, -2, 2);
  scene.add(dirLight2);

  /* ── Mouse parallax ─────────────────────────── */
  let mouseX = 0, mouseY = 0;
  const PARALLAX_STRENGTH = 0.0015;

  document.addEventListener('mousemove', (e) => {
    mouseX = (e.clientX / window.innerWidth  - 0.5) * 2;
    mouseY = (e.clientY / window.innerHeight - 0.5) * 2;
  }, { passive: true });

  /* ── Resize handler ──────────────────────────── */
  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }, { passive: true });

  /* ── Animation loop ──────────────────────────── */
  let lastTime = 0;
  let rafId;

  function animate(time) {
    rafId = requestAnimationFrame(animate);

    // Cap frame rate for low-power mode (target ~30fps background)
    if (time - lastTime < 32) return;
    lastTime = time;

    const t = time * 0.001;

    crystals.forEach(({ mesh, speed }) => {
      mesh.rotation.x += speed.rotX;
      mesh.rotation.y += speed.rotY;
      // Gentle float
      mesh.position.y += Math.sin(t + speed.phase) * speed.floatY;
    });

    // Camera subtle drift from mouse
    camera.position.x += (mouseX * PARALLAX_STRENGTH - camera.position.x) * 0.02;
    camera.position.y += (-mouseY * PARALLAX_STRENGTH - camera.position.y) * 0.02;

    renderer.render(scene, camera);
  }

  animate(0);

  // Pause when tab is hidden (save battery)
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      cancelAnimationFrame(rafId);
    } else {
      animate(0);
    }
  });
})();
