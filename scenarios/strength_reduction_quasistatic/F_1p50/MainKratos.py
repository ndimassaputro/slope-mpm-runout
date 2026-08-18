import KratosMultiphysics as KM
import KratosMultiphysics.MPMApplication as KMPM
from KratosMultiphysics.MPMApplication.mpm_analysis import MpmAnalysis


TARGET_G = 9.81
RAMP_END_TIME = 1.0


class GravityRampAnalysis(MpmAnalysis):

    def ApplyBoundaryConditions(self):

        # Standard displacement constraints.
        super().ApplyBoundaryConditions()

        # This hook is executed before solver.Predict().
        # Therefore the current gravity level is available when
        # material-point quantities are mapped to the grid.
        mp_model_part = (
            self._GetSolver()
            .GetComputingModelPart()
        )

        load_factor = max(
            0.0,
            min(
                1.0,
                float(self.time) / RAMP_END_TIME,
            ),
        )

        gravity = KM.Vector(3)
        gravity[0] = 0.0
        gravity[1] = -TARGET_G * load_factor
        gravity[2] = 0.0

        info = mp_model_part.ProcessInfo

        for element in mp_model_part.Elements:

            element.SetValuesOnIntegrationPoints(
                KMPM.MP_VOLUME_ACCELERATION,
                [gravity],
                info,
            )

            element.SetValuesOnIntegrationPoints(
                KMPM.MP_ACCELERATION,
                [gravity],
                info,
            )

        KM.Logger.PrintInfo(
            "GravityRamp",
            (
                f"lambda={load_factor:.3f}, "
                f"g_y={gravity[1]:.6f} m/s2"
            ),
        )


with open("ProjectParameters.json", "r") as parameter_file:

    parameters = KM.Parameters(
        parameter_file.read()
    )


model = KM.Model()

simulation = GravityRampAnalysis(
    model,
    parameters,
)

simulation.Run()
