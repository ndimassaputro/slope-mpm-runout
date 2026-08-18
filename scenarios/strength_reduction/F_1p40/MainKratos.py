import KratosMultiphysics
from KratosMultiphysics.MPMApplication.mpm_analysis import MpmAnalysis


with open("ProjectParameters.json", "r") as parameter_file:
    parameters = KratosMultiphysics.Parameters(
        parameter_file.read()
    )


model = KratosMultiphysics.Model()

simulation = MpmAnalysis(
    model,
    parameters,
)

simulation.Run()
