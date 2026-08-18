from pathlib import Path
import json
import math
import shutil


ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT
    / "scenarios"
    / "dynamic_pipeline"
    / "wet_preconditioned_F1p58_checkpoint"
)

CASE = (
    ROOT
    / "scenarios"
    / "dynamic_pipeline"
    / "wet_preconditioned_F1p59_checkpoint"
)

F = 1.59

TARGET_C_KPA = 20.0 / F

TARGET_PHI_DEG = math.degrees(
    math.atan(
        math.tan(
            math.radians(28.0)
        ) / F
    )
)


CASE.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# Copy validated F=1.58 equilibrium setup
# ============================================================

for filename in (
    "MainKratos.py",
    "slope_Body.mdpa",
    "slope_Grid.mdpa",
    "ProjectParameters.json",
):
    src = SOURCE / filename

    if not src.exists():
        raise FileNotFoundError(src)

    shutil.copy2(
        src,
        CASE / filename,
    )


# ============================================================
# Modify material strength BEFORE constitutive initialization
# ============================================================

material_source = (
    SOURCE / "ParticleMaterials.json"
)

with open(material_source) as f:
    material = json.load(f)


changes = []


def patch(obj, path="root"):

    if isinstance(obj, dict):

        for key, value in obj.items():

            current_path = f"{path}.{key}"

            if (
                key == "COHESION"
                and isinstance(value, (int, float))
            ):

                old = float(value)

                # Detect whether file stores Pa or kPa.
                if abs(old) > 1000.0:
                    new = TARGET_C_KPA * 1000.0
                    unit = "Pa"
                else:
                    new = TARGET_C_KPA
                    unit = "kPa"

                obj[key] = new

                changes.append(
                    (
                        current_path,
                        old,
                        new,
                        unit,
                    )
                )

            elif (
                key == "INTERNAL_FRICTION_ANGLE"
                and isinstance(value, (int, float))
            ):

                old = float(value)

                # Detect degrees versus radians.
                if abs(old) > 3.2:
                    new = TARGET_PHI_DEG
                    unit = "deg"
                else:
                    new = math.radians(
                        TARGET_PHI_DEG
                    )
                    unit = "rad"

                obj[key] = new

                changes.append(
                    (
                        current_path,
                        old,
                        new,
                        unit,
                    )
                )

            else:
                patch(
                    value,
                    current_path,
                )

    elif isinstance(obj, list):

        for i, value in enumerate(obj):
            patch(
                value,
                f"{path}[{i}]",
            )


patch(material)


cohesion_changes = [
    c for c in changes
    if c[0].endswith(".COHESION")
]

phi_changes = [
    c for c in changes
    if c[0].endswith(
        ".INTERNAL_FRICTION_ANGLE"
    )
]


if not cohesion_changes:
    raise RuntimeError(
        "COHESION not found in ParticleMaterials.json"
    )

if not phi_changes:
    raise RuntimeError(
        "INTERNAL_FRICTION_ANGLE not found "
        "in ParticleMaterials.json"
    )


with open(
    CASE / "ParticleMaterials.json",
    "w",
) as f:

    json.dump(
        material,
        f,
        indent=4,
    )


# ============================================================
# Clean metadata / output identity
# ============================================================

project_path = (
    CASE / "ProjectParameters.json"
)

with open(project_path) as f:
    project = json.load(f)


project["problem_data"][
    "problem_name"
] = "wet_preconditioned_F1p59_checkpoint"


with open(
    project_path,
    "w",
) as f:

    json.dump(
        project,
        f,
        indent=4,
    )


metadata = {
    "strength_reduction_factor": F,
    "cohesion_kpa": TARGET_C_KPA,
    "friction_angle_deg": TARGET_PHI_DEG,
    "purpose": (
        "Near-transition preconditioned strength "
        "state eligibility test. Not interpreted "
        "as a physical factor of safety."
    ),
}


with open(
    CASE / "checkpoint_metadata.json",
    "w",
) as f:

    json.dump(
        metadata,
        f,
        indent=4,
    )


print("=" * 76)
print("F=1.59 PRECONDITIONED CHECKPOINT READY")
print("=" * 76)

print(
    "Target cohesion :",
    f"{TARGET_C_KPA:.6f} kPa",
)

print(
    "Target phi      :",
    f"{TARGET_PHI_DEG:.6f} deg",
)

print()
print("Material changes:")

for path, old, new, unit in changes:

    print(
        f"  {path}"
    )

    print(
        f"    {old:.9g} -> "
        f"{new:.9g} {unit}"
    )

print()
print("Case:", CASE)

print("=" * 76)
