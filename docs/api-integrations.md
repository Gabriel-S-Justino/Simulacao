# Integrações externas

Todas as fontes são consultadas **pelo backend** (`backend/app/integrations/`). O navegador nunca recebe a
chave da NASA e nunca chama o Open Notify (HTTP). A única exceção são as imagens da GIBS, que são públicas,
não exigem chave e são baixadas direto pelo navegador para não passar megabytes pela função da Vercel.

## Situação (2026-10-24)

| Fonte | Endpoint desta API | Implementado | Testes isolados | Verificado ao vivo |
|---|---|---|---|---|
| NASA GIBS (WMTS GetCapabilities) | `GET /api/v1/earth/imagery/layers` | sim | sim | **não** |
| NASA GIBS (imagens WMS, no navegador) | — | sim (Blue Marble, Black Marble, VIIRS diária) | URL testada | **não** |
| NASA EPIC | `GET /api/v1/earth/epic?date=` | sim | sim | **não** |
| NASA DONKI (FLR, GST, CME) | `GET /api/v1/events/space-weather?days=` | sim | sim | **não** |
| NASA EONET v3 | `GET /api/v1/events/earth?days=&limit=&status=&category=` | sim | sim | **não** |
| JPL Horizons (vetores) | `GET /api/v1/ephemerides?target=&center=&start=&stop=&step=` | sim | sim | **não** |
| JPL SBDB | `GET /api/v1/small-bodies?q=` | sim | sim | **não** |
| JPL CNEOS CAD | `GET /api/v1/asteroids/close-approaches?days=&dist_max_au=` | sim | sim | **não** |
| NASA NeoWs (feed) | `GET /api/v1/asteroids/feed?start=&end=` | sim | sim | **não** |
| NASA APOD | `GET /api/v1/apod?date=` | sim | sim | **não** |
| Open Notify (ISS) | `GET /api/v1/iss/position` | sim | sim | **não** |
| Estado de configuração | `GET /api/v1/sources` | sim (sem rede) | sim | — |

**Por que nada foi verificado ao vivo:** o ambiente de desenvolvimento usado nesta etapa bloqueia todos os
hosts (api.nasa.gov, epic.gsfc.nasa.gov, eonet.gsfc.nasa.gov, kauai.ccmc.gsfc.nasa.gov,
ssd-api.jpl.nasa.gov, ssd.jpl.nasa.gov, gibs.earthdata.nasa.gov, api.open-notify.org). As chamadas reais
nesse ambiente retornam `status: "error"` com `code: "connection"`, como esperado. Os testes usam respostas
montadas a partir da documentação oficial (`backend/app/tests/external_fixtures.py`), **não gravações**.

Pontos que só a verificação ao vivo confirma (formato assumido a partir da documentação ou do uso público):

- Horizons: ordem e nomes das colunas do CSV de vetores. O parser lê o cabeçalho (`JDTDB, …, X, Y, Z, VX,
  VY, VZ`) em vez de supor posições; se o cabeçalho não vier, a resposta é `invalid_payload`.
- DONKI: nomes dos campos FLR/GST/CME (`flrID`, `beginTime`, `classType`, `allKpIndex`, `cmeAnalyses`…).
- EPIC: unidade dos vetores `*_j2000_position` (assumida km).
- NeoWs: números enviados como strings (o parser aceita número ou string numérica).
- GIBS: tamanho do GetCapabilities (limite de 64 MB por segurança).

Para verificar: com rede liberada, rode o backend e chame cada endpoint; `status` deve ser `ok` e `data`
preenchido. Registre aqui a data e o resultado por fonte.

## Contrato comum (§4.9)

Toda rota de fonte externa responde HTTP 200 com o envelope abaixo; o estado da **fonte** fica em `status`.
Parâmetros inválidos desta API dão 422.

| Campo | Significado |
|---|---|
| `source` | nome da fonte (p. ex. `NASA DONKI GST`) |
| `status` | `ok`, `stale` (fonte falhou; servindo última cópia válida), `error` (falhou e não há cópia), `not_configured` (falta chave; nenhuma requisição feita) |
| `fetched_at` | quando o dado foi obtido da fonte (numa cópia em cache, a hora original) |
| `observed_at` | instante da observação, quando a fonte informa |
| `valid_time_start`, `valid_time_end` | janela de validade/abrangência do dado |
| `stale` | `true` quando o dado é uma cópia antiga servida por falha da fonte |
| `units` | unidade de cada campo numérico (SI, salvo quando indicado) |
| `reference_frame` | referencial ou sistema de coordenadas |
| `uncertainty` | o que a fonte publica (ou não) sobre incerteza |
| `data` | dado normalizado, ou `null` |
| `error` | `{code, message, retryable, http_status, candidates}` |
| `notes` | avisos de qualidade (p. ex. "não oficial", DEMO_KEY em desenvolvimento, TDB) |
| `attribution` | crédito exigido/recomendado pela fonte |

Códigos de erro: `timeout`, `connection`, `http_error`, `auth` (401/403), `rate_limited` (429), `not_found`,
`ambiguous` (p. ex. SBDB HTTP 300), `invalid_payload`, `not_configured`.

## Cliente HTTP, cache e dados desatualizados

`backend/app/integrations/http.py`:

- Timeout por requisição: `EXTERNAL_TIMEOUT_SECONDS` (padrão 10 s). Redirecionamentos seguidos.
- Limite de tamanho da resposta (padrão 5 MB; GIBS 64 MB; Open Notify 64 kB), lido em streaming.
- Validação com Pydantic dos campos documentados; campos extras ignorados; URLs que serão exibidas precisam
  ser http(s).
- Cache em memória por processo (LRU, 256 entradas), com TTL por fonte:

TTLs com os valores padrão (os de DONKI, EONET e CAD nunca passam de `NASA_CACHE_TTL_SECONDS`):

| Fonte | TTL | Cópia "stale" aceita por até |
|---|---|---|
| GIBS capabilities | 6 h | `EXTERNAL_MAX_STALE_SECONDS` (7 d) |
| EPIC, APOD, NeoWs | `NASA_CACHE_TTL_SECONDS` (1 h) | 7 d |
| DONKI | 15 min | 7 d |
| EONET | 30 min | 7 d |
| Horizons, SBDB | 24 h | 7 d |
| CAD | 1 h | 7 d |
| ISS | `ISS_UPDATE_INTERVAL_SECONDS` (15 s) | 5 min |

- Respostas definitivas (`not_found`, `ambiguous`) nunca são cobertas por cópia antiga.
- Na Vercel cada instância da função tem seu próprio cache e ele some quando a instância é reciclada; isso
  reduz chamadas repetidas, mas não garante cópia "stale" após uma inatividade longa.

## Chaves e segredos

- `NASA_API_KEY` só no backend (variável de ambiente). APOD, NeoWs e DONKI usam api.nasa.gov.
- Em produção (`APP_ENV=production`), sem chave ou com `DEMO_KEY`, essas três fontes respondem
  `not_configured` sem fazer requisição. Em desenvolvimento, sem chave, usa-se `DEMO_KEY` com aviso em `notes`.
- O valor de `api_key` é removido dos logs do httpx (`api_key=***`) e nunca aparece em mensagens de erro, que
  citam só host e caminho. Teste: `test_api_key_sent_but_never_echoed`.

## Fontes

### NASA GIBS
- Docs: https://nasa-gibs.github.io/gibs-api-docs/access-basics/
- Backend lê `wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml` e extrai, só das camadas usadas, título, formato
  e a dimensão `Time` (`Default`, `Value`). `latest_date` é o fim do último intervalo de `Value`.
- O GetCapabilities lista só os 100 períodos mais recentes por camada (documentado).
- Frontend: Blue Marble (composto estático), Black Marble (2016) e VIIRS SNPP cor verdadeira diária. A VIIRS
  só é pedida com a data confirmada pelo backend; sem ela, mantém-se a Blue Marble.
- Crédito: "We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse Services
  (GIBS), part of NASA's Earth Science Data and Information System (ESDIS)."

### NASA EPIC
- Docs: https://epic.gsfc.nasa.gov/about/api — direto em epic.gsfc.nasa.gov (sem chave).
- `api/natural` (mais recente) ou `api/natural/date/YYYY-MM-DD`. Cada imagem traz instante UTC, centroide
  (lat/lon) e vetores J2000 geocêntricos de DSCOVR, Lua e Sol. URLs do arquivo montadas conforme a doc
  (`archive/natural/YYYY/MM/DD/{png,jpg,thumbs}/`), com o nome da imagem validado.

### NASA DONKI
- Docs: https://api.nasa.gov (DONKI) e https://kauai.ccmc.gsfc.nasa.gov/DONKI/
- FLR (classe GOES, início/pico/fim, localização), GST (série Kp e Kp máximo), CME (análise marcada como mais
  precisa: velocidade em m/s, meia-abertura, tipo). Intervalo máximo de 30 dias. Corpo vazio = sem eventos.

### NASA EONET v3
- Docs: https://eonet.gsfc.nasa.gov/docs/v3
- Eventos com categorias, fontes e geometrias (Point ou Polygon). Para polígonos, o ponto de exibição é a
  média dos vértices do anel externo, marcado `point_method: "polygon_vertex_mean"` (não vem da fonte).
- A NASA alerta que o EONET não é fonte oficial de posição/horário precisos; isso vai em `notes`.

### JPL Horizons
- Docs: https://ssd-api.jpl.nasa.gov/doc/horizons.html
- `EPHEM_TYPE=VECTORS`, `VEC_TABLE=2`, `REF_PLANE=FRAME`, `REF_SYSTEM=ICRF`, `OUT_UNITS=KM-S`,
  `CSV_FORMAT=YES`. Saída em m e m/s, no equador ICRF (mesma orientação do ECI J2000 do simulador),
  origem `center` (padrão `500@399`, geocentro).
- Instantes em TDB (data juliana e texto do calendário). Não são convertidos para UTC (exigiria tabela de
  segundos bissextos; Astropy entra na etapa 4).
- Limites: alvo/centro com caracteres restritos; passo `N m|h|d`; no máximo 5000 amostras.

### JPL SBDB
- Docs: https://ssd-api.jpl.nasa.gov/doc/sbdb.html — `sstr=…&full-prec=true`.
- Elementos com sigma (1σ); `a`, `q`, `ad` e MOID convertidos de au para m (au IAU 2012 = 149 597 870 700 m).
- HTTP 300 → `ambiguous` com até 20 candidatos; sem `object` → `not_found`.

### JPL CNEOS CAD
- Docs: https://ssd-api.jpl.nasa.gov/doc/cad.html — `date-min=now`, `date-max=+N`, `dist-max`, `diameter`,
  `fullname`.
- Distâncias nominal e 3σ em m, velocidades em m/s, instante em TDB, incerteza do instante como texto da fonte.

### NASA NeoWs
- Docs: https://api.nasa.gov (Asteroids - NeoWs). Feed de até 7 dias.
- Diâmetro estimado (faixa min-max a partir de H), velocidade relativa e distância de passagem em SI.
- A escala de tempo de `epoch_date_close_approach` não é documentada; avisado em `notes`. Para análise, o CAD
  é a fonte primária.

### NASA APOD
- Docs: https://github.com/nasa/apod-api. Datas de 1995-06-16 até hoje. Conteúdo editorial, não científico.
- Exposto na API; ainda sem uso na interface.

### Open Notify (ISS)
- Docs: https://open-notify-api.readthedocs.io — `iss-now.json`. Serviço comunitário, não oficial da NASA.
- Só latitude/longitude do subponto e instante; sem altitude nem incerteza. O globo mostra o subponto.

## Interface

O botão "Dados externos" abre um painel com:

- Eventos naturais abertos (EONET, 30 dias) como pontos coloridos por categoria no globo, na posição mais
  recente de cada evento; pontos no hemisfério oposto à câmera não são desenhados.
- Subponto da ISS, atualizado a cada 15 s enquanto ativo.
- Textura diurna: Blue Marble ou VIIRS diária (data da GIBS).
- Resumo de clima espacial dos últimos 7 dias (quantidade de erupções e classe máxima, tempestades e Kp
  máximo, CMEs e maior velocidade).

Cada item mostra a fonte, o estado (`ok`, em cache, indisponível, não configurado), quando foi obtido e o
erro, se houver. Com a fonte fora do ar, os valores aparecem como "—"; nada é preenchido. Marcadores e
textura diária ficam desligados por padrão e só consultam o backend quando ativados.
