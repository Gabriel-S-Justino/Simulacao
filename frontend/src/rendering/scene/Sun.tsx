import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";

const DISTANCE = 40_000;

/** Disco solar e luz direcional na direção calculada do Sol. Efeito visual, não atividade solar. */
export function Sun({ direction }: { direction: THREE.Vector3 }) {
  const light = useRef<THREE.DirectionalLight>(null);
  const sprite = useRef<THREE.Sprite>(null);
  const texture = useMemo(() => {
    const size = 256;
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = size;
    const ctx = canvas.getContext("2d")!;
    const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    g.addColorStop(0, "rgba(255,255,255,1)");
    g.addColorStop(0.07, "rgba(255,250,238,1)");
    g.addColorStop(0.14, "rgba(255,226,170,0.32)");
    g.addColorStop(0.45, "rgba(255,190,120,0.05)");
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, size, size);
    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  }, []);
  useEffect(() => () => texture.dispose(), [texture]);

  useFrame(() => {
    light.current?.position.copy(direction).multiplyScalar(DISTANCE);
    sprite.current?.position.copy(direction).multiplyScalar(DISTANCE);
  });

  return (
    <>
      <directionalLight ref={light} intensity={3.2} color="#fff6ea" />
      {/* Luz refletida pela Terra (albedo), aproximação visual a partir do centro do planeta. */}
      <pointLight position={[0, 0, 0]} intensity={0.35} decay={0} color="#7894c0" />
      <ambientLight intensity={0.015} />
      <sprite ref={sprite} scale={[5200, 5200, 1]} renderOrder={-1}>
        <spriteMaterial map={texture} blending={THREE.AdditiveBlending} depthWrite={false} transparent />
      </sprite>
    </>
  );
}
