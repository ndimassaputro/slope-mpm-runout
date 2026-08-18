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

DYNAMIC_TEMPLATE = (
    ROOT
    / "scenarios"
    / "dynamic_pipeline"
    / "wet_preconditioned_F1p58_dynamic"
)

CASE = (
    ROOT
    / "scenarios"
    / "toe_erosion"
    / "F1p58_Et010"
)

CASE.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# Geometry / erosion definition
# ============================================================

H = 10.0
CREST_X = 6.0
SLOPE_ANGLE_DEG = 30.0

ET = 0.10
EROSION_RECESSION = ET * H


# ============================================================
# Copy required input
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


# ============================================================
# Dynamic ProjectParameters
# ============================================================

with open(
    DYNAMIC_TEMPLATE / "ProjectParameters.json"
) as f:
    project = json.load(f)


project["problem_data"][
    "problem_name"
] = "F1p58_Et010_toe_erosion"


project["problem_data"][
    "start_time"
] = 1.0

project["problem_data"][
    "end_time"
] = 1.20


solver = project[
    "solver_settings"
]

solver[
    "model_import_settings"
] = {
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


solver[
    "grid_model_import_settings"
] = {
    "input_type":
        "mdpa",

    "input_filename":
        "slope_Grid",
}


solver[
    "time_stepping"
] = {
    "time_step":
        0.001,
}

solver[
    "max_iteration"
] = 30


# ============================================================
# Output
# ============================================================

project[
    "output_processes"
].pop(
    "restart_processes",
    None,
)


body = (
    project[
        "output_processes"
    ][
        "body_output_process"
    ][0][
        "Parameters"
    ]
)

body[
    "output_path"
] = "erosion_Body"

body[
    "output_interval"
] = 0.01


grid = (
    project[
        "output_processes"
    ][
        "grid_output_process"
    ][0][
        "Parameters"
    ]
)

grid[
    "output_path"
] = "erosion_Grid"

grid[
    "output_interval"
] = 0.01


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
# Custom analysis
#
# Stage:
#
# equilibrium F=1.58 restart
#       ↓
# remove toe wedge Et=0.10
#       ↓
# zero quasi-static pseudo velocity
#       ↓
# dynamic MPM
#
# Response history is calculated directly from MPs so that
# the removal of material points does not break coordinate
# comparisons.
# ============================================================

script = f'''import csv
import math

import numpy as np

import KratosMultiphysics as KM
import KratosMultiphysics.MPMApplication as KMPM

from KratosMultiphysics.MPMApplication.mpm_analysis import (
    MpmAnalysis,
)


H = {H}
CREST_X = {CREST_X}
SLOPE_ANGLE_DEG = {SLOPE_ANGLE_DEG}

ET = {ET}
EROSION_RECESSION = {EROSION_RECESSION}

TAN_BETA = math.tan(
    math.radians(
        SLOPE_ANGLE_DEG
    )
)

TOE_X = (
    CREST_X
    + H / TAN_BETA
)

NEW_TOE_X = (
    TOE_X
    - EROSION_RECESSION
)


class ToeErosionAnalysis(MpmAnalysis):

    # ========================================================
    # Remove toe BEFORE dynamic solver initialization
    # ========================================================

    def ModifyInitialGeometry(self):

        mp = (
            self._GetSolver()
            .GetComputingModelPart()
        )

        info = mp.ProcessInfo

        before = (
            mp.NumberOfElements()
        )

        removed_ids = []
        removed_coordinates = []


        for element in mp.Elements:

            values = (
                element
                .CalculateOnIntegrationPoints(
                    KMPM.MP_COORD,
                    info,
                )
            )

            coord = values[0]

            x = float(coord[0])
            y = float(coord[1])


            surface_y = (
                (TOE_X - x)
                * TAN_BETA
            )


            erase = (
                x >= NEW_TOE_X
                and x <= TOE_X
                and y >= -1.0e-8
                and y <= surface_y + 1.0e-8
            )


            if erase:

                element.Set(
                    KM.TO_ERASE,
                    True,
                )

                removed_ids.append(
                    int(element.Id)
                )

                removed_coordinates.append(
                    [x, y]
                )


        KMPM.MaterialPointEraseProcess(
            mp
        ).Execute()


        after = (
            mp.NumberOfElements()
        )


        print()
        print("=" * 76)
        print("PRESCRIBED TOE EROSION")
        print("=" * 76)

        print(
            "E_t                 :",
            ET,
        )

        print(
            "Slope height H      :",
            f"{{H:.3f}} m",
        )

        print(
            "Toe recession e     :",
            f"{{EROSION_RECESSION:.3f}} m",
        )

        print(
            "Original toe x      :",
            f"{{TOE_X:.6f}} m",
        )

        print(
            "New toe x           :",
            f"{{NEW_TOE_X:.6f}} m",
        )

        print(
            "MPs before erosion  :",
            before,
        )

        print(
            "MPs removed         :",
            len(removed_ids),
        )

        print(
            "MPs remaining       :",
            after,
        )

        print(
            "Fraction removed    :",
            f"{{100*len(removed_ids)/before:.3f}} %",
        )


        if removed_coordinates:

            rc = np.asarray(
                removed_coordinates
            )

            print(
                "Removed x range     :",
                f"{{rc[:,0].min():.6f}}",
                "to",
                f"{{rc[:,0].max():.6f}} m",
            )

            print(
                "Removed y range     :",
                f"{{rc[:,1].min():.6f}}",
                "to",
                f"{{rc[:,1].max():.6f}} m",
            )


        print(
            "TOE_EROSION_EXECUTED = YES"
        )

        print("=" * 76)


    # ========================================================
    # After solver init:
    # reset pseudo-kinematics and define t=0 erosion state
    # ========================================================

    def ModifyAfterSolverInitialize(self):

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


        for element in mp.Elements:

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

            element.SetValuesOnIntegrationPoints(
                KMPM.MP_VOLUME_ACCELERATION,
                [gravity],
                info,
            )


        self.initial_coords = {{}}
        self.initial_plastic = {{}}

        initial_x = []


        for element in mp.Elements:

            coord = (
                element
                .CalculateOnIntegrationPoints(
                    KMPM.MP_COORD,
                    info,
                )[0]
            )

            ep = (
                element
                .CalculateOnIntegrationPoints(
                    KMPM.MP_EQUIVALENT_PLASTIC_STRAIN,
                    info,
                )[0]
            )


            eid = int(
                element.Id
            )

            self.initial_coords[eid] = np.array(
                [
                    float(coord[0]),
                    float(coord[1]),
                ]
            )

            self.initial_plastic[eid] = float(
                ep
            )

            initial_x.append(
                float(coord[0])
            )


        self.initial_front = (
            np.percentile(
                initial_x,
                99.9,
            )
        )


        self.history_file = (
            "response_history.csv"
        )


        with open(
            self.history_file,
            "w",
            newline="",
        ) as f:

            writer = csv.writer(f)

            writer.writerow(
                [
                    "time_s",
                    "n_mp",
                    "mean_displacement_m",
                    "p95_displacement_m",
                    "p99_displacement_m",
                    "max_displacement_m",
                    "mean_speed_mps",
                    "p95_speed_mps",
                    "max_speed_mps",
                    "max_plastic_strain",
                    "plastic_fraction_gt_1e4_percent",
                    "mean_delta_plastic_strain",
                    "max_delta_plastic_strain",
                    "fraction_delta_plastic_gt_1e5_percent",
                    "robust_front_advance_m",
                ]
            )


        print()
        print(
            "DYNAMIC_RESET_EXECUTED = YES"
        )

        print(
            "Dynamic initial MPs:",
            len(
                self.initial_coords
            ),
        )


    # ========================================================
    # Calculate response every dynamic step
    # ========================================================

    def FinalizeSolutionStep(self):

        super().FinalizeSolutionStep()


        mp = (
            self._GetSolver()
            .GetComputingModelPart()
        )

        info = mp.ProcessInfo


        displacements = []
        speeds = []
        plastic = []
        delta_plastic = []
        current_x = []


        for element in mp.Elements:

            eid = int(
                element.Id
            )


            coord = (
                element
                .CalculateOnIntegrationPoints(
                    KMPM.MP_COORD,
                    info,
                )[0]
            )


            velocity = (
                element
                .CalculateOnIntegrationPoints(
                    KMPM.MP_VELOCITY,
                    info,
                )[0]
            )


            ep = (
                element
                .CalculateOnIntegrationPoints(
                    KMPM.MP_EQUIVALENT_PLASTIC_STRAIN,
                    info,
                )[0]
            )


            current = np.array(
                [
                    float(coord[0]),
                    float(coord[1]),
                ]
            )


            initial = (
                self.initial_coords[eid]
            )


            disp = np.linalg.norm(
                current - initial
            )


            speed = math.sqrt(
                float(velocity[0])**2
                + float(velocity[1])**2
            )


            dep = (
                float(ep)
                - self.initial_plastic[eid]
            )


            displacements.append(
                disp
            )

            speeds.append(
                speed
            )

            plastic.append(
                float(ep)
            )

            delta_plastic.append(
                dep
            )

            current_x.append(
                float(coord[0])
            )


        d = np.asarray(
            displacements
        )

        v = np.asarray(
            speeds
        )

        ep = np.asarray(
            plastic
        )

        dep = np.asarray(
            delta_plastic
        )

        x = np.asarray(
            current_x
        )


        front_advance = (
            np.percentile(
                x,
                99.9,
            )
            - self.initial_front
        )


        time = float(
            info[KM.TIME]
        )


        row = [
            time,
            len(d),

            np.mean(d),
            np.percentile(d, 95),
            np.percentile(d, 99),
            np.max(d),

            np.mean(v),
            np.percentile(v, 95),
            np.max(v),

            np.max(ep),

            100.0
            * np.mean(
                ep > 1.0e-4
            ),

            np.mean(dep),
            np.max(dep),

            100.0
            * np.mean(
                dep > 1.0e-5
            ),

            front_advance,
        ]


        with open(
            self.history_file,
            "a",
            newline="",
        ) as f:

            csv.writer(f).writerow(
                row
            )


        step = int(
            info[KM.STEP]
        )


        if step % 20 == 0:

            print(
                "EROSION_RESPONSE:",
                f"time={{time:.3f}}",
                f"p95_u={{np.percentile(d,95):.6e}}",
                f"p95_v={{np.percentile(v,95):.6e}}",
                f"plastic={{100*np.mean(ep>1e-4):.2f}}%",
                f"front={{front_advance:.6e}}",
            )


with open(
    "ProjectParameters.json",
    "r",
) as f:

    parameters = KM.Parameters(
        f.read()
    )


model = KM.Model()

simulation = ToeErosionAnalysis(
    model,
    parameters,
)

simulation.Run()
'''


(
    CASE / "MainKratos.py"
).write_text(
    script
)


metadata = {
    "strength_state":
        "preconditioned F=1.58",

    "erosion_ratio_Et":
        ET,

    "slope_height_m":
        H,

    "toe_recession_m":
        EROSION_RECESSION,

    "erosion_type":
        (
            "instantaneous prescribed triangular "
            "toe-wedge removal"
        ),

    "interpretation":
        (
            "Idealized geometric toe-recession state; "
            "not wave-resolved erosion."
        ),

    "dynamic_duration_s":
        0.20,

    "time_step_s":
        0.001,
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
print("PHASE 5A — F=1.58 + TOE EROSION")
print("=" * 78)

print("Strength state  : F=1.58")
print("E_t             : 0.10")
print("Toe recession   : 1.00 m")
print("Dynamic time    : 0.20 s")
print("dt              : 0.001 s")
print("Case            :", CASE)

print("=" * 78)
print("TOE EROSION PILOT READY")
print("=" * 78)
