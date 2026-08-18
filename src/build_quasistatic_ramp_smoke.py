from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT
    / "scenarios"
    / "strength_reduction_ramped"
    / "F_1p00"
)

CASE = (
    ROOT
    / "scenarios"
    / "quasistatic_ramp_smoke"
    / "F_1p00"
)

CASE.mkdir(
    parents=True,
    exist_ok=True,
)

# ------------------------------------------------------------
# Copy only input files.
# Do NOT copy failed raw outputs from previous ramp test.
# ------------------------------------------------------------

for name in (
    "MainKratos.py",
    "slope_Body.mdpa",
    "slope_Grid.mdpa",
    "ParticleMaterials.json",
    "case_metadata.json",
):
    shutil.copy2(
        SOURCE / name,
        CASE / name,
    )


# ------------------------------------------------------------
# ProjectParameters
# ------------------------------------------------------------

with open(
    SOURCE / "ProjectParameters.json"
) as f:
    project = json.load(f)


project["problem_data"]["problem_name"] = (
    "quasistatic_gravity_ramp_F1p00"
)

project["problem_data"]["start_time"] = 0.0
project["problem_data"]["end_time"] = 1.0


solver = project["solver_settings"]

# Critical change:
# use quasi-static MPM rather than repeated Static solves.
solver["solver_type"] = "quasi_static"

# Quasi-static inherits the implicit MPM scheme.
solver["scheme_type"] = "bossak"
solver["damp_factor_m"] = -0.3
solver["newmark_beta"] = 0.25

solver["time_stepping"] = {
    "time_step": 0.05
}

solver["max_iteration"] = 50
solver["echo_level"] = 1

# Not required for quasi_static wrapper.
solver.pop(
    "time_integration_method",
    None,
)


# Gravity remains empty here because MainKratos.py
# applies the ramp explicitly at every increment.
project["processes"]["gravity"] = []


body_output = (
    project["output_processes"]
    ["body_output_process"][0]
    ["Parameters"]
)

body_output["output_path"] = "qs_Body"
body_output["output_interval"] = 0.05


grid_output = (
    project["output_processes"]
    ["grid_output_process"][0]
    ["Parameters"]
)

grid_output["output_path"] = "qs_Grid"
grid_output["output_interval"] = 0.05


with open(
    CASE / "ProjectParameters.json",
    "w",
) as f:
    json.dump(
        project,
        f,
        indent=4,
    )


metadata = {
    "case": "F_1p00",
    "purpose":
        "Smoke test for incremental self-weight using "
        "Kratos quasi-static MPM.",
    "solver_type":
        "quasi_static",
    "gravity_ramp":
        "0.05g to 1.00g in 20 increments",
    "acceptance":
        (
            "All 20 increments must complete without "
            "element inversion and the final response "
            "must remain physically comparable to the "
            "verified one-step static baseline."
        ),
}

with open(
    CASE / "smoke_metadata.json",
    "w",
) as f:
    json.dump(
        metadata,
        f,
        indent=4,
    )


print("=" * 76)
print("QUASI-STATIC GRAVITY-RAMP SMOKE CASE")
print("=" * 76)

print("Strength factor : 1.00")
print("Solver          : quasi_static")
print("Steps           : 20")
print("dt              : 0.05")
print("Gravity         : 0.05g -> 1.00g")
print(f"Case directory  : {CASE}")

print("=" * 76)
print("CASE READY")
print("=" * 76)
