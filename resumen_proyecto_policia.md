# Modelo de crimen con policía como campo conservado — resumen del proyecto

*Resumen de la sesión de trabajo (junio 2026). Proyecto basado en la réplica de Short et al. (2008), Fig. 3(d), extendida con presencia policial.*

## 1. Punto de partida

Partimos del notebook que replica el modelo discreto de Short et al., *A Statistical Model of Criminal Behavior* (M3AS, 2008), en el régimen de hotspots dinámicos de la Fig. 3(d): red 128×128, δt=1/100, ω=1/15, A⁰=1/30, η=0.03, θ=5.6, Γ=0.002. El objetivo era añadir policía de forma sencilla, con espíritu Lotka-Volterra: B (atractividad dinámica) como presa y M (presencia policial) como predador.

## 2. El modelo final

Decisiones de diseño, en orden de discusión:

1. **M es un campo escalar, no agentes.** Más barato (una operación vectorizada por paso), determinista dado E (la única estocasticidad queda en los criminales) y analizable (punto fijo homogéneo, estabilidad lineal). Análogo en espíritu al "cops on the dots" de Jones et al. (2010).
2. **ΣM se conserva exactamente.** La policía no nace ni muere: se redistribuye. M_tot es el presupuesto policial.
3. **M depende de B solo a través de E** (los crímenes observados). B es un campo latente que la policía no puede medir; E es lo que ve. Evitamos el término αBM del LV clásico.
4. **B siente a M solo vía disuasión** ("perception modification" de Jones et al., Sec. 2.1.1), aplicada **solo a la componente dinámica**: el A⁰ intrínseco (riqueza, accesibilidad) no se puede patrullar. Implicación: la disuasión satura — la policía devuelve el crimen al nivel de fondo, nunca a cero.
5. **La probabilidad de robo se mantiene como en Short** (p = 1−e^{−Ãδt}), no como en Jones (Ã/(1+Ã)): son casi idénticas numéricamente y así χ=0 reproduce la réplica base exactamente.

Ecuaciones:

$$\tilde A_s = A^0 + B_s\,e^{-\chi M_s}, \qquad p_s = 1-e^{-\tilde A_s \delta t}, \qquad q_{s\to s'} = \tilde A_{s'}/\textstyle\sum_r \tilde A_r$$

$$B_s(t+\delta t) = \Big[(1-\eta)B_s + \tfrac{\eta}{z}\textstyle\sum_{s'}B_{s'}\Big](1-\omega\delta t) + \theta E_s \quad \text{(igual que Short)}$$

$$M_s(t+\delta t) = (1-\omega_M\delta t)\Big[(1-\eta_M)M_s + \tfrac{\eta_M}{z}\textstyle\sum_{s'}M_{s'}\Big] + \omega_M\delta t\, M_{tot}\,\frac{E_s}{\sum_r E_r}$$

Parámetros nuevos: χ (disuasión), η_M (patrulla difusiva), ω_M (tasa de redespliegue), M_tot. La conservación es exacta (difusión conserva masa en red periódica + combinación convexa). Nota de escalas: M y A tienen unidades distintas; solo importan los productos adimensionales χM (y κM si hay arrestos). El parámetro de control efectivo es χ·M_tot.

**Verificación:** ΣM = M_tot en los 73.000 pasos; con χ=0 y la misma semilla, el campo B coincide bit a bit con la réplica de Fig. 3(d).

## 3. Resultados

**Run de referencia** (χ=1, M_tot=500, η_M=0.1, ω_M=1/15, 730 días): reducción modesta del crimen (252→229), hotspots persistentes. Diagnóstico: en los núcleos hace falta χM ≳ ln(B/A⁰) ≈ 3–5 y el χM real era ~0.04.

**Asimetría viejos/nuevos hotspots.** La policía aborta hotspots nacientes pero no mata los consolidados: (i) la supresión es multiplicativa y los núcleos tienen B alto; (ii) la reasignación ∝E aterriza en la casilla del crimen justo durante la ventana crítica de consolidación (1/ω ≈ 15 días), bloqueando la victimización repetida de los nuevos; (iii) en un hotspot maduro, M ~ constante sobre el núcleo se cancela en el cociente del sesgo de movimiento y no expulsa a los criminales ya atrapados; el hotspot se desplaza en vez de morir. Esto reproduce el resultado supresión-vs-desplazamiento de Short et al. (PNAS 2010) — es un resultado, no un bug.

**Artefacto de conservación del crimen.** Con policía muy fuerte (M_tot=200.000) la población criminal explota (~936) y el crimen se difumina sin reducirse: en el modelo de Short un criminal solo sale del sistema robando, así que el crimen estacionario está fijado por la entrada Γ·L² y la disuasión solo lo retrasa y lo esparce. Solución pendiente: canal de salida sin robo — el δ de Jones ("return home") o, mejor, arresto dependiente de policía, p_rem = 1−e^{−κMδt}, que además permite que la policía drene hotspots maduros.

**Barrido en χ** (χ ∈ {0,1,3,10,30,100,300}, M_tot=500, 3 semillas, 365 días, promedio sobre t∈[185,365]):

| χ | std(B)/⟨B⟩ | criminales |
|------|------|------|
| 0 | 1.56 | 69 |
| 1 | 1.55 | 74 |
| 3 | 1.49 | 81 |
| 10 | 1.39 | 117 |
| 30 | 1.05 | 275 |
| 100 | 0.83 | 807 |
| 300 | 0.83 | 977 |

Dos fases con zona de transición en **χ_c ≈ 20–50, es decir χ·M̄ ≈ 1** (M̄ = M_tot/L²): fase de hotspots (plateau ~1.56) y fase difusa (plateau ~0.83). La fracción de área de hotspots colapsa de 0.125 a 0.045 entre χ=10 y 100. **Sin histéresis** (ramas con inicio homogéneo y con hotspots preformados coinciden) → transición continua/supercrítica, consistente con que 3(d) está en régimen supercrítico. El proxy de susceptibilidad no muestra pico → apunta a crossover; test decisivo pendiente: comparar L=64 vs 128 (una transición real se afila con L).

## 4. Pendiente / siguientes pasos

- Añadir el canal de arresto κ y comparar mecanismos: solo-disuasión vs solo-arresto vs ambos. Con κ el crimen total vuelve a ser un parámetro de orden válido.
- Test de tamaño finito (L=64 vs 128) para distinguir transición de crossover.
- Predicción analítica de χ_c: con M uniforme la disuasión es un reescalado B→Be^{−χM̄} en el análisis de estabilidad lineal del modelo continuo (Eqs. 82–83 de la review de Jusup et al.).
- Email a Jones/Brantingham/Chayes (borrador listo: `email_to_jones_et_al.md`); considerar copiar a Martin Short (Georgia Tech).

## 5. Referencias

Short et al., M3AS 18 (2008) — modelo base. Jones, Brantingham & Chayes, M3AS 20 (2010) 1397–1423 — policía como agentes, disuasión. Short, Brantingham, Bertozzi & Tita, PNAS 107 (2010) 3961–3965 — supresión vs desplazamiento. Pitcher, Eur. J. Appl. Math. 21 (2010) — policía en PDE. Zipkin, Short & Bertozzi, DCDS-B 19 (2014) — cops on the dots. Jusup et al., Phys. Rep. 948 (2022), Sec. 8.2 — review.

## 6. Archivos

`crime_model_police_extension.ipynb` (réplica + secciones 8 policía y 9 barrido/histéresis, con GIFs), `figures_police/` (mapas comparativos, series temporales, barrido, histéresis, GIFs χ=0 y χ=30), `chi_sweep.csv` y `chi_hysteresis.csv` (datos del barrido), `email_to_jones_et_al.md`.
