import type { UseQueryResult } from "@tanstack/react-query";
import { useEarthEvents, useGibsLayers, useIssPosition, useSpaceWeather } from "../../services/queries";
import { CATEGORY_COLORS } from "../../rendering/celestial-bodies/GeoMarkers";
import { VIIRS_DAILY } from "../../rendering/celestial-bodies/gibs";
import { useView } from "../../stores/viewStore";
import type { Envelope } from "../../types/sources";
import { fmt, kms } from "../../utils/format";

const STATUS_LABEL = {
  ok: "ok",
  stale: "em cache (fonte falhou)",
  error: "indisponível",
  not_configured: "não configurado",
} as const;

function age(iso: string | null | undefined): string {
  if (!iso) return "";
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 90) return `há ${Math.round(s)} s`;
  if (s < 5400) return `há ${Math.round(s / 60)} min`;
  if (s < 172_800) return `há ${Math.round(s / 3600)} h`;
  return `há ${Math.round(s / 86_400)} d`;
}

/** Estado honesto da fonte: carregando, backend fora, ou o status do envelope §4.9. */
export function SourceStatus({
  query,
  env,
}: {
  query: Pick<UseQueryResult, "isLoading" | "isError">;
  env: Envelope<unknown> | undefined;
}) {
  if (query.isLoading) return <span className="src-status" data-status="loading">consultando…</span>;
  if (query.isError || !env) return <span className="src-status" data-status="error">backend indisponível</span>;
  const detail = env.error ? ` · ${env.error.message}` : "";
  return (
    <span className="src-status" data-status={env.status} title={[...env.notes, env.uncertainty ?? ""].join(" ")}>
      {env.source}: {STATUS_LABEL[env.status]}
      {env.fetched_at ? ` · obtido ${age(env.fetched_at)}` : ""}
      {detail}
    </span>
  );
}

function EarthSection() {
  const { showEvents, setShowEvents, showIss, setShowIss, dayLayer, setDayLayer } = useView();
  const events = useEarthEvents(showEvents);
  const iss = useIssPosition(showIss);
  const gibs = useGibsLayers(dayLayer === "viirs-daily");
  const viirs = gibs.data?.data?.layers.find((l) => l.id === VIIRS_DAILY.id);
  const categories = new Map<string, string>();
  for (const e of events.data?.data ?? []) {
    const c = e.categories[0];
    if (c) categories.set(c.id, c.title);
  }
  const pos = iss.data?.data;

  return (
    <div className="section">
      <div className="section-title">Terra</div>
      <label className="toggle">
        <input type="checkbox" checked={showEvents} onChange={(e) => setShowEvents(e.target.checked)} />
        Eventos naturais abertos (EONET, 30 dias)
      </label>
      {showEvents && (
        <div className="src">
          <SourceStatus query={events} env={events.data} />
          {events.data?.data && (
            <>
              <div className="note">{events.data.data.length} eventos no globo (posição mais recente de cada um).</div>
              <ul className="legend">
                {[...categories].map(([id, title]) => (
                  <li key={id}>
                    <i style={{ background: CATEGORY_COLORS[id] ?? "#cfd6e0" }} />
                    {title}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      <label className="toggle">
        <input type="checkbox" checked={showIss} onChange={(e) => setShowIss(e.target.checked)} />
        Estação Espacial (subponto, Open Notify)
      </label>
      {showIss && (
        <div className="src">
          <SourceStatus query={iss} env={iss.data} />
          {pos && (
            <div className="note mono">
              {fmt(pos.lat_deg, 2)}°, {fmt(pos.lon_deg, 2)}° · observado {age(pos.observed_at)}
            </div>
          )}
        </div>
      )}

      <div className="field">
        <label htmlFor="day-layer">Textura diurna</label>
        <select
          id="day-layer"
          className="select"
          value={dayLayer}
          onChange={(e) => setDayLayer(e.target.value as typeof dayLayer)}
        >
          <option value="blue-marble">Blue Marble (composto)</option>
          <option value="viirs-daily">VIIRS diária</option>
        </select>
      </div>
      {dayLayer === "viirs-daily" && (
        <div className="src">
          <SourceStatus query={gibs} env={gibs.data} />
          <div className="note">
            {viirs?.latest_date
              ? `Data mais recente publicada: ${viirs.latest_date}. ${VIIRS_DAILY.note}`
              : "Sem data confirmada pela GIBS; mantendo Blue Marble."}
          </div>
        </div>
      )}
    </div>
  );
}

function SpaceWeatherSection() {
  const sw = useSpaceWeather(true);
  const d = sw.data;
  const flares = d?.flares.data ?? [];
  const strongest = [...flares]
    .filter((f) => f.class_type)
    .sort((a, b) => classRank(b.class_type!) - classRank(a.class_type!))[0];
  const kpMax = Math.max(-1, ...(d?.storms.data ?? []).map((s) => s.kp_max ?? -1));
  const fastest = Math.max(-1, ...(d?.cmes.data ?? []).map((c) => c.analysis?.speed_ms ?? -1));

  return (
    <div className="section">
      <div className="section-title">Clima espacial (DONKI, 7 dias)</div>
      {sw.isLoading || sw.isError || !d ? (
        <SourceStatus query={sw} env={undefined} />
      ) : (
        <dl className="kv">
          <dt>Erupções solares</dt>
          <dd>
            {d.flares.data ? `${flares.length}${strongest ? ` · máx. ${strongest.class_type}` : ""}` : "—"}
          </dd>
          <dt>Tempestades geomagnéticas</dt>
          <dd>
            {d.storms.data ? `${d.storms.data.length}${kpMax >= 0 ? ` · Kp máx. ${fmt(kpMax, 1)}` : ""}` : "—"}
          </dd>
          <dt>Ejeções de massa coronal</dt>
          <dd>{d.cmes.data ? `${d.cmes.data.length}${fastest >= 0 ? ` · até ${kms(fastest, 0)}` : ""}` : "—"}</dd>
        </dl>
      )}
      {d && (
        <div className="src-list">
          <SourceStatus query={sw} env={d.flares} />
          <SourceStatus query={sw} env={d.storms} />
          <SourceStatus query={sw} env={d.cmes} />
        </div>
      )}
    </div>
  );
}

/** Classe GOES (A < B < C < M < X) com multiplicador, p. ex. "X3.9" → 4,39. */
export function classRank(c: string): number {
  const letter = "ABCMX".indexOf(c[0]?.toUpperCase() ?? "");
  const mult = Number.parseFloat(c.slice(1));
  return letter < 0 ? -1 : letter + (Number.isFinite(mult) ? Math.min(mult, 9.99) / 10 : 0);
}

export function LivePanel() {
  const open = useView((s) => s.liveOpen);
  const toggle = useView((s) => s.toggleLive);
  if (!open) return null;
  return (
    <aside className="live" aria-label="Dados externos">
      <div className="panel-head">
        <span className="panel-title">Dados externos</span>
        <button className="link" aria-label="Fechar dados externos" onClick={toggle}>
          ×
        </button>
      </div>
      <div className="panel-body">
        <EarthSection />
        <SpaceWeatherSection />
        <p className="note">
          Dados de NASA GIBS, EONET, CCMC DONKI e Open Notify, consultados pelo backend. Nada é
          preenchido quando a fonte falha.
        </p>
      </div>
    </aside>
  );
}
