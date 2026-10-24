import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { playbackClock, useMission } from "../../stores/missionStore";
import { useLayerStatus } from "../../stores/layerStore";
import { EARTH_RADIUS_M, METERS_PER_UNIT, gmst } from "../frames";
import { atmosphereFragment, earthFragment, earthVertex } from "./earthShaders";
import { BLACK_MARBLE, BLUE_MARBLE, gibsWmsUrl, type GibsLayer } from "./gibs";

const R = EARTH_RADIUS_M / METERS_PER_UNIT;

function loadLayer(layer: GibsLayer, onDone: (tex: THREE.Texture | null) => void): () => void {
  const loader = new THREE.TextureLoader();
  loader.setCrossOrigin("anonymous");
  let cancelled = false;
  const set = useLayerStatus.getState().set;
  set(layer.id, { status: "loading" });
  loader.load(
    gibsWmsUrl(layer),
    (tex) => {
      if (cancelled) return tex.dispose();
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.anisotropy = 8;
      set(layer.id, { status: "ok", fetchedAt: new Date().toISOString() });
      onDone(tex);
    },
    undefined,
    () => {
      if (!cancelled) {
        set(layer.id, { status: "unavailable" });
        onDone(null);
      }
    },
  );
  return () => {
    cancelled = true;
  };
}

export function Earth({ sunDir }: { sunDir: THREE.Vector3 }) {
  const mesh = useRef<THREE.Group>(null);
  const epochMs = useMission((s) => s.epochMs);
  const uniforms = useMemo(
    () => ({
      dayMap: { value: null as THREE.Texture | null },
      nightMap: { value: null as THREE.Texture | null },
      hasDay: { value: 0 },
      hasNight: { value: 0 },
      sunDir: { value: sunDir },
    }),
    [sunDir],
  );
  const atmoUniforms = useMemo(() => ({ sunDir: { value: sunDir } }), [sunDir]);

  useEffect(() => {
    const textures: THREE.Texture[] = [];
    const c1 = loadLayer(BLUE_MARBLE, (t) => {
      if (t) textures.push(t);
      uniforms.dayMap.value = t;
      uniforms.hasDay.value = t ? 1 : 0;
    });
    const c2 = loadLayer(BLACK_MARBLE, (t) => {
      if (t) textures.push(t);
      uniforms.nightMap.value = t;
      uniforms.hasNight.value = t ? 1 : 0;
    });
    return () => {
      c1();
      c2();
      textures.forEach((t) => t.dispose());
    };
  }, [uniforms]);

  useFrame(() => {
    if (mesh.current) mesh.current.rotation.y = gmst(new Date(epochMs + playbackClock.t * 1000));
  });

  return (
    <group>
      <group ref={mesh}>
        <mesh>
          <sphereGeometry args={[R, 128, 64]} />
          <shaderMaterial vertexShader={earthVertex} fragmentShader={earthFragment} uniforms={uniforms} />
        </mesh>
      </group>
      <mesh scale={1.022}>
        <sphereGeometry args={[R, 96, 48]} />
        <shaderMaterial
          vertexShader={earthVertex}
          fragmentShader={atmosphereFragment}
          uniforms={atmoUniforms}
          side={THREE.BackSide}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  );
}
