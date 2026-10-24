import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef, type ReactNode } from "react";
import * as THREE from "three";
import { playbackClock, useMission } from "../../stores/missionStore";
import { useLayerStatus } from "../../stores/layerStore";
import { EARTH_RADIUS_M, METERS_PER_UNIT, gmst } from "../frames";
import { atmosphereFragment, earthFragment, earthVertex } from "./earthShaders";
import { BLACK_MARBLE, gibsWmsUrl, type GibsLayer } from "./gibs";

const R = EARTH_RADIUS_M / METERS_PER_UNIT;

export interface DaySource {
  layer: GibsLayer;
  /** Data (YYYY-MM-DD) para camadas temporais, conforme o catálogo GIBS do backend. */
  time?: string;
}

function loadLayer(
  layer: GibsLayer,
  onDone: (tex: THREE.Texture | null) => void,
  time?: string,
): () => void {
  const loader = new THREE.TextureLoader();
  loader.setCrossOrigin("anonymous");
  let cancelled = false;
  const set = useLayerStatus.getState().set;
  set(layer.id, { status: "loading" });
  loader.load(
    gibsWmsUrl(layer, 4096, time),
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

/** `children` ficam no referencial da Terra (giram com ela): marcadores geográficos. */
export function Earth({
  sunDir,
  day,
  children,
}: {
  sunDir: THREE.Vector3;
  day: DaySource;
  children?: ReactNode;
}) {
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

  const { layer: dayLayer, time: dayTime } = day;
  useEffect(() => {
    let tex: THREE.Texture | null = null;
    const cancel = loadLayer(
      dayLayer,
      (t) => {
        tex = t;
        // Ao trocar de camada, a anterior permanece até a nova chegar (ou falhar).
        if (t) {
          const prev = uniforms.dayMap.value;
          uniforms.dayMap.value = t;
          uniforms.hasDay.value = 1;
          prev?.dispose();
        } else if (!uniforms.dayMap.value) {
          uniforms.hasDay.value = 0;
        }
      },
      dayTime,
    );
    return () => {
      cancel();
      if (tex && uniforms.dayMap.value !== tex) tex.dispose();
    };
  }, [uniforms, dayLayer, dayTime]);

  useEffect(() => () => uniforms.dayMap.value?.dispose(), [uniforms]);

  useEffect(() => {
    let tex: THREE.Texture | null = null;
    const cancel = loadLayer(BLACK_MARBLE, (t) => {
      tex = t;
      uniforms.nightMap.value = t;
      uniforms.hasNight.value = t ? 1 : 0;
    });
    return () => {
      cancel();
      tex?.dispose();
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
        {children}
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
