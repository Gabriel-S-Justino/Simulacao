/**
 * Gera o modelo 3D da nave a partir da montagem do usuário. Cada componente
 * visível do catálogo vira geometria proporcional às suas dimensões (metros,
 * no espaço local do modelo). Eixo +Y = frente (direção de empuxo), motor em -Y.
 */
import * as THREE from "three";
import type { Component } from "../../types/contracts";
import type { SpacecraftMaterials } from "./materials";

export interface PlacedPart {
  component: Component;
  quantity: number;
}

function bell(radius: number, length: number, segments = 32): THREE.LatheGeometry {
  const pts: THREE.Vector2[] = [];
  for (let i = 0; i <= 16; i++) {
    const s = i / 16;
    pts.push(new THREE.Vector2(radius * (0.28 + 0.72 * Math.pow(s, 0.6)), -length * s));
  }
  return new THREE.LatheGeometry(pts, segments);
}

function dish(diameter: number, depth: number): THREE.LatheGeometry {
  const pts: THREE.Vector2[] = [];
  const r = diameter / 2;
  for (let i = 0; i <= 20; i++) {
    const x = (i / 20) * r;
    pts.push(new THREE.Vector2(x, (depth * x * x) / (r * r)));
  }
  return new THREE.LatheGeometry(pts, 48);
}

export interface SpacecraftModel {
  root: THREE.Group;
  solarWings: THREE.Object3D[];
  plume: THREE.Mesh | null;
  geometries: THREE.BufferGeometry[];
}

export function buildSpacecraft(parts: PlacedPart[], mat: SpacecraftMaterials): SpacecraftModel {
  const root = new THREE.Group();
  const geometries: THREE.BufferGeometry[] = [];
  const add = <G extends THREE.BufferGeometry>(g: G) => {
    geometries.push(g);
    return g;
  };
  const solarWings: THREE.Object3D[] = [];

  const core = parts.find((p) => p.component.category === "structure" && !p.component.params.separator);
  const [bx, by, bz] = core ? core.component.dimensions_m : [0.8, 0.8, 0.8];
  const bodyW = bx;
  const bodyH = bz; // altura do núcleo no eixo Y local
  const bodyD = by;

  // Núcleo com MLI dourado e quadro estrutural de alumínio.
  const body = new THREE.Mesh(add(new THREE.BoxGeometry(bodyW, bodyH, bodyD)), mat.mli);
  root.add(body);
  const strut = add(new THREE.CylinderGeometry(0.025, 0.025, bodyH * 1.02, 8));
  for (const sx of [-1, 1]) {
    for (const sz of [-1, 1]) {
      const m = new THREE.Mesh(strut, mat.aluminum);
      m.position.set((sx * bodyW) / 2, 0, (sz * bodyD) / 2);
      root.add(m);
    }
  }
  const deck = add(new THREE.BoxGeometry(bodyW * 1.04, 0.04, bodyD * 1.04));
  for (const y of [-bodyH / 2, bodyH / 2]) {
    const m = new THREE.Mesh(deck, mat.aluminum);
    m.position.y = y;
    root.add(m);
  }

  let wingIndex = 0;
  let plume: THREE.Mesh | null = null;
  let monoCount = 0;

  for (const { component: c, quantity } of parts) {
    const [dx, dy] = c.dimensions_m;
    switch (c.category) {
      case "power_solar": {
        for (let q = 0; q < quantity; q++, wingIndex++) {
          const side = wingIndex % 2 === 0 ? 1 : -1;
          const tier = Math.floor(wingIndex / 2);
          const wing = new THREE.Group();
          // Haste até o painel; o painel gira em torno do eixo da haste (articulação).
          const boomLen = 0.5;
          const boom = new THREE.Mesh(add(new THREE.CylinderGeometry(0.02, 0.02, boomLen, 8)), mat.aluminum);
          boom.rotation.z = Math.PI / 2;
          boom.position.x = (side * boomLen) / 2;
          wing.add(boom);
          const hinge = new THREE.Group();
          hinge.position.x = side * (boomLen + dx / 2);
          const front = new THREE.Mesh(add(new THREE.PlaneGeometry(dx, dy)), mat.solarCells);
          const back = new THREE.Mesh(add(new THREE.PlaneGeometry(dx, dy)), mat.panelBack);
          front.rotation.x = -Math.PI / 2;
          back.rotation.x = Math.PI / 2;
          back.position.y = -0.004;
          const frame = new THREE.Mesh(add(new THREE.BoxGeometry(dx + 0.04, 0.02, 0.03)), mat.aluminum);
          frame.position.z = dy / 2;
          const frame2 = frame.clone();
          frame2.position.z = -dy / 2;
          hinge.add(front, back, frame, frame2);
          wing.add(hinge);
          wing.position.set((side * bodyW) / 2, bodyH * 0.25 - tier * (dy + 0.15), 0);
          root.add(wing);
          solarWings.push(hinge);
        }
        break;
      }
      case "comms": {
        if (c.params.gain_dbi !== undefined && Number(c.params.gain_dbi) > 20) {
          const d = add(dish(dx, dx * 0.18));
          const m = new THREE.Mesh(d, mat.dish);
          m.rotation.x = -Math.PI / 2;
          const g = new THREE.Group();
          g.add(m);
          const feed = new THREE.Mesh(add(new THREE.CylinderGeometry(0.015, 0.015, dx * 0.45, 6)), mat.darkMetal);
          feed.rotation.x = Math.PI / 2;
          feed.position.z = dx * 0.22;
          g.add(feed);
          const mast = new THREE.Mesh(add(new THREE.CylinderGeometry(0.03, 0.03, 0.35, 8)), mat.aluminum);
          mast.rotation.x = Math.PI / 2;
          mast.position.z = -0.17;
          g.add(mast);
          g.position.set(0, bodyH * 0.1, bodyD / 2 + 0.35);
          root.add(g);
        } else if (!c.params.transmitter) {
          const m = new THREE.Mesh(add(new THREE.ConeGeometry(0.05, 0.15, 12)), mat.radiator);
          m.position.set(bodyW * 0.3, bodyH / 2 + 0.08, -bodyD * 0.3);
          root.add(m);
        }
        break;
      }
      case "propulsion_engine": {
        const thrust = Number(c.params.thrust_n ?? 0);
        if (thrust >= 100) {
          const g = add(bell(dx / 2, dy * 0.75));
          const nozzle = new THREE.Mesh(g, mat.nozzle);
          nozzle.position.y = -bodyH / 2 - 0.12;
          const throat = new THREE.Mesh(add(new THREE.CylinderGeometry(dx * 0.2, dx * 0.25, 0.14, 16)), mat.darkMetal);
          throat.position.y = -bodyH / 2 - 0.06;
          root.add(nozzle, throat);
          const plumeGeo = add(new THREE.ConeGeometry(dx * 0.6, dy * 3, 24, 1, true));
          plume = new THREE.Mesh(plumeGeo, mat.plume);
          plume.position.y = -bodyH / 2 - 0.12 - dy * 0.75 - dy * 1.5;
          plume.rotation.x = Math.PI;
          root.add(plume);
        } else {
          for (let q = 0; q < quantity; q++, monoCount++) {
            const nozzle = new THREE.Mesh(add(bell(dx / 2, dy * 0.6, 16)), mat.nozzle);
            const sx = monoCount % 2 === 0 ? 1 : -1;
            const sz = Math.floor(monoCount / 2) % 2 === 0 ? 1 : -1;
            nozzle.position.set((sx * bodyW) / 2.6, -bodyH / 2, (sz * bodyD) / 2.6);
            root.add(nozzle);
          }
        }
        break;
      }
      case "thermal": {
        const rad = new THREE.Mesh(add(new THREE.BoxGeometry(0.02, bodyH * 0.8, bodyD * 0.8)), mat.radiator);
        rad.position.x = -bodyW / 2 - 0.012;
        root.add(rad);
        break;
      }
      case "payload": {
        const len = c.dimensions_m[2];
        if (len > 1) {
          const boom = new THREE.Mesh(add(new THREE.CylinderGeometry(0.012, 0.012, len, 6)), mat.aluminum);
          boom.rotation.z = Math.PI / 2;
          boom.position.set(-bodyW / 2 - len / 2, bodyH * 0.4, -bodyD * 0.3);
          root.add(boom);
        } else {
          const barrel = new THREE.Mesh(add(new THREE.CylinderGeometry(dx / 2, dx / 2, len * 0.6, 32)), mat.mliSilver);
          barrel.rotation.x = Math.PI / 2;
          barrel.position.set(-bodyW * 0.18, -bodyH * 0.15, bodyD / 2 + len * 0.3);
          const lens = new THREE.Mesh(add(new THREE.CircleGeometry(dx / 2.4, 32)), mat.lens);
          lens.position.set(-bodyW * 0.18, -bodyH * 0.15, bodyD / 2 + len * 0.6 + 0.001);
          root.add(barrel, lens);
        }
        break;
      }
      case "attitude": {
        if (c.params.accuracy_arcsec !== undefined) {
          const baffle = new THREE.Mesh(add(new THREE.CylinderGeometry(0.05, 0.07, 0.2, 16, 1, true)), mat.darkMetal);
          baffle.position.set(bodyW * 0.3, bodyH / 2 + 0.1, bodyD * 0.25);
          root.add(baffle);
        }
        break;
      }
      default:
        break;
    }
  }
  return { root, solarWings, plume, geometries };
}
