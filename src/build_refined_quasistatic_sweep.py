from pathlib import Path
import json
import math
import shutil


ROOT = Path(__file__).resolve().parents[1]

TEMPLATE = (
    ROOT
    / "scenarios"
    / "quasistatic_ramp_smoke"
    / "F_1p00"
)

OUT = (
    ROOT
    / "scenarios"
    / "strength_reduction_quasistatic"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


FACTORS = [
    1.50,
    1.52,
    1.54,
    1.56,
    1.58,
    1.60,
]

C0 = 20.0e3
PHI0_DEG = 28.0


def case_name(F):
    return f"F_{F:.2f}".replace(".", "p")


manifest = []


print("=" * 82)
print("PHASE 3B — REFINED QUASI-STATIC STRENGTH REDUCTION")
print("=" * 82)

print(
    f"{'F':>6s}"
    f"{'c (kPa)':>14s}"
    f"{'phi (deg)':>14s}"
    f"{'case':>14s}"
)

print("-" * 82)


for F in FACTORS:

    name = case_name(F)
    case = OUT / name

    case.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ---------------------------------------------------------
    # Copy validated quasi-static framework
    # ---------------------------------------------------------

    for filename in (
        "MainKratos.py",
        "slope_Body.mdpa",
        "slope_Grid.mdpa",
        "ProjectParameters.json",
    ):
        shutil.copy2(
            TEMPLATE / filename,
            case / filename,
        )

    # ---------------------------------------------------------
    # Strength reduction
    # ---------------------------------------------------------

    cohesion = C0 / F

    phi_rad = math.atan(
        math.tan(
            math.radians(PHI0_DEG)
        ) / F
    )

    phi_deg = math.degrees(
        phi_rad
    )

    with open(
        TEMPLATE / "ParticleMaterials.json"
    ) as f:
        materials = json.load(f)

    variables = (
        materials["properties"][0]
        ["Material"]["Variables"]
    )

    variables["COHESION"] = cohesion

    variables[
        "INTERNAL_FRICTION_ANGLE"
    ] = phi_rad

    with open(
        case / "ParticleMaterials.json",
        "w",
    ) as f:
        json.dump(
            materials,
            f,
            indent=4,
        )

    # ---------------------------------------------------------
    # Unique problem/output names
    # ---------------------------------------------------------

    with open(
        case / "ProjectParameters.json"
    ) as f:
        project = json.load(f)

    project["problem_data"][
        "problem_name"
    ] = f"qs_strength_reduction_{name}"

    body_output = (
        project["output_processes"]
        ["body_output_process"][0]
        ["Parameters"]
    )

    body_output[
        "output_path"
    ] = "qs_Body"

    grid_output = (
        project["output_processes"]
        ["grid_output_process"][0]
        ["Parameters"]
    )

    grid_output[
        "output_path"
    ] = "qs_Grid"

    with open(
        case / "ProjectParameters.json",
        "w",
    ) as f:
        json.dump(
            project,
            f,
            indent=4,
        )

    metadata = {
        "strength_reduction_factor": F,

        "baseline_strength": {
            "cohesion_kpa": C0 / 1000,
            "friction_angle_deg": PHI0_DEG,
        },

        "reduced_strength": {
            "cohesion_kpa":
                cohesion / 1000,

            "friction_angle_deg":
                phi_deg,
        },

        "reduction_rule": {
            "cohesion":
                "c_F = c_0 / F",

            "friction":
                "tan(phi_F) = tan(phi_0) / F",
        },

        "solver":
            "Kratos quasi_static MPM",

        "gravity_path":
            "0.05g to 1.00g in 20 increments",

        "interpretation":
            (
                "Critical transition is bracketed "
                "between the highest strength-reduction "
                "factor completing full self-weight "
                "equilibrium and the lowest factor "
                "that cannot complete it."
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

    manifest.append(
        metadata
    )

    print(
        f"{F:6.2f}"
        f"{cohesion/1000:14.3f}"
        f"{phi_deg:14.3f}"
        f"{name:>14s}"
    )


with open(
    OUT / "sweep_manifest.json",
    "w",
) as f:
    json.dump(
        manifest,
        f,
        indent=4,
    )


print("-" * 82)
print(f"Cases generated : {len(FACTORS)}")
print("Solver          : quasi_static")
print("Gravity steps   : 20")
print("Gravity path    : 0.05g -> 1.00g")
print(f"Directory       : {OUT}")

print("=" * 82)
print("REFINED CASE GENERATION COMPLETE")
print("=" * 82)
