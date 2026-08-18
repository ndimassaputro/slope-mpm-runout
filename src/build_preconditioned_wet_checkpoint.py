from pathlib import Path
import json
import shutil


ROOT = Path(__file__).resolve().parents[1]

TEMPLATE = (
    ROOT
    / "scenarios"
    / "strength_reduction_quasistatic"
    / "F_1p58_iter100"
)

CASE = (
    ROOT
    / "scenarios"
    / "dynamic_pipeline"
    / "wet_preconditioned_F1p58_checkpoint"
)

CASE.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# Copy validated quasi-static F=1.58 case
# ============================================================

for filename in (
    "MainKratos.py",
    "slope_Body.mdpa",
    "slope_Grid.mdpa",
    "ParticleMaterials.json",
):
    source = TEMPLATE / filename

    if not source.exists():
        raise FileNotFoundError(source)

    shutil.copy2(
        source,
        CASE / filename,
    )


# ============================================================
# Project parameters
# ============================================================

with open(
    TEMPLATE / "ProjectParameters.json"
) as f:
    project = json.load(f)


project["problem_data"][
    "problem_name"
] = "wet_preconditioned_F1p58_checkpoint"


solver = project["solver_settings"]

solver["max_iteration"] = 100


# ============================================================
# Output paths
# ============================================================

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


# ============================================================
# Save final equilibrated material-point state
# ============================================================

project[
    "output_processes"
]["restart_processes"] = [
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
        "preconditioned wet / near-critical state",

    "strength_reduction_factor":
        1.58,

    "cohesion_kpa":
        20.0 / 1.58,

    "friction_angle_deg":
        18.599370835493087,

    "interpretation":
        (
            "Hydrologically informed preconditioned "
            "strength state. Strength is prescribed "
            "before self-weight equilibration; this "
            "is not transient infiltration or an "
            "explicit saturation history."
        ),

    "max_newton_iterations":
        100,

    "checkpoint_time":
        1.0,
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
print("PRECONDITIONED WET F=1.58 CHECKPOINT")
print("=" * 78)

print("F               : 1.58")
print("cohesion        : 12.658 kPa")
print("friction angle  : 18.599 deg")
print("initialization  : strength applied before self-weight")
print("Newton max      : 100")
print("restart time    : 1.0")
print("case            :", CASE)

print("=" * 78)
print("CHECKPOINT CASE READY")
print("=" * 78)
