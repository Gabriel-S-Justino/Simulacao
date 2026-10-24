import { useMission, type Phase } from "../../stores/missionStore";
import { useView } from "../../stores/viewStore";

const PHASES: { id: Phase; label: string }[] = [
  { id: "assembly", label: "Montagem" },
  { id: "planning", label: "Planejamento" },
  { id: "operations", label: "Operações" },
];

export function TopBar() {
  const phase = useMission((s) => s.phase);
  const setPhase = useMission((s) => s.setPhase);
  const hasSim = useMission((s) => s.simulation !== null);
  const clean = useMission((s) => s.cleanMode);
  const toggleClean = useMission((s) => s.toggleClean);
  const focus = useView((s) => s.focus);
  const setFocus = useView((s) => s.setFocus);
  const liveOpen = useView((s) => s.liveOpen);
  const toggleLive = useView((s) => s.toggleLive);

  return (
    <header className="topbar">
      <span className="brand">Mission Architect</span>
      <nav className="nav" aria-label="Fases da missão">
        {PHASES.map((p) => (
          <button
            key={p.id}
            aria-current={phase === p.id ? "page" : undefined}
            disabled={p.id === "operations" && !hasSim}
            onClick={() => setPhase(p.id)}
          >
            {p.label}
          </button>
        ))}
      </nav>
      <span className="spacer" />
      <div role="group" aria-label="Foco da câmera" style={{ display: "flex" }}>
        <button className="chip" aria-pressed={focus === "craft"} onClick={() => setFocus("craft")}>
          Nave
        </button>
        <button className="chip" aria-pressed={focus === "earth"} onClick={() => setFocus("earth")}>
          Terra
        </button>
      </div>
      <button className="chip" aria-pressed={liveOpen} onClick={toggleLive} title="Dados de fontes externas">
        Dados externos
      </button>
      <button className="chip" aria-pressed={clean} onClick={toggleClean} title="Modo cinematográfico (C)">
        {clean ? "Sair da tela limpa" : "Tela limpa"}
      </button>
    </header>
  );
}
