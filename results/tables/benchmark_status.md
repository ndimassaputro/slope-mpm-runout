# Kratos MPM benchmark status

## Benchmark

Kratos Multiphysics MPMApplication:
2D non-cohesive granular collapse benchmark.

## Reproduction environment

- Kratos Multiphysics 10.4.0
- Kratos MPMApplication 10.4.0
- Python 3.14
- macOS ARM64
- OpenMP

## Numerical reproduction

- Simulation duration: 2.0 s
- Time step: 5e-5 s
- Nominal increments: 40,000
- Material points: 30,000
- Initial column width: 0.199333 m
- Initial column height: 0.099333 m
- Final maximum front coordinate: 0.509893 m
- Raw front advance: 0.310226 m
- Normalized raw runout: 1.556 L0
- Robust 99.9th-percentile front advance: 0.284825 m
- Maximum material-point displacement: 0.315026 m
- Peak material-point speed: 1.488305 m/s at approximately 0.120 s

## Interpretation

The reproduced calculation exhibits the expected large-deformation
granular-collapse behaviour and stable front extent after the principal
runout phase.

The maximum-x and 99.9th-percentile front definitions are both retained
because the latter reduces sensitivity to isolated leading material
points.

This benchmark is treated as a solver-reproduction and workflow
verification case. No numerical experimental error is claimed because
the upstream Kratos example provides the Bui et al. experimental
comparison primarily in graphical form.

## Next stage

The verified MPM workflow is used as the basis for an independently
developed slope-failure model investigating hydrologically informed
strength weakening and progressive toe erosion.
