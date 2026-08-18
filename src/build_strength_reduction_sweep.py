from pathlib import Path
import json
import math
import shutil

ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT
    / "scenarios"
    / "baseline_dry_intact"
    / "equilibrium"
)

SWEEP = ROOT / "scenarios" / "strength_reduction"
SWEEP.mkdir(parents=True, exist_ok=True)

FACTORS = [
    1.00,
    1.10,
    1.20,
    1.30,
    1.40,
    1.50,
    1.60,
]

C0 = 20.0e3
PHI0_DEG = 28.0


def case_name(F):
    return f"F_{F:.2f}".replace(".", "p")


print("=" * 78)
print("PHASE 3A — STRENGTH-REDUCTION SWEEP GENERATION")
print("=" * 78)

print(
    f"{'F':>6s} "
    f"{'cohesion (kPa)':>16s} "
    f"{'phi (deg)':>12s} "
    f"{'case':>12s}"
)

print("-" * 78)

manifest = []

for F in FACTORS:

    name = case_name(F)
    case = SWEEP / name
    case.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------
    # Strength reduction
    # --------------------------------------------------------------

    cohesion = C0 / F

    phi_rad = math.atan(
        math.tan(
            math.radians(PHI0_DEG)
        ) / F
    )

    phi_deg = math.degrees(phi_rad)

    # --------------------------------------------------------------
    # Copy verified geometry + executable
    # --------------------------------------------------------------

    for filename in (
        "MainKratos.py",
        "slope_Body.mdpa",
        "slope_Grid.mdpa",
    ):
        shutil.copy2(
            SOURCE / filename,
            case / filename,
        )

    # --------------------------------------------------------------
    # Material definition
    # --------------------------------------------------------------

    with open(
        SOURCE / "ParticleMaterials.json"
    ) as f:
        materials = json.load(f)

    variables = (
        materials["properties"][0]
        ["Material"]["Variables"]
    )

    variables["COHESION"] = cohesion
    variables["INTERNAL_FRICTION_ANGLE"] = phi_rad

    with open(
        case / "ParticleMaterials.json",
        "w",
    ) as f:
        json.dump(
            materials,
            f,
            indent=4,
        )

    # --------------------------------------------------------------
    # Static solver settings copied from verified equilibrium case
    # --------------------------------------------------------------

    with open(
        SOURCE / "ProjectParameters.json"
    ) as f:
        project = json.load(f)

    project["problem_data"]["problem_name"] = (
        f"strength_reduction_{name}"
    )

    # Keep one nonlinear static self-weight solution.
    project["problem_data"]["start_time"] = 0.0
    project["problem_data"]["end_time"] = 1.0

    project["solver_settings"]["echo_level"] = 1

    # Increase NR allowance slightly for reduced-strength cases.
    project["solver_settings"]["max_iteration"] = 50

    # Unique output directories.
    body_output = (
        project["output_processes"]
        ["body_output_process"][0]
        ["Parameters"]
    )

    body_output["output_path"] = "sr_Body"
    body_output["output_interval"] = 1.0

    grid_output = (
        project["output_processes"]
        ["grid_output_process"][0]
        ["Parameters"]
    )

    grid_output["output_path"] = "sr_Grid"
    grid_output["output_interval"] = 1.0

    with open(
        case / "ProjectParameters.json",
        "w",
    ) as f:
        json.dump(
            project,
            f,
            indent=4,
        )

    # --------------------------------------------------------------
    # Metadata
    # --------------------------------------------------------------

    metadata = {
        "strength_reduction_factor": F,

        "baseline": {
            "cohesion_pa": C0,
            "friction_angle_deg": PHI0_DEG,
        },

        "reduced": {
            "cohesion_pa": cohesion,
            "cohesion_kpa": cohesion / 1000,
            "friction_angle_rad": phi_rad,
            "friction_angle_deg": phi_deg,
        },

        "reduction_rule": {
            "cohesion":
                "c_F = c_0 / F",

            "friction":
                "tan(phi_F) = tan(phi_0) / F",
        },

        "interpretation":
            (
                "Static strength-reduction screening case. "
                "Convergence loss alone is not interpreted "
                "as physical slope failure."
            ),
    }

    with open(
        case / "case_metadata.json",
        "w",
    ) as f:
        json.dump(
            metadata,
            f,
            indent=4,
        )

    manifest.append(metadata)

    print(
        f"{F:6.2f} "
        f"{cohesion/1000:16.3f} "
        f"{phi_deg:12.3f} "
        f"{name:>12s}"
    )


with open(
    SWEEP / "sweep_manifest.json",
    "w",
) as f:
    json.dump(
        manifest,
        f,
        indent=4,
    )


print("-" * 78)
print(
    f"Cases generated: {len(FACTORS)}"
)

print(
    f"Directory      : {SWEEP}"
)

print("=" * 78)
print("PHASE 3A CASE GENERATION COMPLETE")
print("=" * 78)
