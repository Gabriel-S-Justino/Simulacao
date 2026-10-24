# Desempenho

Situação: **ainda não medido em hardware de referência.** Nenhuma meta de FPS é declarada cumprida.

## Instrumentação disponível

Operações → Detalhes técnicos mostra FPS médio e percentis p95/p99 do tempo por quadro (últimos 600
quadros) e o DPR atual. O tempo de cálculo do backend é informado em cada simulação (`compute_time_ms`).

## Decisões já tomadas

- Física fora da thread de renderização (backend); a cena só interpola.
- Relógio de reprodução mutável fora do React; HUD amostrado a 10 Hz, linha do tempo a 15 Hz.
- Trajetória em `Float64Array`; linha percorrida reutiliza o mesmo buffer com `setDrawRange` (sem cópias).
- Geometrias e materiais da nave criados uma vez por montagem e descartados ao trocar.
- Vetores temporários reutilizados nos caminhos por quadro (restam alocações pequenas, como `Date`, a eliminar).
- DPR adaptativo (`PerformanceMonitor`) com limite de oscilações (3) antes de fixar em 1.
- Texturas GIBS: uma requisição WMS por camada (4096×2048), sem baixar a pirâmide de tiles.

## Cenas de referência (a medir)

| Cena | Conteúdo |
|---|---|
| A — Montagem | nave em primeiro plano, Terra fora de quadro, 9000 estrelas |
| B — Terra | Terra + atmosfera + trajetória 2000 amostras, reprodução 1000× |
| C — Acompanhamento | nave em órbita com Terra ao fundo, pluma ativa |

## Hardware de referência (a registrar)

| Classe | GPU | Navegador | Resolução | Preset | FPS médio | p95 | p99 |
|---|---|---|---|---|---|---|---|
| Entrada | — | — | 1920×1080 | — | — | — | — |
| Intermediária | — | — | 2560×1440 | — | — | — | — |
| Alta | — | — | 3840×2160 | — | — | — | — |

Observação: no ambiente de CI/servidor sem GPU (SwiftShader), o FPS não é representativo.
