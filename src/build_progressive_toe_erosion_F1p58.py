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

TEMPLATE = (
    ROOT
    / "scenarios"
    / "toe_erosion"
    / "F1p58_Et030"
)

CASE = (
    ROOT
    / "scenarios"
    / "toe_erosion"
    / "F1p58_progressive"
)

CASE.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# Copy inputs
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
# ProjectParameters
# ============================================================

with open(
    TEMPLATE / "ProjectParameters.json"
) as f:
    project = json.load(f)


project["problem_data"][
    "problem_name"
] = "F1p58_progressive_toe_erosion"

project["problem_data"][
    "start_time"
] = 1.0

project["problem_data"][
    "end_time"
] = 1.601


solver = project[
    "solver_settings"
]

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

body["output_path"] = "progressive_Body"
body["output_interval"] = 0.02


grid = (
    project[
        "output_processes"
    ][
        "grid_output_process"
    ][0][
        "Parameters"
    ]
)

grid["output_path"] = "progressive_Grid"
grid["output_interval"] = 0.02


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
# MainKratos
# ============================================================

script = r'''import csv
import math

import numpy as np

import KratosMultiphysics as KM
import KratosMultiphysics.MPMApplication as KMPM

from KratosMultiphysics.MPMApplication.mpm_analysis import (
    MpmAnalysis,
)


# ============================================================
# Geometry
# ============================================================

H = 10.0
CREST_X = 6.0
SLOPE_ANGLE_DEG = 30.0

TAN_BETA = math.tan(
    math.radians(
        SLOPE_ANGLE_DEG
    )
)

TOE_X = (
    CREST_X
    + H / TAN_BETA
)


# ============================================================
# Progressive erosion schedule
#
# Numerical staging times — NOT a physical erosion rate.
# ============================================================

EROSION_SCHEDULE = [
    (1.001, 0.10),
    (1.101, 0.15),
    (1.201, 0.20),
    (1.301, 0.25),
    (1.401, 0.30),
]


class ProgressiveToeErosionAnalysis(MpmAnalysis):

    def ModifyAfterSolverInitialize(self):

        mp = (
            self._GetSolver()
            .GetComputingModelPart()
        )

        info = mp.ProcessInfo


        # ----------------------------------------------------
        # Remove quasi-static pseudo velocity only once.
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # Store reference state BEFORE any erosion.
        # ----------------------------------------------------

        self.reference_coords = {}
        self.initial_plastic = {}


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


            ep = (
                element
                .CalculateOnIntegrationPoints(
                    KMPM.MP_EQUIVALENT_PLASTIC_STRAIN,
                    info,
                )[0]
            )


            self.reference_coords[eid] = (
                np.array(
                    [
                        float(coord[0]),
                        float(coord[1]),
                    ]
                )
            )


            self.initial_plastic[eid] = float(
                ep
            )


        self.initial_n_mp = (
            mp.NumberOfElements()
        )

        self.current_Et = 0.0

        self.applied_stages = set()


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
                    "Et",
                    "n_mp",
                    "removed_total",
                    "mean_displacement_m",
                    "p95_displacement_m",
                    "p99_displacement_m",
                    "max_displacement_m",
                    "mean_speed_mps",
                    "p95_speed_mps",
                    "max_speed_mps",
                    "plastic_fraction_gt_1e4_percent",
                    "new_plastic_fraction_gt_1e5_percent",
                    "max_delta_plastic_strain",
                    "q999_downslope_displacement_m",
                    "max_downslope_displacement_m",
                ]
            )


        print()
        print("=" * 76)
        print("PROGRESSIVE TOE EROSION INITIALIZATION")
        print("=" * 76)

        print(
            "Initial MPs       :",
            self.initial_n_mp,
        )

        print(
            "Initial strength  : F=1.58"
        )

        print(
            "Pseudo velocity   : RESET"
        )

        print(
            "Gravity           : RESTORED"
        )

        print(
            "EROSION PIPELINE READY = YES"
        )

        print("=" * 76)


    # ========================================================
    # Apply one geometric erosion stage
    # ========================================================

    def ApplyErosion(self, target_Et):

        mp = (
            self._GetSolver()
            .GetComputingModelPart()
        )

        erosion_distance = (
            target_Et * H
        )

        new_toe_x = (
            TOE_X
            - erosion_distance
        )


        before = (
            mp.NumberOfElements()
        )

        erase_ids = []


        for element in mp.Elements:

            eid = int(
                element.Id
            )


            # IMPORTANT:
            # erosion geometry is based on original
            # equilibrium coordinates, not current moving
            # coordinates.
            ref = (
                self.reference_coords[eid]
            )

            x = float(
                ref[0]
            )

            y = float(
                ref[1]
            )


            surface_y = (
                (TOE_X - x)
                * TAN_BETA
            )


            erase = (
                x >= new_toe_x
                and x <= TOE_X
                and y >= -1.0e-8
                and y <= surface_y + 1.0e-8
            )


            if erase:

                element.Set(
                    KM.TO_ERASE,
                    True,
                )

                erase_ids.append(
                    eid
                )


        KMPM.MaterialPointEraseProcess(
            mp
        ).Execute()


        after = (
            mp.NumberOfElements()
        )

        removed_now = (
            before - after
        )

        removed_total = (
            self.initial_n_mp
            - after
        )


        self.current_Et = (
            target_Et
        )


        print()
        print("=" * 76)
        print("PROGRESSIVE EROSION STAGE")
        print("=" * 76)

        print(
            "E_t target        :",
            f"{target_Et:.2f}",
        )

        print(
            "Toe recession     :",
            f"{erosion_distance:.3f} m",
        )

        print(
            "MPs removed now   :",
            removed_now,
        )

        print(
            "MPs removed total :",
            removed_total,
        )

        print(
            "MPs remaining     :",
            after,
        )

        print(
            "EROSION_STAGE_APPLIED = YES"
        )

        print("=" * 76)


    # ========================================================
    # Before each dynamic solve, check whether a new erosion
    # level must be introduced.
    # ========================================================

    def InitializeSolutionStep(self):

        mp = (
            self._GetSolver()
            .GetComputingModelPart()
        )

        time = float(
            mp.ProcessInfo[KM.TIME]
        )


        for stage_time, Et in EROSION_SCHEDULE:

            key = round(
                Et,
                3,
            )

            if (
                time >= stage_time - 1.0e-10
                and key not in self.applied_stages
            ):

                self.ApplyErosion(
                    Et
                )

                self.applied_stages.add(
                    key
                )


        super().InitializeSolutionStep()


    # ========================================================
    # Response history
    # ========================================================

    def FinalizeSolutionStep(self):

        super().FinalizeSolutionStep()


        mp = (
            self._GetSolver()
            .GetComputingModelPart()
        )

        info = mp.ProcessInfo


        displacement = []
        speed = []
        plastic = []
        delta_plastic = []
        dx_values = []


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
                self.reference_coords[eid]
            )


            dxy = (
                current - initial
            )


            displacement.append(
                np.linalg.norm(
                    dxy
                )
            )


            dx_values.append(
                float(
                    dxy[0]
                )
            )


            speed.append(
                math.sqrt(
                    float(
                        velocity[0]
                    ) ** 2
                    +
                    float(
                        velocity[1]
                    ) ** 2
                )
            )


            plastic.append(
                float(ep)
            )


            delta_plastic.append(
                float(ep)
                - self.initial_plastic[eid]
            )


        d = np.asarray(
            displacement
        )

        v = np.asarray(
            speed
        )

        ep = np.asarray(
            plastic
        )

        dep = np.asarray(
            delta_plastic
        )

        dx = np.asarray(
            dx_values
        )


        time = float(
            info[KM.TIME]
        )


        removed_total = (
            self.initial_n_mp
            - len(d)
        )


        row = [
            time,
            self.current_Et,
            len(d),
            removed_total,

            np.mean(d),
            np.percentile(d, 95),
            np.percentile(d, 99),
            np.max(d),

            np.mean(v),
            np.percentile(v, 95),
            np.max(v),

            100.0
            * np.mean(
                ep > 1.0e-4
            ),

            100.0
            * np.mean(
                dep > 1.0e-5
            ),

            np.max(dep),

            np.percentile(
                dx,
                99.9,
            ),

            np.max(
                dx
            ),
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


        if step % 50 == 0:

            print(
                "PROGRESSIVE_RESPONSE:",
                f"time={time:.3f}",
                f"Et={self.current_Et:.2f}",
                f"n={len(d)}",
                f"p95_u={np.percentile(d,95):.6e}",
                f"p95_v={np.percentile(v,95):.6e}",
                f"new_plastic={100*np.mean(dep>1e-5):.2f}%",
                f"q999_dx={np.percentile(dx,99.9):.6e}",
            )


with open(
    "ProjectParameters.json",
    "r",
) as f:

    parameters = KM.Parameters(
        f.read()
    )


model = KM.Model()

simulation = ProgressiveToeErosionAnalysis(
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

    "erosion_sequence_Et":
        [
            0.10,
            0.15,
            0.20,
            0.25,
            0.30,
        ],

    "erosion_recession_m":
        [
            1.0,
            1.5,
            2.0,
            2.5,
            3.0,
        ],

    "relaxation_interval_s":
        0.10,

    "note":
        (
            "Dynamic staging interval is a numerical "
            "scenario parameter and is not interpreted "
            "as a physical coastal erosion rate."
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
print("PROGRESSIVE TOE EROSION CASE READY")
print("=" * 78)

print("Strength        : F=1.58")
print(
    "Erosion stages  : "
    "0.10 -> 0.15 -> 0.20 -> 0.25 -> 0.30"
)
print(
    "Toe recession   : "
    "1.0 -> 1.5 -> 2.0 -> 2.5 -> 3.0 m"
)
print("Stage interval  : 0.10 s")
print("End time        : 1.601 s")
print("Case            :", CASE)

print("=" * 78)
