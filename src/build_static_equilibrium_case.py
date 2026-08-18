from pathlib import Path
import json
import shutil


ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "scenarios" / "baseline_dry_intact"
CASE = SOURCE / "equilibrium"

CASE.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# Copy the already verified geometry and material definition
# ---------------------------------------------------------------------

for filename in (
    "slope_Body.mdpa",
    "slope_Grid.mdpa",
    "ParticleMaterials.json",
):
    shutil.copy2(
        SOURCE / filename,
        CASE / filename,
    )


# ---------------------------------------------------------------------
# Modern Kratos entry script
# Uses MpmAnalysis rather than deprecated MPMAnalysis.
# ---------------------------------------------------------------------

main_script = '''\
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
'''

(CASE / "MainKratos.py").write_text(main_script)


# ---------------------------------------------------------------------
# Static self-weight equilibrium
# ---------------------------------------------------------------------

project = {
    "problem_data": {
        "problem_name": "baseline_dry_intact_equilibrium",
        "parallel_type": "OpenMP",
        "echo_level": 0,
        "start_time": 0.0,
        "end_time": 1.0,
    },

    "solver_settings": {
        "solver_type": "Static",
        "model_part_name": "MPM_Material",
        "domain_size": 2,
        "echo_level": 1,
        "analysis_type": "non_linear",

        "model_import_settings": {
            "input_type": "mdpa",
            "input_filename": "slope_Body",
        },

        "material_import_settings": {
            "materials_filename":
                "ParticleMaterials.json",
        },

        # Required by the common MPM analysis loop.
        # One static load step is sufficient for this
        # first self-weight equilibrium attempt.
        "time_stepping": {
            "time_step": 1.1,
        },

        "convergence_criterion":
            "residual_criterion",

        "displacement_relative_tolerance":
            1.0e-4,

        "displacement_absolute_tolerance":
            1.0e-9,

        "residual_relative_tolerance":
            1.0e-4,

        "residual_absolute_tolerance":
            1.0e-9,

        "max_iteration": 30,

        "compute_reactions": True,

        "problem_domain_sub_model_part_list": [
            "SlopeBody",
            "BackgroundGrid",
        ],

        "processes_sub_model_part_list": [
            "BoundaryBottom",
            "BoundaryLeft",
        ],

        "grid_model_import_settings": {
            "input_type": "mdpa",
            "input_filename": "slope_Grid",
        },

        "pressure_dofs": False,

        "linear_solver_settings": {
            "solver_type":
                "LinearSolversApplication.sparse_lu",
            "scaling": False,
        },
    },

    "processes": {

        "constraints_process_list": [

            {
                "python_module":
                    "assign_vector_variable_process",
                "kratos_module":
                    "KratosMultiphysics",

                "Parameters": {
                    "model_part_name":
                        "Background_Grid.BoundaryBottom",

                    "variable_name":
                        "DISPLACEMENT",

                    "constrained":
                        [True, True, True],

                    "value":
                        [0.0, 0.0, 0.0],

                    "interval":
                        [0.0, "End"],
                },
            },

            {
                "python_module":
                    "assign_vector_variable_process",
                "kratos_module":
                    "KratosMultiphysics",

                "Parameters": {
                    "model_part_name":
                        "Background_Grid.BoundaryLeft",

                    "variable_name":
                        "DISPLACEMENT",

                    "constrained":
                        [True, False, True],

                    "value":
                        [0.0, 0.0, 0.0],

                    "interval":
                        [0.0, "End"],
                },
            },
        ],

        "loads_process_list": [],

        "list_other_processes": [],

        "gravity": [
            {
                "python_module":
                    "assign_gravity_to_material_point_process",

                "kratos_module":
                    "KratosMultiphysics.MPMApplication",

                "process_name":
                    "AssignGravityToMaterialPointProcess",

                "Parameters": {
                    "model_part_name":
                        "MPM_Material",

                    "modulus":
                        9.81,

                    "direction":
                        [0.0, -1.0, 0.0],
                },
            }
        ],
    },

    "output_processes": {

        "body_output_process": [
            {
                "python_module":
                    "mpm_vtk_output_process",

                "kratos_module":
                    "KratosMultiphysics.MPMApplication",

                "process_name":
                    "MPMVTKOutputProcess",

                "Parameters": {
                    "model_part_name":
                        "MPM_Material",

                    "output_path":
                        "equilibrium_Body",

                    "output_control_type":
                        "time",

                    "output_interval":
                        1.0,

                    "gauss_point_variables_in_elements": [
                        "MP_DISPLACEMENT",
                        "MP_VELOCITY",
                        "MP_CAUCHY_STRESS_VECTOR",
                        "MP_ALMANSI_STRAIN_VECTOR",
                        "MP_EQUIVALENT_PLASTIC_STRAIN",
                    ],
                },
            }
        ],

        "grid_output_process": [
            {
                "python_module":
                    "vtk_output_process",

                "kratos_module":
                    "KratosMultiphysics",

                "process_name":
                    "VTKOutputProcess",

                "Parameters": {
                    "model_part_name":
                        "Background_Grid",

                    "output_path":
                        "equilibrium_Grid",

                    "output_control_type":
                        "time",

                    "output_interval":
                        1.0,

                    "nodal_solution_step_data_variables": [
                        "DISPLACEMENT",
                        "REACTION",
                    ],
                },
            }
        ],
    },
}


with (CASE / "ProjectParameters.json").open("w") as f:
    json.dump(
        project,
        f,
        indent=4,
    )


metadata = {
    "stage":
        "static_self_weight_equilibrium",

    "purpose":
        (
            "Establish a gravity-loaded dry/intact "
            "reference configuration prior to "
            "strength weakening and toe erosion."
        ),

    "solver":
        "Kratos MPM static nonlinear",

    "gravity_m_s2":
        9.81,

    "interpretation_rule":
        (
            "This case is accepted as the dry/intact "
            "reference only if the nonlinear solution "
            "converges and the displacement/stress "
            "response is physically plausible."
        ),
}


with (CASE / "equilibrium_metadata.json").open("w") as f:
    json.dump(
        metadata,
        f,
        indent=4,
    )


print("=" * 76)
print("PHASE 2C — STATIC SELF-WEIGHT CASE")
print("=" * 76)

for filename in (
    "MainKratos.py",
    "ProjectParameters.json",
    "ParticleMaterials.json",
    "slope_Body.mdpa",
    "slope_Grid.mdpa",
    "equilibrium_metadata.json",
):
    path = CASE / filename

    print(
        f"{filename:30s}"
        f"{path.stat().st_size / 1024:9.1f} KB"
    )

print()
print("Solver      : Static nonlinear MPM")
print("Load        : self-weight, g = 9.81 m/s2")
print("Load steps  : 1")
print("Max NR iter : 30")

print()
print("Output MP variables:")
print("  displacement")
print("  velocity")
print("  Cauchy stress")
print("  Almansi strain")
print("  equivalent plastic strain")

print("=" * 76)
print("STATIC EQUILIBRIUM CASE READY")
print("=" * 76)
