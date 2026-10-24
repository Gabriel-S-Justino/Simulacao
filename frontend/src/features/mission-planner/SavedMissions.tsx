import { useMissions } from "../../services/queries";
import { useMission } from "../../stores/missionStore";

const SHOWN = 5;

export function SavedMissions() {
  const missions = useMissions(true);
  const loadMission = useMission((s) => s.loadMission);
  const current = useMission((s) => s.missionId);
  const list = missions.data?.slice(0, SHOWN) ?? [];
  if (list.length === 0) return null;
  return (
    <div className="section">
      <div className="section-title">Missões salvas</div>
      <ul className="events">
        {list.map((m) => (
          <li key={m.id}>
            <button onClick={() => loadMission(m)} aria-current={m.id === current ? "true" : undefined}>
              <span className="t">{m.status === "simulated" ? "simulada" : "rascunho"}</span>
              <span>{m.name}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
