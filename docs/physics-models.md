# Modelos físicos

Unidades SI internamente (m, s, kg, m/s, rad). Constantes em `backend/app/domain/constants.py`:
μ⊕ = 3,986004418×10¹⁴ m³/s² (EGM2008/IERS), R⊕ = 6 378 137 m (WGS-84), g₀ = 9,80665 m/s².

## Referencial

ECI centrado na Terra, eixos tipo J2000. A rotação da Terra não afeta a dinâmica (Terra como massa pontual
esférica). A orientação visual da Terra usa GMST (IAU 1982) e a direção do Sol usa a fórmula de baixa
precisão do Astronomical Almanac (~0,01°); ambas são apenas visuais.

## Dinâmica

r̈ = −μ r / |r|³ (dois corpos). Perturbações (J2, arrasto, terceiro corpo, pressão de radiação) ainda não
modeladas: serão módulos opcionais.

## Integrador

`scipy.integrate.solve_ivp`, método DOP853 (Runge-Kutta 8(5,3) de Dormand-Prince, passo adaptativo).
Padrões: rtol = 1e-11, atol = 1e-6 m (posição) e 1e-9 m/s (velocidade). Intervalo permitido de rtol:
[1e-13, 1e-6]. Evento terminal de impacto em |r| = R⊕. Saída densa para amostragem uniforme, mais as
amostras exatas antes e depois de cada manobra.

## Manobras

Impulsivas, no referencial local VNB (V = velocidade, N = normal ao plano, B = V×N). O consumo usa
Tsiolkovsky com a massa atual: m_p = m (1 − e^(−Δv / (Isp g₀))). Quando um estágio esgota, é descartado
(massa seca e propelente não queimável) e a queima continua no estágio seguinte. Sem propelente, a parte
restante não é executada e um evento `propellant_depleted` registra o Δv faltante.

A duração finita estimada de cada queima (m_p / ṁ) é registrada; se exceder 5% do período orbital, o evento
`finite_burn_warning` indica que a aproximação impulsiva perde precisão.

## Desempenho da nave

- Δv por estágio: Isp_ef · g₀ · ln(m₀/m_f), com m₀ incluindo os estágios superiores.
- Isp efetivo de motores simultâneos: ΣF / Σ(F/Isp).
- Δv total = soma dos Δv sequenciais dos estágios (não a soma por motor).
- Energia: geração dos painéis a 1 UA, incidência normal, início de vida; consumo nominal dos componentes
  do estágio final. Déficit é erro de projeto.
- Confiabilidade: produto das confiabilidades (independência assumida).

## Planejamento

Hohmann coplanar entre órbitas circulares (analítico). Bi-elíptica disponível no domínio.
Não há otimização global; nenhuma trajetória é declarada ótima.

## Limitações conhecidas

- Sem perturbações; sem eclipse no balanço de energia; sem modelo de atitude (a orientação da nave na cena é
  apenas visual: +Y na direção da velocidade, +Z para o nadir).
- Órbita inicial sempre circular, RAAN = 0, argumento de latitude = 0.
- Mudança de plano só via componente N manual (API), sem planejador dedicado.
