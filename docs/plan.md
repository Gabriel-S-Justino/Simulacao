# Mission Architect — auditoria, plano e critérios (Etapa 0)

Data da auditoria: 2026-10-24.

## 1. Auditoria do repositório

O repositório continha apenas um `README.md` com o título "Simulacao" e um commit inicial. Não havia
código, dependências, CI nem configuração de deploy, portanto nada precisou ser preservado ou migrado.
A estrutura proposta no prompt mestre (seção 18) foi adotada com duas adaptações:

- O repositório já é a raiz do projeto (não há subpasta `mission-architect/`).
- Diretórios só são criados quando recebem código real (sem pastas vazias de integrações futuras).

## 2. Decisão de deploy (Vercel × FastAPI/PostgreSQL/Docker)

**Decidido em 2026-10-24: tudo na Vercel com Neon Postgres.**

O prompt pede FastAPI + PostgreSQL + Docker e "pronto para deploy na Vercel". Abordagem adotada
(reversível, sem mudanças de código para trocar):

| Ambiente | Frontend | Backend | Banco |
|---|---|---|---|
| Local | Vite (5173) com proxy `/api` | Uvicorn (8000) | PostgreSQL via Docker Compose (etapa de persistência) |
| Docker | nginx servindo o build, proxy `/api` | container Python 3.12 | idem |
| Vercel | build estático de `frontend/` | `api/index.py` como função Python (FastAPI) | Postgres gerenciado (Neon via Marketplace) |

Consequências na Vercel: funções têm tempo máximo (configurado em 60 s) e limite de pacote. Por isso o
núcleo físico já impõe limites (30 dias simulados, 32 manobras, 6000 amostras) e propagações longas
serão feitas em lotes com checkpoints. Se esse limite apertar, o mesmo container Docker do backend pode ir
para Render/Fly.io sem alteração de código; só muda a variável `VITE_API_BASE_URL`.

## 3. Plano de implementação (fatias verticais incrementais)

| # | Entrega | Critério de aceite |
|---|---|---|
| 1 (feito) | Fatia vertical: montar nave → Δv por estágio → plano Hohmann → propagação DOP853 → trajetória 3D → objetivo validado | 46 testes científicos/API e 10 de frontend passam; fluxo ponta a ponta verificado em navegador |
| 2 (feito) | Persistência: PostgreSQL, SQLAlchemy 2, Alembic; projetos, missões, checkpoints (snapshot + semente + versão), relatórios | mesma missão → trajetória idêntica bit a bit; retomada de checkpoint → massa exata e órbita final a 1 m |
| 3 | Integrações (8 adaptadores) com contrato comum §4.9, cache, timeouts, testes isolados com respostas gravadas | cada adaptador testado com: ok, timeout, HTTP 4xx/5xx, payload inválido, cache, dado desatualizado |
| 4 | Efemérides JPL Horizons + Sol/Lua reais na cena; Astropy para escalas de tempo (UTC/TDB) e referenciais (ICRF/eclíptica) | comparação com Horizons dentro de tolerância documentada |
| 5 | Comandos e operações: queimas finitas, energia (eclipse, orientação dos painéis), telecom (link budget, latência), atitude simplificada | comandos alteram estado físico e cena; energia nunca negativa silenciosamente |
| 6 | Planejamento avançado: Lambert (Izzo), janelas, porkchop, perturbações J2/arrasto como módulos | casos de referência publicados reproduzidos |
| 7 | Missões 1–5 completas, relatórios, eventos/falhas com semente, dificuldades | cada missão jogável do briefing ao relatório (teste Playwright §21.3) |
| 8 | Acabamento visual (pós-processamento seletivo, LOD, texturas comprimidas) e medição de desempenho em hardware documentado | metas da seção 10 medidas e registradas |

## 4. Riscos técnicos

| Risco | Impacto | Mitigação |
|---|---|---|
| Tempo/tamanho de função na Vercel | Propagações longas falham | Limites rígidos no núcleo; lotes + checkpoints; backend portável para container |
| Precisão float32 na GPU (cena de 1000 km/unidade) | Tremor da nave | Física em float64 no backend; nave com escala visual indicada; próximo passo: origem flutuante relativa à câmera |
| CORS/disponibilidade de GIBS no navegador | Terra sem textura | Fallback neutro sem geografia inventada; estado da camada registrado; próximo passo: proxy/cache no backend |
| Open Notify sem HTTPS e instável | Conteúdo misto / falhas | Consumir pelo backend com timeout, cache e marca de "histórico" |
| Mistura de referenciais (ECI × eclíptica × geográfico) | Erros silenciosos | Referencial explícito em todo contrato; Astropy para conversões; testes de conversão |
| Escopo muito grande | Entregas superficiais | Fatias verticais com critério de aceite verificável por etapa |
| Desempenho em hardware fraco | < 60 FPS | Medição embutida (p50/p95/p99), DPR adaptativo, presets; sem promessas sem medição |

## 5. Compatibilidade das bibliotecas científicas

| Biblioteca | Situação (out/2026) | Licença | Uso |
|---|---|---|---|
| NumPy 2.x | Mantida | BSD-3 | Vetores, estados |
| SciPy 1.18 (`solve_ivp`, DOP853) | Mantida | BSD-3 | Integração numérica com controle de erro |
| Astropy | Mantida | BSD-3 | Escalas de tempo, referenciais, unidades (etapa 4) |
| sgp4 / Skyfield | Mantidas | MIT | Propagação de TLE da ISS (etapa 3) |
| poliastro | **Arquivada em 2023** | MIT | Não usada |
| hapsira (fork do poliastro) | Manutenção incerta | MIT | Não usada; algoritmos implementados e testados localmente |
| lamberthub | Ativa | **GPL-3** | Não usada por licença; Lambert (Izzo 2015) será implementado e validado |

Mecânica orbital central (elementos, Hohmann, Tsiolkovsky, propagação) foi implementada sobre NumPy/SciPy,
com testes contra soluções analíticas e exemplos publicados (ver `validation.md`).

## 6. Contratos frontend ↔ backend

API versionada em `/api/v1`, OpenAPI em `/api/docs`. Unidades SI em todos os campos (sufixos `_m`, `_ms`,
`_kg`, `_s`, `_w`). Toda resposta do frontend é validada com Zod (`frontend/src/types/contracts.ts`).

| Endpoint | Entrada | Saída |
|---|---|---|
| `GET /health` | — | status, versão, catálogo, banco |
| `GET /catalog/components` | — | componentes (todos marcados `fictional`) |
| `POST /spacecraft/evaluate` | `{stages:[{name, parts:[{component_id, quantity, propellant_kg?}]}]}` | massas, Δv por estágio, energia, custo, confiabilidade, `issues` |
| `POST /planning/hohmann` | altitudes inicial/alvo, `design?` | Δv1, Δv2, tempo, manobras prontas, viabilidade, `provenance` |
| `POST /simulations/propagate` | projeto, órbita inicial, manobras (VNB), duração, objetivo | trajetória amostrada, eventos, órbitas inicial/final, objetivo, diagnósticos numéricos, `provenance` |

`provenance` traz `source`, `kind` (`calculated`/`observed`/`approximation`/`synthetic`), modelo,
referencial, unidades e hipóteses. Os adaptadores externos seguirão o contrato §4.9 completo.

Fontes de verdade: posição e massa da nave vêm do propagador; o frontend apenas interpola (Hermite cúbica)
entre amostras para exibição. Direção do Sol e rotação da Terra são calculadas no frontend somente para
iluminação/orientação visual (não entram na física de dois corpos).

## 7. Critérios de validação física

Ver `validation.md` para a lista completa com tolerâncias. Resumo:

- Ida e volta estado ↔ elementos (elíptica, hiperbólica, retrógrada, circular equatorial): 1e-9 rad / 1e-11 relativo.
- Propagação × Kepler analítico, 10 órbitas, e = 0,6: erro < 1 m.
- Conservação de energia e momento angular sem manobras: deriva relativa < 1e-9.
- Convergência: erro decresce monotonicamente com a tolerância.
- Hohmann: Vallado, Exemplo 6-1 (Δv total 3,935224 km/s, τ 5,256713 h) a 2 mm/s.
- Tsiolkovsky e consumo de propelente: identidade a 1e-12; estágios sequenciais, nunca soma ingênua.
- Simulação de Hohmann: órbita final circular a ±10 m do alvo.

## 8. Plano de desempenho e cenas de referência

Ver `performance.md`. Cenas: (A) montagem com nave em primeiro plano; (B) visão da Terra com trajetória de
2000 amostras e reprodução a 1000×; (C) acompanhamento da nave em órbita com Terra ao fundo. Medição embutida
(FPS médio, p50/p95/p99 do tempo por quadro) nos detalhes técnicos de Operações.

## 9. Sistema visual e regras de interface minimalista

- Cena 3D ocupa a tela inteira; painéis são vidro translúcido escuro e recolhíveis.
- Barra superior compacta: marca, fases (Montagem, Planejamento, Operações), foco da câmera, tela limpa.
- Painel lateral: 4 indicadores essenciais no topo, seguidos apenas do que a fase exige.
- HUD de voo: no máximo 4 indicadores (altitude, velocidade, propelente, próxima queima).
- Detalhes técnicos (modelo, referencial, integrador, tolerâncias, deriva, quadros) só sob demanda.
- Tipografia: Inter para rótulos, JetBrains Mono para valores; números sempre com unidade.
- Cores com significado: âmbar = alvo/atenção, azul = trajetória, verde = sucesso, vermelho = erro.
- Tela limpa (tecla C) oculta painéis e HUD sem tocar no estado da missão.
- Nenhum botão sem comportamento: fases ainda não implementadas não aparecem na navegação.
