import KratosMultiphysics as KM
import KratosMultiphysics.MPMApplication as KMPM

from KratosMultiphysics.MPMApplication.mpm_analysis import MpmAnalysis


class DryDynamicRestartAnalysis(MpmAnalysis):

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

        n_mp = 0

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

            n_mp += 1

        KM.Logger.PrintInfo(
            "DynamicRestart",
            (
                f"RESET_CALLBACK_EXECUTED: "
                f"{n_mp} MPs; "
                "MP_VELOCITY=0; "
                "MP_ACCELERATION=0; "
                "gravity=(0,-9.81,0)"
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
