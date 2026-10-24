import * as THREE from "three";

function canvasTexture(size: number, draw: (ctx: CanvasRenderingContext2D, size: number) => void) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  draw(canvas.getContext("2d")!, size);
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.anisotropy = 4;
  return tex;
}

/** Materiais compartilhados da nave. Criados uma vez e descartados juntos. */
export function createSpacecraftMaterials() {
  // Relevo amassado do isolamento multicamadas (MLI).
  const crinkle = canvasTexture(256, (ctx, s) => {
    ctx.fillStyle = "#808080";
    ctx.fillRect(0, 0, s, s);
    for (let i = 0; i < 900; i++) {
      const g = 90 + Math.floor(Math.random() * 90);
      ctx.strokeStyle = `rgba(${g},${g},${g},0.55)`;
      ctx.lineWidth = 0.5 + Math.random() * 2;
      ctx.beginPath();
      const x = Math.random() * s;
      const y = Math.random() * s;
      ctx.moveTo(x, y);
      ctx.lineTo(x + (Math.random() - 0.5) * 40, y + (Math.random() - 0.5) * 40);
      ctx.stroke();
    }
  });
  crinkle.repeat.set(2, 2);

  const cells = canvasTexture(512, (ctx, s) => {
    ctx.fillStyle = "#0b1426";
    ctx.fillRect(0, 0, s, s);
    const n = 8;
    const c = s / n;
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        const grad = ctx.createLinearGradient(i * c, j * c, (i + 1) * c, (j + 1) * c);
        grad.addColorStop(0, "#14284a");
        grad.addColorStop(1, "#0a1630");
        ctx.fillStyle = grad;
        ctx.fillRect(i * c + 2, j * c + 2, c - 4, c - 4);
      }
    }
    ctx.strokeStyle = "rgba(190,200,215,0.55)";
    ctx.lineWidth = 2;
    for (let i = 0; i <= n; i++) {
      ctx.beginPath();
      ctx.moveTo(i * c, 0);
      ctx.lineTo(i * c, s);
      ctx.moveTo(0, i * c);
      ctx.lineTo(s, i * c);
      ctx.stroke();
    }
  });
  cells.colorSpace = THREE.SRGBColorSpace;

  return {
    mli: new THREE.MeshStandardMaterial({
      color: "#c79a3c",
      metalness: 0.75,
      roughness: 0.38,
      bumpMap: crinkle,
      bumpScale: 0.6,
    }),
    mliSilver: new THREE.MeshStandardMaterial({
      color: "#c8ccd2",
      metalness: 0.7,
      roughness: 0.34,
      bumpMap: crinkle,
      bumpScale: 0.5,
    }),
    solarCells: new THREE.MeshStandardMaterial({
      map: cells,
      metalness: 0.3,
      roughness: 0.3,
      color: "#ffffff",
    }),
    panelBack: new THREE.MeshStandardMaterial({ color: "#3a3f47", metalness: 0.4, roughness: 0.7 }),
    aluminum: new THREE.MeshStandardMaterial({ color: "#a9adb3", metalness: 0.7, roughness: 0.4 }),
    darkMetal: new THREE.MeshStandardMaterial({ color: "#2a2c30", metalness: 0.9, roughness: 0.45 }),
    nozzle: new THREE.MeshStandardMaterial({
      color: "#4a4038",
      metalness: 1,
      roughness: 0.5,
      side: THREE.DoubleSide,
    }),
    dish: new THREE.MeshStandardMaterial({
      color: "#e9e7e2",
      metalness: 0.1,
      roughness: 0.6,
      side: THREE.DoubleSide,
    }),
    radiator: new THREE.MeshStandardMaterial({ color: "#f1f2f4", metalness: 0, roughness: 0.85 }),
    lens: new THREE.MeshStandardMaterial({ color: "#06080c", metalness: 0.2, roughness: 0.05 }),
    plume: new THREE.MeshBasicMaterial({
      color: "#9cc2ff",
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    }),
    textures: [crinkle, cells],
  };
}

export type SpacecraftMaterials = ReturnType<typeof createSpacecraftMaterials>;

export function disposeMaterials(m: SpacecraftMaterials) {
  for (const value of Object.values(m)) {
    if (value instanceof THREE.Material) value.dispose();
  }
  m.textures.forEach((t) => t.dispose());
}
