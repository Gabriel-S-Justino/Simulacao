# Validação científica

Executar: `cd backend && .venv/bin/pytest -q` (55 testes, ~3 s). Com `TEST_DATABASE_URL` apontando para
um PostgreSQL, os testes de persistência rodam nele (no CI, PostgreSQL 16); sem ela, em SQLite temporário.

| Teste | Referência | Tolerância | Resultado |
|---|---|---|---|
| Ida e volta estado ↔ elementos (elíptica, Molniya, hiperbólica, retrógrada) | identidade | a: 1e-11 rel; ângulos: 1e-9 rad | passa |
| Circular equatorial (longitude verdadeira) | identidade | 1e-12 rad | passa |
| Velocidade circular e período a 400 km | 7,6686 km/s; 92,56 min | 0,1 m/s; 0,01 min | passa |
| Período geoestacionário | dia sideral 86 164,09 s | 1 s | passa |
| Velocidade de escape | 11,180 km/s (R equatorial); 11,186 km/s (R médio) | 1 m/s | passa |
| Sinal da energia por tipo de órbita | ε<0 fechada, ε>0 hiperbólica | exato | passa |
| Hohmann LEO→GEO | Vallado, 4ª ed., Exemplo 6-1 | 1 mm/s por queima; 0,1 s | passa |
| Bi-elíptica mais econômica para r₂/r₁ = 20 | teoria (limiar 15,58) | desigualdade | passa |
| Tsiolkovsky e consumo | identidade | 1e-12 rel | passa |
| Isp combinado | ΣF/Σ(F/Isp) | 1e-12 | passa |
| Propagação × Kepler analítico, 10 órbitas, e = 0,6 | solução de Kepler | 1 m; 1 mm/s | passa (≈0,4 m) |
| Conservação de energia e de h, 10 órbitas | invariantes | 1e-9 rel | passa (~2e-10) |
| Convergência com rtol 1e-7 → 1e-11 | monotonicidade | erro final < 0,5 m | passa |
| Hohmann simulada 400 → 2000 km | alvo | raio 10 m; e < 1e-6 | passa |
| Propelente de Hohmann simulada | Tsiolkovsky | 1e-12 rel | passa |
| Propelente insuficiente | Δv disponível | 1e-12 rel | passa |
| Estágios: descarte e massa final | balanço de massa | 1e-12 rel | passa |
| Queima de reentrada termina em impacto | |r| = R⊕ | 1 m | passa |
| Mudança de plano pura (1°) | geometria | 1e-12 rad | passa |
| Entradas inválidas/ilimitadas rejeitadas | — | — | passa |
| Mesma missão executada duas vezes | determinismo | trajetória idêntica bit a bit | passa |
| Retomada de checkpoint no meio da transferência e no instante da 2ª queima | execução completa | massa final 1e-12 rel; a e periapsis 1 m | passa |
| Checkpoint de outra versão do simulador | — | recusado (409) | passa |
| Migração Alembic × modelos | `alembic check` | sem diferenças | passa (PostgreSQL 16) |

Frontend (`cd frontend && npm test`): interpolação Hermite (erro relativo < 1e-4 com 16 amostras por
órbita; amostras do núcleo reproduzidas exatamente; estado pós-queima em tempos repetidos), GMST em J2000,
declinação solar nos equinócio/solstício, fallback sem WebGL 2, painel de montagem chamando o backend.
