import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../services/api";
import { useCheckpoints } from "../../services/queries";
import { playbackClock, useMission } from "../../stores/missionStore";
import { duration } from "../../utils/format";

/** Checkpoints persistidos: snapshot do estado físico calculado pelo backend no instante escolhido. */
export function Checkpoints({ missionId }: { missionId: string }) {
  const list = useCheckpoints(missionId);
  const loadSimulation = useMission((s) => s.loadSimulation);
  const resumedFrom = useMission((s) => s.resumedFrom);
  const queryClient = useQueryClient();

  const save = useMutation({
    mutationFn: () => {
      const t = Math.round(playbackClock.t);
      return api.createCheckpoint(missionId, t, `T+${duration(t)}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["checkpoints", missionId] }),
  });

  const resume = useMutation({
    mutationFn: (ck: { id: string; t_s: number }) => api.resume(missionId, ck.id),
    onSuccess: (run, ck) => loadSimulation(run.simulation, ck),
  });

  return (
    <div className="section">
      <div className="section-title">Checkpoints</div>
      {resumedFrom && <p className="note">Retomada do checkpoint T+{duration(resumedFrom.t_s)}.</p>}
      <ul className="events">
        {list.data?.map((ck) => (
          <li key={ck.id}>
            <button
              disabled={resume.isPending}
              onClick={() => resume.mutate({ id: ck.id, t_s: ck.t_s })}
              title="Retomar a simulação a partir deste estado"
            >
              <span className="t">T+{duration(ck.t_s)}</span>
              <span>Retomar · {ck.state.mass_kg.toFixed(1)} kg</span>
            </button>
          </li>
        ))}
      </ul>
      <button className="link" disabled={save.isPending} onClick={() => save.mutate()}>
        {save.isPending ? "Salvando…" : "Salvar checkpoint no instante atual"}
      </button>
      {(save.isError || resume.isError) && (
        <p className="note" style={{ color: "var(--error)" }}>
          {(save.error ?? resume.error)?.message}
        </p>
      )}
    </div>
  );
}
