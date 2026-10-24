import { useEffect, useState } from "react";
import { FlightHud } from "../features/flight-operations/FlightHud";
import { SidePanel } from "../features/mission-control/SidePanel";
import { TimeBar } from "../features/mission-control/TimeBar";
import { TopBar } from "../features/mission-control/TopBar";
import { SceneRoot } from "../rendering/scene/SceneRoot";
import { CRAFT_VISUAL_SCALE } from "../rendering/spacecraft/Spacecraft";
import { hasWebGL2 } from "../rendering/webgl";
import { useMission } from "../stores/missionStore";
import { useView } from "../stores/viewStore";

export function App({ webgl2 = hasWebGL2() }: { webgl2?: boolean }) {
  const clean = useMission((s) => s.cleanMode);
  const toggleClean = useMission((s) => s.toggleClean);
  const focus = useView((s) => s.focus);
  const [contextLost, setContextLost] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;
      if (e.key === "c" || e.key === "C") toggleClean();
      if (e.key === " ") {
        const s = useMission.getState();
        if (s.track) {
          e.preventDefault();
          s.setPlaying(!s.playing);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggleClean]);

  if (!webgl2) {
    return (
      <div className="fallback">
        <div>
          <h1>WebGL 2 indisponível</h1>
          <p>
            Este simulador requer WebGL 2. Atualize o navegador ou os drivers de vídeo, ou ative a
            aceleração por hardware.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`app${clean ? " clean" : ""}`}>
      <div className="scene">
        <SceneRoot onContextLost={setContextLost} />
      </div>
      <TopBar />
      <SidePanel />
      <FlightHud />
      <TimeBar />
      {focus === "craft" && !clean && (
        <span className="scale-badge" title="Escala visual; a física usa as dimensões reais">
          Nave ×{CRAFT_VISUAL_SCALE}
        </span>
      )}
      {contextLost && (
        <div className="alert" role="alert">
          <strong>Contexto gráfico perdido</strong>
          Aguardando o navegador restaurar a GPU. A simulação não foi afetada.
        </div>
      )}
    </div>
  );
}
