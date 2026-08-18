import numpy as np

import KratosMultiphysics as KM
import KratosMultiphysics.MPMApplication as KMPM

from KratosMultiphysics.MPMApplication.mpm_analysis import MpmAnalysis


def mp_vector_stats(model_part, variable):

    values = []

    info = model_part.ProcessInfo

    for element in model_part.Elements:

        vals = element.CalculateOnIntegrationPoints(
            variable,
            info,
        )

        if vals:
            v = vals[0]
            values.append(
                [
                    float(v[0]),
                    float(v[1]),
                    float(v[2]),
                ]
            )

    arr = np.asarray(values)

    mag = np.linalg.norm(
        arr[:, :2],
        axis=1,
    )

    return (
        len(mag),
        np.mean(mag),
        np.percentile(mag, 95),
        np.max(mag),
    )


class DiagnosticAnalysis(MpmAnalysis):

    def ModifyAfterSolverInitialize(self):

        mp = (
            self._GetSolver()
            .GetComputingModelPart()
        )

        info = mp.ProcessInfo

        print()
        print("========================================")
        print("RESTART STATE — BEFORE RESET")
        print("========================================")

        n, mean_v, p95_v, max_v = (
            mp_vector_stats(
                mp,
                KMPM.MP_VELOCITY,
            )
        )

        print("MPs        :", n)
        print("mean speed :", f"{mean_v:.9e}")
        print("p95 speed  :", f"{p95_v:.9e}")
        print("max speed  :", f"{max_v:.9e}")

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

        print()
        print("========================================")
        print("RESTART STATE — AFTER RESET")
        print("========================================")

        n, mean_v, p95_v, max_v = (
            mp_vector_stats(
                mp,
                KMPM.MP_VELOCITY,
            )
        )

        print("MPs        :", n)
        print("mean speed :", f"{mean_v:.9e}")
        print("p95 speed  :", f"{p95_v:.9e}")
        print("max speed  :", f"{max_v:.9e}")

        print("RESET_CALLBACK_EXECUTED = YES")


    def FinalizeSolutionStep(self):

        super().FinalizeSolutionStep()

        mp = (
            self._GetSolver()
            .GetComputingModelPart()
        )

        n, mean_v, p95_v, max_v = (
            mp_vector_stats(
                mp,
                KMPM.MP_VELOCITY,
            )
        )

        print()
        print("========================================")
        print("AFTER DYNAMIC STEP")
        print("========================================")

        print(
            "TIME       :",
            float(mp.ProcessInfo[KM.TIME]),
        )

        print("MPs        :", n)
        print("mean speed :", f"{mean_v:.9e}")
        print("p95 speed  :", f"{p95_v:.9e}")
        print("max speed  :", f"{max_v:.9e}")


with open(
    "ProjectParameters.json",
    "r",
) as f:

    parameters = KM.Parameters(
        f.read()
    )


# ONLY ONE DYNAMIC STEP
parameters["problem_data"]["end_time"].SetDouble(
    1.001
)


model = KM.Model()

simulation = DiagnosticAnalysis(
    model,
    parameters,
)

simulation.Run()
