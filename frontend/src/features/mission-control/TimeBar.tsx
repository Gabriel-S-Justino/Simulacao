import { useMission, playbackClock } from "../../stores/missionStore";
import { useTelemetry } from "../flight-operations/useTelemetry";
import { duration } from "../../utils/format";

const SCALES = [1, 10, 100, 1000];

export function TimeBar() {
  const track = useMission((s) => s.track);
  const playing = useMission((s) => s.playing);
  const scale = useMission((s) => s.timeScale);
  const setPlaying = useMission((s) => s.setPlaying);
  const setScale = useMission((s) => s.setTimeScale);
  const tel = useTelemetry(15);
  if (!track) return null;
  const atEnd = tel.t >= track.duration;

  return (
    <div className="timebar" role="toolbar" aria-label="Controle de tempo">
      <button
        className="play"
        aria-label={playing ? "Pausar" : "Reproduzir"}
        onClick={() => {
          if (atEnd) playbackClock.t = track.t[0] ?? 0;
          setPlaying(!playing);
        }}
      >
        {playing ? (
          <svg width="10" height="12" viewBox="0 0 10 12" fill="currentColor"><rect width="3" height="12" /><rect x="7" width="3" height="12" /></svg>
        ) : (
          <svg width="10" height="12" viewBox="0 0 10 12" fill="currentColor"><path d="M0 0l10 6-10 6z" /></svg>
        )}
      </button>
      <span className="clock" aria-label="Tempo da missão">T+{duration(tel.t)}</span>
      <input
        className="scrub"
        type="range"
        aria-label="Linha do tempo"
        min={track.t[0] ?? 0}
        max={track.duration}
        step={(track.duration - (track.t[0] ?? 0)) / 2000}
        value={tel.t}
        onChange={(e) => (playbackClock.t = Number(e.target.value))}
      />
      <div className="scales" role="group" aria-label="Aceleração temporal">
        {SCALES.map((s) => (
          <button key={s} aria-pressed={scale === s} onClick={() => setScale(s)}>
            {s}×
          </button>
        ))}
      </div>
    </div>
  );
}
