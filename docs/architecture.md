# Arquitetura

## Camadas

```
frontend/ (React + TS estrito + Vite)            backend/ (FastAPI + Pydantic v2)
  features/      painéis por fase                  api/v1/routes.py   endpoints versionados
  rendering/     cena Three.js (R3F)               services/flight.py orquestra projeto→plano→voo
  services/      cliente HTTP + TanStack Query     domain/            física pura, sem I/O
  stores/        Zustand (UI) + relógio mutável      orbital_mechanics/  elementos, manobras
  types/         contratos Zod                       propulsion/         Tsiolkovsky
                                                     spacecraft/         catálogo, avaliação
                                                   simulation/        propagador DOP853
data/catalogs/   catálogo de componentes (JSON, fictício)
api/index.py     entrada da função Python na Vercel
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

Ainda não implementada (próxima etapa). Plano: PostgreSQL com projetos, missões, planos, checkpoints
(snapshot de estado + semente + versão do simulador + configuração física), eventos e relatórios.
