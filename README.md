# Mission Architect

Simulador de engenharia e operações espaciais: monte uma nave, calcule seu desempenho, planeje uma
manobra, simule o voo com mecânica orbital numérica e acompanhe tudo numa cena 3D em WebGL 2.

Estado atual: **primeira fatia vertical** (ver `docs/plan.md` para o plano completo e as próximas etapas).

## Funcionalidades desta etapa

- Montagem modular a partir de um catálogo (fictício) com massa, Δv por estágio (Tsiolkovsky), energia,
  custo, confiabilidade e verificação de compatibilidade.
- Planejamento de transferência de Hohmann com viabilidade frente ao Δv disponível.
- Propagação de dois corpos com DOP853 (passo adaptativo), manobras impulsivas, consumo de propelente,
  descarte de estágios, detecção de impacto e diagnósticos de conservação.
- Cena Three.js: Terra com camadas NASA GIBS (quando disponíveis), atmosfera, Sol na posição calculada,
  campo estelar ilustrativo, nave gerada a partir da montagem, trajetória e reprodução 1×–1000×.
- Interface minimalista: três fases, painel recolhível, HUD de 4 indicadores, tela limpa (C).
- Persistência em PostgreSQL: missões salvas, relatórios de execução e checkpoints que podem ser retomados
  com resultado reprodutível.

## Tecnologias

Frontend: React 19, TypeScript estrito, Vite, Three.js, React Three Fiber, Drei, Zustand, TanStack Query,
Zod, Vitest, Testing Library. Backend: Python 3.12, FastAPI, Pydantic v2, NumPy, SciPy, SQLAlchemy 2, Alembic, PostgreSQL, Pytest, Ruff, mypy.

## Instalação e execução

Requisitos: Python 3.12+, Node 22+.

Linux/macOS:

```bash
cp .env.example .env
./scripts/dev.sh          # API em :8000, app em http://localhost:5173
```

Windows (PowerShell):

```powershell
copy .env.example .env
./scripts/dev.ps1
```

Manual:

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload --port 8000
cd ../frontend && npm ci && npm run dev
```

Docker: `docker compose up --build` → app em http://localhost:8080, API em http://localhost:8000
(documentação OpenAPI em `/api/docs`).

## Testes

```bash
./scripts/test.sh   # ruff, mypy, pytest, tsc, vitest, build
```

## Deploy na Vercel com Neon

1. Importe o repositório na Vercel (raiz do repositório). O build estático vem de `frontend/` e
   `api/index.py` expõe o FastAPI como função Python em `/api/*` (ver `vercel.json`).
2. Adicione o Neon pelo Marketplace da Vercel (Storage → Neon). Ele cria `DATABASE_URL` (com pooler).
3. Em Environment Variables, defina `DATABASE_POOLING=false` e `CORS_ORIGINS=https://<seu-domínio>`.
4. Aplique as migrações com a URL direta do Neon (sem `-pooler`):
   `DATABASE_URL=<url-direta> ./scripts/migrate.sh`.
5. Confira `GET /api/v1/health`: `"database": "ok"`.

Sem banco, a aplicação continua funcionando; apenas missões e checkpoints não são salvos.

## Documentação

`docs/plan.md` (auditoria, plano, riscos, contratos), `docs/architecture.md`, `docs/physics-models.md`,
`docs/validation.md`, `docs/performance.md`, `docs/api-integrations.md`, `docs/user-guide.md`.

## Solução de problemas

- "WebGL 2 indisponível": ative a aceleração por hardware ou atualize o navegador/driver.
- Terra sem continentes: as camadas GIBS não carregaram (rede/CORS). A simulação não é afetada.
- "Servidor indisponível": confira se a API está em :8000 (o Vite faz proxy de `/api`).
