import { useMission } from "../../stores/missionStore";
import { AssemblyPanel } from "../spacecraft-assembly/AssemblyPanel";
import { PlanPanel } from "../mission-planner/PlanPanel";
import { OperationsPanel } from "../flight-operations/OperationsPanel";

const TITLES = { assembly: "Montagem da nave", planning: "Plano de manobra", operations: "Operações de voo" };

export function SidePanel() {
  const phase = useMission((s) => s.phase);
  const open = useMission((s) => s.panelOpen);
  const toggle = useMission((s) => s.togglePanel);
  return (
    <>
      {!open && (
        <button className="collapse" aria-label="Abrir painel" onClick={toggle}>
          ›
        </button>
      )}
      <aside className="panel" data-open={open} aria-label={TITLES[phase]} aria-hidden={!open}>
        <div className="panel-head">
          <span className="panel-title">{TITLES[phase]}</span>
          <button className="link" aria-label="Recolher painel" onClick={toggle}>
            ‹
          </button>
        </div>
        <div className="panel-body">
          {phase === "assembly" && <AssemblyPanel />}
          {phase === "planning" && <PlanPanel />}
          {phase === "operations" && <OperationsPanel />}
        </div>
      </aside>
    </>
  );
}
