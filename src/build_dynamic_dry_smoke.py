from pathlib import Path
import json
import shutil


ROOT = Path(__file__).resolve().parents[1]

CHECKPOINT = (
    ROOT
    / "scenarios"
    / "dynamic_pipeline"
    / "dry_checkpoint"
)

CASE = (
    ROOT
    / "scenarios"
    / "dynamic_pipeline"
    / "dry_dynamic_smoke"
)

CASE.mkdir(
    parents=True,
    exist_ok=True,
)

RESTART_INPUT = (
    CASE
    / "restart_input"
)

RESTART_INPUT.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# Copy required files
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
        f"Restart not found: {restart_source}"
    )

restart_target = (
    RESTART_INPUT
    / "MPM_Material_1.0.rest"
)

shutil.copy2(
    restart_source,
    restart_target,
)


# ============================================================
# Start from checkpoint ProjectParameters
# ============================================================

with open(
    CHECKPOINT / "ProjectParameters.json"
) as f:
    project = json.load(f)


project["problem_data"]["problem_name"] = (
    "dry_dynamic_restart_smoke"
)

project["problem_data"]["start_time"] = 1.0
project["problem_data"]["end_time"] = 1.05


# ============================================================
# Dynamic implicit MPM
# ============================================================

solver = project["solver_settings"]

solver["solver_type"] = "Dynamic"

solver["time_integration_method"] = (
    "implicit"
)

solver["scheme_type"] = "newmark"

solver["newmark_beta"] = 0.25

solver["time_stepping"] = {
    "time_step": 0.001
}

solver["max_iteration"] = 30

solver["echo_level"] = 1


# ============================================================
# Load MATERIAL POINTS from restart
# ============================================================

solver["model_import_settings"] = {
    "input_type": "rest",
    "input_filename": "MPM_Material",
    "input_output_path": "restart_input",
    "load_restart_files_from_folder": True,
    "restart_load_file_label": "1.0",
    "echo_level": 1,
    "serializer_trace": "no_trace",
}


# Background grid is still read normally.
solver["grid_model_import_settings"] = {
    "input_type": "mdpa",
    "input_filename": "slope_Grid",
}


# ============================================================
# Gravity is explicitly preserved in custom MainKratos.py.
#
# Do NOT use the normal gravity process here because we need
# to distinguish:
#
# MP_VOLUME_ACCELERATION = gravitational body acceleration
# MP_ACCELERATION        = physical particle acceleration
# ============================================================

project["processes"]["gravity"] = []


# ============================================================
# Remove restart output from this smoke test
# ============================================================

project["output_processes"].pop(
    "restart_processes",
    None,
)


# ============================================================
# Dynamic outputs
# ============================================================

body = (
    project["output_processes"]
    ["body_output_process"][0]
    ["Parameters"]
)

body["output_path"] = "dynamic_Body"

body["output_interval"] = 0.005


# Ensure required variables are present.
variables = body.get(
    "gauss_point_variables_in_elements",
    [],
)

required_variables = [
    "MP_DISPLACEMENT",
    "MP_VELOCITY",
    "MP_ACCELERATION",
    "MP_CAUCHY_STRESS_VECTOR",
    "MP_ALMANSI_STRAIN_VECTOR",
    "MP_EQUIVALENT_PLASTIC_STRAIN",
]

for variable in required_variables:
    if variable not in variables:
        variables.append(variable)

body[
    "gauss_point_variables_in_elements"
] = variables


grid = (
    project["output_processes"]
    ["grid_output_process"][0]
    ["Parameters"]
)

grid["output_path"] = "dynamic_Grid"
grid["output_interval"] = 0.005


with open(
    CASE / "ProjectParameters.json",
    "w",
) as f:
    json.dump(
        project,
        f,
        indent=4,
    )


# ============================================================
# Custom analysis:
#
# 1. Load equilibrated restart.
# 2. Preserve stress/internal state.
# 3. Zero algorithmic quasi-static velocity/acceleration.
# 4. Explicitly maintain gravity as MP_VOLUME_ACCELERATION.
# 5. Continue with dynamic implicit Newmark MPM.
# ============================================================

main_script = r'''import KratosMultiphysics as KM
import KratosMultiphysics.MPMApplication as KMPM

from KratosMultiphysics.MPMApplication.mpm_analysis import (
    MpmAnalysis,
)


class DryDynamicRestartAnalysis(MpmAnalysis):

    def ModifyBeforeSolutionLoop(self):

        mp = (
            self._GetSolver()
            .GetComputingModelPart()
        )

        info = mp.ProcessInfo

        zero = KM.Vector(3)
        zero[0] = 0.0
        zero[1] = 0.0
        zero[2] = 0.0

        gravity = KM.Vector(3)
        gravity[0] = 0.0
        gravity[1] = -9.81
        gravity[2] = 0.0

        n_mp = 0

        for element in mp.Elements:

            # Remove pseudo-kinematics inherited from
            # quasi-static loading.
            element.SetValuesOnIntegrationPoints(
                KMPM.MP_VELOCITY,
                [zero],
                info,
            )

            element.SetValuesOnIntegrationPoints(
                KMPM.MP_ACCELERATION,
                [zero],
                info,
            )

            # Preserve physical self-weight loading.
            element.SetValuesOnIntegrationPoints(
                KMPM.MP_VOLUME_ACCELERATION,
                [gravity],
                info,
            )

            n_mp += 1

        KM.Logger.PrintInfo(
            "DynamicRestart",
            (
                f"Reset kinematics on {n_mp} MPs: "
                "MP_VELOCITY=0, "
                "MP_ACCELERATION=0, "
                "MP_VOLUME_ACCELERATION=(0,-9.81,0)"
            ),
        )


with open(
    "ProjectParameters.json",
    "r",
) as f:

    parameters = KM.Parameters(
        f.read()
    )


model = KM.Model()

simulation = DryDynamicRestartAnalysis(
    model,
    parameters,
)

simulation.Run()
'''


(
    CASE
    / "MainKratos.py"
).write_text(
    main_script
)


metadata = {
    "initial_state":
        "F=1.00 equilibrated dry/intact restart",

    "restart_time":
        1.0,

    "dynamic_end_time":
        1.05,

    "dynamic_duration_s":
        0.05,

    "dynamic_dt_s":
        0.001,

    "solver":
        "implicit dynamic MPM / Newmark",

    "kinematic_reset": {
        "MP_VELOCITY":
            0.0,

        "MP_ACCELERATION":
            0.0,

        "MP_VOLUME_ACCELERATION":
            [0.0, -9.81, 0.0],
    },

    "purpose":
        (
            "Verify that the equilibrated dry/intact "
            "stress state remains mechanically stable "
            "after switching from quasi-static "
            "initialization to dynamic MPM."
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


print("=" * 80)
print("PHASE 4A — DRY DYNAMIC RESTART SMOKE TEST")
print("=" * 80)

print(f"Checkpoint : {restart_source}")
print(f"Case       : {CASE}")
print("Restart    : t = 1.0")
print("Dynamics   : 1.000 -> 1.050 s")
print("dt         : 0.001 s")
print("Steps      : 50")
print("Strength   : dry/intact F=1.00")
print("v_MP start : 0")
print("a_MP start : 0")
print("gravity    : 9.81 m/s2 retained")

print("=" * 80)
print("DYNAMIC DRY SMOKE CASE READY")
print("=" * 80)
