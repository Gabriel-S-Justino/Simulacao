# Arquitetura

## Camadas

```
frontend/ (React + TS estrito + Vite)            backend/ (FastAPI + Pydantic v2)
  features/      painéis por fase                  api/v1/routes.py   endpoints versionados
                                                   api/v1/sources.py  fontes externas (envelope §4.9)
                                                   integrations/      adaptadores HTTP, cache, stale
  rendering/     cena Three.js (R3F)               services/flight.py orquestra projeto→plano→voo
  services/      cliente HTTP + TanStack Query     domain/            física pura, sem I/O
  stores/        Zustand (UI) + relógio mutável      orbital_mechanics/  elementos, manobras
  types/         contratos Zod                       propulsion/         Tsiolkovsky
                                                     spacecraft/         catálogo, avaliação
                                                   simulation/        propagador DOP853
backend/app/catalogs/   catálogo de componentes (JSON, fictício; empacotado com o app)
vercel.json             Vercel Services: frontend (Vite) em /, backend (FastAPI) em /api/*
```

O núcleo científico (`backend/app/domain`, `backend/app/simulation`) não depende de FastAPI e é testado
isoladamente.

## Fluxo de dados da fatia vertical

1. Montagem: o estado da nave (peças e propelente) fica no Zustand. Cada alteração (com debounce de 150 ms)
   chama `POST /spacecraft/evaluate`; massa, Δv e energia exibidos vêm do backend.
2. Planejamento: `POST /planning/hohmann` devolve Δv, tempo e manobras prontas, com viabilidade frente ao Δv
   disponível do projeto.
3. Simulação: `POST /simulations/propagate` executa a propagação numérica com as manobras, consome
   propelente por estágio e avalia o objetivo.
4. Cena: a trajetória vira `Float64Array`s; um relógio de reprodução mutável (fora do React) avança a cada
   quadro; nave, câmera e linha percorrida leem o estado interpolado. O HUD amostra a 10 Hz.

## Tempos separados

- Tempo de integração: passos adaptativos do DOP853 (backend), independentes de quadros.
- Tempo da missão: `t` em segundos desde o início, nas amostras.
- Tempo de renderização: `dt` do quadro × aceleração (1×–1000×), limitado a 0,1 s por quadro.

## Referenciais

Ver `physics-models.md`. Física em ECI (Z norte, metros). Cena Y-up: `(x, z, −y) / 10⁶`.
A nave é desenhada com escala visual ×1500 (indicada na tela). Coordenadas visuais nunca voltam à física.

## Persistência

PostgreSQL via SQLAlchemy 2 (psycopg 3) e migrações Alembic (`backend/alembic`). Sem `DATABASE_URL`, as
rotas de missões respondem 503 e o restante da API funciona (o frontend simula sem salvar).

| Tabela | Conteúdo |
|---|---|
| `projects` | agência/projeto do jogador |
| `missions` | projeto da nave, órbita inicial, objetivo, manobras, duração, configuração física (modelo, integrador, tolerâncias), semente, versão do simulador |
| `checkpoints` | snapshot do estado físico num instante: posição, velocidade, massa e estágios restantes (propelente queimável, Isp, empuxo, massa descartável) |
| `mission_runs` | relatório de cada execução: resumo, eventos, objetivo, diagnósticos (sem as amostras da trajetória) |

Decisões:

- A trajetória não é gravada passo a passo: é reproduzível a partir do plano, da versão do simulador, da
  configuração física e da semente. Só os relatórios (até 20 por missão) e os checkpoints (até 50) são gravados.
- Alterar o plano (projeto, órbita, objetivo, manobras, duração, semente ou integrador) remove checkpoints e
  relatórios, que deixariam de corresponder à missão. Renomear não invalida.
- Checkpoint gravado com outra versão do simulador não é retomado (409): é preciso replanejar.
- Na Vercel, `DATABASE_POOLING=false` usa `NullPool`; o pooler do Neon gerencia as conexões.

API (todas em `/api/v1`): `GET/POST /projects`; `GET/POST /missions`; `GET/PATCH/DELETE /missions/{id}`;
`POST /missions/{id}/validate`, `/plan`, `/run`; `GET /missions/{id}/state`;
`GET/POST /missions/{id}/checkpoints`; `POST /missions/{id}/checkpoints/{ck}/resume`;
`GET /missions/{id}/reports`.
