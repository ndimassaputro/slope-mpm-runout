from pathlib import Path
import json
import shutil


ROOT = Path(__file__).resolve().parents[1]

CHECKPOINT = (
    ROOT
    / "scenarios"
    / "dynamic_pipeline"
    / "wet_preconditioned_F1p58_checkpoint"
)

DRY_DYNAMIC = (
    ROOT
    / "scenarios"
    / "dynamic_pipeline"
    / "dry_dynamic_smoke"
)

CASE = (
    ROOT
    / "scenarios"
    / "dynamic_pipeline"
    / "wet_preconditioned_F1p58_dynamic"
)

CASE.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# Inputs
# ============================================================

for filename in (
    "slope_Grid.mdpa",
    "ParticleMaterials.json",
):
    shutil.copy2(
        CHECKPOINT / filename,
        CASE / filename,
    )


restart_source = (
    CHECKPOINT
    / "restart"
    / "MPM_Material_1.0.rest"
)

if not restart_source.exists():
    raise FileNotFoundError(
        restart_source
    )


restart_dir = (
    CASE
    / "restart_input"
)

restart_dir.mkdir(
    parents=True,
    exist_ok=True,
)

shutil.copy2(
    restart_source,
    restart_dir / "MPM_Material_1.0.rest",
)


# Proven dynamic restart script:
# reset pseudo-velocity/acceleration while preserving gravity.
shutil.copy2(
    DRY_DYNAMIC / "MainKratos.py",
    CASE / "MainKratos.py",
)


# ============================================================
# Dynamic parameters
# ============================================================

with open(
    DRY_DYNAMIC / "ProjectParameters.json"
) as f:
    project = json.load(f)


project["problem_data"][
    "problem_name"
] = "wet_preconditioned_F1p58_dynamic"

project["problem_data"]["start_time"] = 1.0
project["problem_data"]["end_time"] = 1.05


solver = project["solver_settings"]

solver["model_import_settings"] = {
    "input_type":
        "rest",

    "input_filename":
        "MPM_Material",

    "input_output_path":
        "restart_input",

    "load_restart_files_from_folder":
        True,

    "restart_load_file_label":
        "1.0",

    "echo_level":
        1,

    "serializer_trace":
        "no_trace",
}

solver["grid_model_import_settings"] = {
    "input_type":
        "mdpa",

    "input_filename":
        "slope_Grid",
}

solver["time_stepping"] = {
    "time_step":
        0.001,
}

solver["max_iteration"] = 30


body = (
    project["output_processes"]
    ["body_output_process"][0]
    ["Parameters"]
)

body["output_path"] = "dynamic_Body"
body["output_interval"] = 0.005


grid = (
    project["output_processes"]
    ["grid_output_process"][0]
    ["Parameters"]
)

grid["output_path"] = "dynamic_Grid"
grid["output_interval"] = 0.005


project["output_processes"].pop(
    "restart_processes",
    None,
)


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
    "strength_state":
        "preconditioned F=1.58",

    "initial_checkpoint":
        "../wet_preconditioned_F1p58_checkpoint",

    "dynamic_duration_s":
        0.05,

    "time_step_s":
        0.001,

    "purpose":
        (
            "Verify dynamic stability of the "
            "preconditioned near-critical wet state "
            "before introducing prescribed toe erosion."
        ),
}


with open(
    CASE / "case_metadata.json",
    "w",
) as f:
    json.dump(
        metadata,
        f,
        indent=4,
    )


print("=" * 78)
print("F=1.58 PRECONDITIONED DYNAMIC CONTINUATION")
print("=" * 78)
print("Dynamic duration : 0.05 s")
print("dt               : 0.001 s")
print("No strength edit : restart already contains F=1.58 law state")
print("Case             :", CASE)
print("=" * 78)
