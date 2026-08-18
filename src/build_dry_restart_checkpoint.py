from pathlib import Path
import json
import shutil


ROOT = Path(__file__).resolve().parents[1]

TEMPLATE = (
    ROOT
    / "scenarios"
    / "quasistatic_ramp_smoke"
    / "F_1p00"
)

CASE = (
    ROOT
    / "scenarios"
    / "dynamic_pipeline"
    / "dry_checkpoint"
)

CASE.mkdir(
    parents=True,
    exist_ok=True,
)


# ------------------------------------------------------------
# Copy validated dry/intact quasi-static case
# ------------------------------------------------------------

for filename in (
    "MainKratos.py",
    "slope_Body.mdpa",
    "slope_Grid.mdpa",
    "ParticleMaterials.json",
):
    shutil.copy2(
        TEMPLATE / filename,
        CASE / filename,
    )


# ------------------------------------------------------------
# Project parameters
# ------------------------------------------------------------

with open(
    TEMPLATE / "ProjectParameters.json"
) as f:
    project = json.load(f)


project["problem_data"]["problem_name"] = (
    "dry_equilibrium_restart_checkpoint"
)

project["problem_data"]["start_time"] = 0.0
project["problem_data"]["end_time"] = 1.0


solver = project["solver_settings"]

solver["solver_type"] = "quasi_static"
solver["time_stepping"] = {
    "time_step": 0.05
}

solver["max_iteration"] = 50
solver["echo_level"] = 1


# Gravity remains controlled by the validated
# GravityRampAnalysis in MainKratos.py.
project["processes"]["gravity"] = []


# ------------------------------------------------------------
# VTK outputs
# ------------------------------------------------------------

body = (
    project["output_processes"]
    ["body_output_process"][0]
    ["Parameters"]
)

body["output_path"] = "checkpoint_Body"
body["output_interval"] = 0.10


grid = (
    project["output_processes"]
    ["grid_output_process"][0]
    ["Parameters"]
)

grid["output_path"] = "checkpoint_Grid"
grid["output_interval"] = 0.10


# ------------------------------------------------------------
# Restart checkpoint
#
# Save only final t = 1.0 state.
# ------------------------------------------------------------

project["output_processes"]["restart_processes"] = [
    {
        "python_module":
            "save_restart_process",

        "kratos_module":
            "KratosMultiphysics",

        "process_name":
            "SaveRestartProcess",

        "Parameters": {
            "model_part_name":
                "MPM_Material",

            "echo_level":
                1,

            "serializer_trace":
                "no_trace",

            "restart_save_frequency":
                1.0,

            "restart_control_type":
                "time",

            "save_restart_files_in_folder":
                True,

            "output_path":
                "restart",

            "max_files_to_keep":
                1,
        },
    }
]


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
    "state":
        "dry intact equilibrium",

    "strength_reduction_factor":
        1.0,

    "gravity_loading":
        "0.05g to 1.00g in 20 quasi-static increments",

    "checkpoint_time":
        1.0,

    "purpose":
        (
            "Equilibrated dry/intact MPM state used "
            "as the common initial condition for "
            "subsequent dynamic weakening and "
            "runout simulations."
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


print("=" * 78)
print("DRY EQUILIBRIUM RESTART CHECKPOINT")
print("=" * 78)

print(f"Template       : {TEMPLATE}")
print(f"Case           : {CASE}")
print("Solver         : quasi_static")
print("Strength state : F = 1.00")
print("Gravity        : 0.05g -> 1.00g")
print("Load steps     : 20")
print("Restart        : final t = 1.0")

print("=" * 78)
print("CHECKPOINT CASE READY")
print("=" * 78)
