import csv
import math

import numpy as np

import KratosMultiphysics as KM
import KratosMultiphysics.MPMApplication as KMPM

from KratosMultiphysics.MPMApplication.mpm_analysis import (
    MpmAnalysis,
)


H = 10.0
CREST_X = 6.0
SLOPE_ANGLE_DEG = 30.0

ET = 0.15
EROSION_RECESSION = 1.5

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
            f"{H:.3f} m",
        )

        print(
            "Toe recession e     :",
            f"{EROSION_RECESSION:.3f} m",
        )

        print(
            "Original toe x      :",
            f"{TOE_X:.6f} m",
        )

        print(
            "New toe x           :",
            f"{NEW_TOE_X:.6f} m",
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
            f"{100*len(removed_ids)/before:.3f} %",
        )


        if removed_coordinates:

            rc = np.asarray(
                removed_coordinates
            )

            print(
                "Removed x range     :",
                f"{rc[:,0].min():.6f}",
                "to",
                f"{rc[:,0].max():.6f} m",
            )

            print(
                "Removed y range     :",
                f"{rc[:,1].min():.6f}",
                "to",
                f"{rc[:,1].max():.6f} m",
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


        self.initial_coords = {}
        self.initial_plastic = {}

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
                f"time={time:.3f}",
                f"p95_u={np.percentile(d,95):.6e}",
                f"p95_v={np.percentile(v,95):.6e}",
                f"plastic={100*np.mean(ep>1e-4):.2f}%",
                f"front={front_advance:.6e}",
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
