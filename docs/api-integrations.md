# Integrações externas

Situação por fonte (verificação: 2026-10-24):

| Fonte | Estado | Observação |
|---|---|---|
| NASA GIBS | Parcial: frontend carrega Blue Marble e Black Marble via WMS (EPSG:4326) | **Não verificado** neste ambiente (rede bloqueada). Falha registrada e Terra exibida sem geografia inventada. Adaptador no backend com cache na etapa 3. |
| NASA EPIC | Não implementado | etapa 3 |
| NASA DONKI | Não implementado | etapa 3 |
| NASA EONET | Não implementado | etapa 3 |
| JPL SSD/CNEOS (Horizons, SBDB, CAD) | Não implementado | etapas 3–4 |
| NASA APOD | Não implementado | etapa 3 |
| NASA NeoWs | Não implementado | etapa 3 |
| Open Notify (ISS) | Não implementado | etapa 3; endpoint histórico é HTTP, consumo será pelo backend |

Todos os adaptadores seguirão o contrato comum §4.9 (`source`, `status`, `fetched_at`, `observed_at`,
`valid_time_start`, `valid_time_end`, `stale`, `units`, `reference_frame`, `uncertainty`, `data`, `error`),
com timeouts, cache e testes com respostas gravadas. Chaves ficam no backend (`NASA_API_KEY`).
