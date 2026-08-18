import csv
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
