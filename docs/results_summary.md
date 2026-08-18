# SlopeMPM — Final Results Summary

## Research question

**How do hydrologically informed soil weakening and progressive toe erosion interact to control slope mobilization and post-disturbance response?**

This study uses a two-dimensional Material Point Method (MPM) slope model with Mohr–Coulomb plasticity. Hydrological effects are represented through independently preconditioned strength states rather than transient infiltration. Toe erosion is represented by prescribed geometric removal of material points and is not a wave-resolved erosion model.

---

## 1. Verified baseline

The dry/intact slope reached a stable self-weight equilibrium.

Key checks:

- Material points: 3,570
- Body area: 146.603 m²
- Weight: 2,876.342 kN/m
- Bottom reaction: 2,876.343 kN/m
- Force-balance error: approximately 0%
- Mean displacement: 11.811 mm
- P95 displacement: 24.459 mm
- Maximum displacement: 25.703 mm
- Maximum equivalent plastic strain: 0
- Plastic MPs above 1e-4: 0%

The baseline therefore provides a mechanically stable reference state for subsequent strength and erosion experiments.

---

## 2. Strength-reduction screening

Strength was reduced using

\[
c_F = \frac{c_0}{F},
\]

and

\[
\tan \phi_F = \frac{\tan \phi_0}{F}.
\]

This screening is **not interpreted as a formal factor-of-safety calculation**.

Under the validated incremental gravity-ramp setup:

- F = 1.58 reached full self-weight equilibrium.
- F = 1.59 failed to converge at the final full-gravity increment under a 100-iteration Newton budget.
- The F = 1.59 final residual increased toward approximately 2.42e-2 rather than approaching the 1e-4 convergence tolerance.

The resulting model-specific equilibrium transition is therefore bracketed between:

\[
1.58 < F_{\mathrm{transition}} \leq 1.59
\]

for this numerical setup.

F = 1.58 was selected as the near-transition preconditioned weakened state.

---

## 3. Dynamic stability of the F = 1.58 state

The equilibrated F = 1.58 state was restarted dynamically with the quasi-static pseudo-velocity removed.

Over the initial dynamic continuation:

- P95 displacement: 0.00335 mm
- Maximum displacement: 0.00382 mm
- P95 speed: 7.57e-5 m/s
- Robust front advance: approximately 0 m
- Plastic MPs above 1e-4: 19.58%

The plasticity was already present in the equilibrium state. During the dynamic continuation:

- Maximum added equivalent plastic strain: 8.22e-7
- MPs with added plastic strain above 1e-5: 0%

Hence the F = 1.58 state contains localized yielding but does not exhibit self-sustaining movement before toe erosion is imposed.

---

## 4. Independent single-stage toe erosion

Toe recession is described by

\[
E_t = \frac{e}{H},
\]

where \(e\) is the horizontal toe recession and \(H=10\) m is the slope height.

Each single-stage case starts independently from the same equilibrated F = 1.58 state.

| Et | Toe recession (m) | Final P95 displacement (mm) | Peak P95 speed (m/s) | New plastic MPs (%) |
|---:|---:|---:|---:|---:|
| 0.10 | 1.0 | 0.044 | 0.00301 | 11.13 |
| 0.15 | 1.5 | 0.127 | 0.00639 | 19.20 |
| 0.20 | 2.0 | 0.313 | 0.01115 | 24.09 |
| 0.25 | 2.5 | 0.686 | 0.01989 | 30.53 |
| 0.30 | 3.0 | 1.142 | 0.02805 | 35.36 |

Increasing toe recession produces a systematic increase in:

- bulk displacement,
- dynamic velocity response,
- and plastic mobilization.

However, all tested single-stage cases show an early velocity peak followed by decay rather than sustained acceleration.

No self-sustaining runout was observed.

---

## 5. Progressive toe erosion

A progressive erosion sequence was also applied to the same preconditioned F = 1.58 slope:

\[
E_t =
0.10
\rightarrow
0.15
\rightarrow
0.20
\rightarrow
0.25
\rightarrow
0.30.
\]

The intervals between geometric erosion stages are numerical relaxation intervals and are **not interpreted as a physical coastal erosion rate**.

At the final \(E_t=0.30\):

- Final P95 displacement: 0.836 mm
- Peak P95 speed: 0.01100 m/s
- Final new-plastic MPs: 33.76%
- Maximum added equivalent plastic strain: 1.48e-3
- Maximum robust downslope displacement: approximately 1.98 mm

The peak P95 speed occurred at \(E_t=0.25\), after which the response decreased.

In the extended relaxation analysis:

- Peak post-Et=0.30 P95 speed: 9.83e-3 m/s
- Final P95 speed: 4.31e-3 m/s
- Final/peak speed ratio: 0.438
- Late-time speed ratio: 0.897

The late-time response therefore remains bounded and trends downward rather than developing sustained acceleration.

---

## 6. Effect of erosion history

The final geometry \(E_t=0.30\) was reached through both instantaneous and progressive erosion histories.

At the same final toe-recession ratio:

| Metric | Single-stage Et=0.30 | Progressive Et=0.30 |
|---|---:|---:|
| Final P95 displacement | 1.142 mm | 0.836 mm |
| Peak P95 speed | 0.02805 m/s | 0.01100 m/s |
| New plastic MPs | 35.36% | 33.76% |

The instantaneous removal produces the stronger transient response.

The lower response under progressive erosion is **consistent with stress redistribution and relaxation between erosion increments**, although the present simulations do not independently prove that mechanism.

---

## 7. Main finding

Within the tested model:

> **Hydrologically informed weakening places the slope close to a model-specific equilibrium transition, while increasing prescribed toe recession progressively increases displacement, dynamic response, and plastic mobilization. However, neither independent nor progressive toe erosion up to \(E_t=0.30\) produces self-sustaining landslide runout.**

The simulations therefore distinguish between:

- **mobilization and localized yielding**, and
- **runaway large-deformation failure**.

This distinction is important because increasing plasticity alone should not be interpreted as evidence of landslide runout.

---

## Scope and limitations

- The weakened states are independently preconditioned Mohr–Coulomb strength states.
- They do not represent transient rainfall infiltration or a prescribed saturation history.
- Toe erosion is implemented as prescribed geometric material-point removal.
- Waves, sediment transport, and fluid–soil interaction are not resolved.
- The strength-reduction factor is used for numerical screening and is not reported as a physical factor of safety.
- The present slope scenarios demonstrate mobilization and stress-history effects, not full landslide runout.
- Large-deformation MPM capability is independently demonstrated through reproduction of the upstream granular-collapse benchmark.
