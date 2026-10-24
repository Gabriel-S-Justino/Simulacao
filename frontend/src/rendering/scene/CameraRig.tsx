import { OrbitControls } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useRef, type ComponentRef } from "react";
import * as THREE from "three";
import { useView } from "../../stores/viewStore";
import { craftPosition } from "../craftPosition";

const _target = new THREE.Vector3();
const _delta = new THREE.Vector3();
const _offset = new THREE.Vector3();
const _up = new THREE.Vector3(0, 1, 0);

/** Câmera: foco na nave (acompanha) ou na Terra. Transições suaves; nunca afeta a física. */
export function CameraRig({ sunDir }: { sunDir: THREE.Vector3 }) {
  const controls = useRef<ComponentRef<typeof OrbitControls>>(null);
  const focus = useView((s) => s.focus);
  const camera = useThree((s) => s.camera);
  const transition = useRef(1);
  const desiredDir = useRef(new THREE.Vector3(0, 0.4, 1).normalize());

  useEffect(() => {
    transition.current = 0;
  }, [focus]);

  useFrame((_, dt) => {
    const c = controls.current;
    if (!c) return;
    if (focus === "craft") _target.copy(craftPosition.scene);
    else _target.set(0, 0, 0);

    if (transition.current === 0) {
      // Enquadramento automático em 3/4 pelo lado iluminado (sunDir já atualizado pelo Ticker).
      const side = new THREE.Vector3().crossVectors(sunDir, _up).normalize();
      desiredDir.current
        .copy(sunDir)
        .multiplyScalar(0.8)
        .addScaledVector(_up, 0.45)
        .addScaledVector(side, -0.7)
        .normalize();
    }
    if (transition.current < 1) {
      transition.current = Math.min(1, transition.current + dt * 1.6);
      const k = 1 - Math.pow(1 - transition.current, 3);
      _delta.copy(_target).sub(c.target).multiplyScalar(k);
      c.target.add(_delta);
      const desired = focus === "craft" ? 0.035 : 32;
      _offset.copy(camera.position).sub(c.target);
      const len = _offset.length();
      _offset.normalize().lerp(desiredDir.current, k).normalize();
      _offset.setLength(len + (desired - len) * k);
      camera.position.copy(c.target).add(_offset);
    } else {
      _delta.copy(_target).sub(c.target);
      c.target.copy(_target);
      camera.position.add(_delta);
    }
    c.minDistance = focus === "craft" ? 0.008 : 7.2;
    c.update();
  });

  return (
    <OrbitControls
      ref={controls}
      makeDefault
      enablePan={false}
      enableDamping
      dampingFactor={0.08}
      rotateSpeed={0.5}
      zoomSpeed={0.9}
      maxDistance={2_000}
    />
  );
}
