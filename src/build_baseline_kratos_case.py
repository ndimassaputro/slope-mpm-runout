from pathlib import Path
import json
import math
import shutil

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "scenarios" / "baseline_dry_intact"
MESH = CASE / "mesh"
BENCH = ROOT / "benchmark" / "official_granular_flow_2D"

CASE.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------
# Input mesh tables generated in Phase 2A
# ---------------------------------------------------------------------

body_nodes = pd.read_csv(MESH / "body_nodes.csv")
body_elements = pd.read_csv(MESH / "body_elements.csv")

grid_nodes = pd.read_csv(MESH / "grid_nodes.csv")
grid_elements = pd.read_csv(MESH / "grid_elements.csv")


# ---------------------------------------------------------------------
# Names
# ---------------------------------------------------------------------

BODY_PART = "SlopeBody"
GRID_PART = "BackgroundGrid"

BOTTOM_PART = "BoundaryBottom"
LEFT_PART = "BoundaryLeft"


# ---------------------------------------------------------------------
# Material — idealised dry cohesive-frictional baseline
# SI units
# ---------------------------------------------------------------------

density = 2000.0              # kg/m3
young_modulus = 30.0e6       # Pa
poisson_ratio = 0.30
cohesion = 20.0e3             # Pa
friction_deg = 28.0
dilatancy_deg = 0.0

friction_rad = math.radians(friction_deg)
dilatancy_rad = math.radians(dilatancy_deg)

mp_per_element = 3


# ---------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------

def write_ids(f, values, indent="        "):
    for value in values:
        f.write(f"{indent}{int(value)}\n")


# ---------------------------------------------------------------------
# BODY .mdpa
# ---------------------------------------------------------------------

body_path = CASE / "slope_Body.mdpa"

with body_path.open("w") as f:

    f.write("Begin ModelPartData\n")
    f.write("// VARIABLE_NAME value\n")
    f.write("End ModelPartData\n\n")

    f.write("Begin Properties 0\n")
    f.write("End Properties\n\n")

    f.write("Begin Nodes\n")

    for row in body_nodes.itertuples(index=False):
        f.write(
            f"{int(row.node_id):8d} "
            f"{row.x_m:.9f} "
            f"{row.y_m:.9f} "
            f"{row.z_m:.9f}\n"
        )

    f.write("End Nodes\n\n")

    f.write("Begin Elements MPMUpdatedLagrangian2D3N\n")

    for row in body_elements.itertuples(index=False):
        f.write(
            f"{int(row.element_id):8d} "
            f"0 "
            f"{int(row.node_1):8d} "
            f"{int(row.node_2):8d} "
            f"{int(row.node_3):8d}\n"
        )

    f.write("End Elements\n\n")

    f.write(f"Begin SubModelPart {BODY_PART}\n")

    f.write("    Begin SubModelPartNodes\n")
    write_ids(
        f,
        body_nodes["node_id"],
        indent="        ",
    )
    f.write("    End SubModelPartNodes\n")

    f.write("    Begin SubModelPartElements\n")
    write_ids(
        f,
        body_elements["element_id"],
        indent="        ",
    )
    f.write("    End SubModelPartElements\n")

    f.write("    Begin SubModelPartConditions\n")
    f.write("    End SubModelPartConditions\n")

    f.write("End SubModelPart\n")


# ---------------------------------------------------------------------
# GRID .mdpa
# ---------------------------------------------------------------------

grid_path = CASE / "slope_Grid.mdpa"

tol = 1.0e-9

bottom_nodes = grid_nodes.loc[
    grid_nodes["y_m"].abs() <= tol,
    "node_id",
].astype(int)

left_nodes = grid_nodes.loc[
    grid_nodes["x_m"].abs() <= tol,
    "node_id",
].astype(int)

with grid_path.open("w") as f:

    f.write("Begin ModelPartData\n")
    f.write("// VARIABLE_NAME value\n")
    f.write("End ModelPartData\n\n")

    f.write("Begin Properties 0\n")
    f.write("End Properties\n\n")

    f.write("Begin Nodes\n")

    for row in grid_nodes.itertuples(index=False):
        f.write(
            f"{int(row.node_id):8d} "
            f"{row.x_m:.9f} "
            f"{row.y_m:.9f} "
            f"{row.z_m:.9f}\n"
        )

    f.write("End Nodes\n\n")

    f.write("Begin Elements Element2D3N\n")

    for row in grid_elements.itertuples(index=False):
        f.write(
            f"{int(row.element_id):8d} "
            f"0 "
            f"{int(row.node_1):8d} "
            f"{int(row.node_2):8d} "
            f"{int(row.node_3):8d}\n"
        )

    f.write("End Elements\n\n")

    # Entire computational background grid
    f.write(f"Begin SubModelPart {GRID_PART}\n")

    f.write("    Begin SubModelPartNodes\n")
    write_ids(
        f,
        grid_nodes["node_id"],
        indent="        ",
    )
    f.write("    End SubModelPartNodes\n")

    f.write("    Begin SubModelPartElements\n")
    write_ids(
        f,
        grid_elements["element_id"],
        indent="        ",
    )
    f.write("    End SubModelPartElements\n")

    f.write("    Begin SubModelPartConditions\n")
    f.write("    End SubModelPartConditions\n")

    f.write("End SubModelPart\n\n")

    # Bottom: ux = uy = 0
    f.write(f"Begin SubModelPart {BOTTOM_PART}\n")

    f.write("    Begin SubModelPartNodes\n")
    write_ids(
        f,
        bottom_nodes,
        indent="        ",
    )
    f.write("    End SubModelPartNodes\n")

    f.write("    Begin SubModelPartElements\n")
    f.write("    End SubModelPartElements\n")

    f.write("    Begin SubModelPartConditions\n")
    f.write("    End SubModelPartConditions\n")

    f.write("End SubModelPart\n\n")

    # Left: ux = 0, uy free
    f.write(f"Begin SubModelPart {LEFT_PART}\n")

    f.write("    Begin SubModelPartNodes\n")
    write_ids(
        f,
        left_nodes,
        indent="        ",
    )
    f.write("    End SubModelPartNodes\n")

    f.write("    Begin SubModelPartElements\n")
    f.write("    End SubModelPartElements\n")

    f.write("    Begin SubModelPartConditions\n")
    f.write("    End SubModelPartConditions\n")

    f.write("End SubModelPart\n")


# ---------------------------------------------------------------------
# ParticleMaterials.json
# ---------------------------------------------------------------------

materials = {
    "properties": [
        {
            "model_part_name": f"Initial_MPM_Material.{BODY_PART}",
            "properties_id": 1,
            "Material": {
                "constitutive_law": {
                    "name": "HenckyMCPlasticPlaneStrain2DLaw"
                },
                "Variables": {
                    "THICKNESS": 1.0,
                    "MATERIAL_POINTS_PER_ELEMENT": mp_per_element,
                    "DENSITY": density,
                    "YOUNG_MODULUS": young_modulus,
                    "POISSON_RATIO": poisson_ratio,
                    "COHESION": cohesion,
                    "INTERNAL_FRICTION_ANGLE": friction_rad,
                    "INTERNAL_DILATANCY_ANGLE": dilatancy_rad,
                },
                "Tables": {},
            },
        }
    ]
}

with (CASE / "ParticleMaterials.json").open("w") as f:
    json.dump(materials, f, indent=4)


# ---------------------------------------------------------------------
# ProjectParameters.json
#
# IMPORTANT:
# This is intentionally a tiny PRE-FLIGHT run:
# end time = 0.002 s
# dt       = 0.001 s
#
# It is NOT yet the scientific baseline simulation.
# ---------------------------------------------------------------------

project = {
    "problem_data": {
        "problem_name": "slope_baseline_preflight",
        "parallel_type": "OpenMP",
        "echo_level": 0,
        "start_time": 0.0,
        "end_time": 0.002,
    },

    "solver_settings": {
        "solver_type": "Dynamic",
        "model_part_name": "MPM_Material",
        "domain_size": 2,
        "echo_level": 0,
        "analysis_type": "non_linear",

        "time_integration_method": "implicit",
        "scheme_type": "newmark",

        "model_import_settings": {
            "input_type": "mdpa",
            "input_filename": "slope_Body",
        },

        "material_import_settings": {
            "materials_filename": "ParticleMaterials.json",
        },

        "time_stepping": {
            "time_step": 0.001,
        },

        "convergence_criterion": "residual_criterion",

        "displacement_relative_tolerance": 1.0e-4,
        "displacement_absolute_tolerance": 1.0e-9,

        "residual_relative_tolerance": 1.0e-4,
        "residual_absolute_tolerance": 1.0e-9,

        "max_iteration": 20,

        "problem_domain_sub_model_part_list": [
            BODY_PART,
            GRID_PART,
        ],

        "processes_sub_model_part_list": [
            BOTTOM_PART,
            LEFT_PART,
        ],

        "grid_model_import_settings": {
            "input_type": "mdpa",
            "input_filename": "slope_Grid",
        },

        "pressure_dofs": False,

        "linear_solver_settings": {
            "solver_type": "LinearSolversApplication.sparse_lu",
            "scaling": False,
        },
    },

    "processes": {

        "constraints_process_list": [

            # Bottom: fixed in x and y.
            {
                "python_module": "assign_vector_variable_process",
                "kratos_module": "KratosMultiphysics",
                "Parameters": {
                    "model_part_name":
                        f"Background_Grid.{BOTTOM_PART}",
                    "variable_name": "DISPLACEMENT",
                    "constrained": [True, True, True],
                    "value": [0.0, 0.0, 0.0],
                    "interval": [0.0, "End"],
                },
            },

            # Left: roller boundary.
            {
                "python_module": "assign_vector_variable_process",
                "kratos_module": "KratosMultiphysics",
                "Parameters": {
                    "model_part_name":
                        f"Background_Grid.{LEFT_PART}",
                    "variable_name": "DISPLACEMENT",
                    "constrained": [True, False, True],
                    "value": [0.0, 0.0, 0.0],
                    "interval": [0.0, "End"],
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
                    "model_part_name": "MPM_Material",
                    "variable_name": "MP_VOLUME_ACCELERATION",
                    "modulus": 9.81,
                    "direction": [0.0, -1.0, 0.0],
                },
            }
        ],
    },

    "output_processes": {

        # VTK only. No GiD output for the preflight.
        "body_output_process": [
            {
                "python_module": "mpm_vtk_output_process",
                "kratos_module":
                    "KratosMultiphysics.MPMApplication",
                "process_name": "MPMVTKOutputProcess",
                "Parameters": {
                    "model_part_name": "MPM_Material",
                    "output_path": "preflight_Body",
                    "output_control_type": "time",
                    "output_interval": 0.001,
                    "gauss_point_variables_in_elements": [
                        "MP_VELOCITY",
                        "MP_DISPLACEMENT",
                    ],
                },
            }
        ],

        "grid_output_process": [
            {
                "python_module": "vtk_output_process",
                "kratos_module": "KratosMultiphysics",
                "process_name": "VTKOutputProcess",
                "Parameters": {
                    "model_part_name": "Background_Grid",
                    "output_path": "preflight_Grid",
                    "output_control_type": "time",
                    "output_interval": 0.001,
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
    json.dump(project, f, indent=4)


# ---------------------------------------------------------------------
# MainKratos.py
# Use the already verified official Kratos entry script.
# ---------------------------------------------------------------------

shutil.copy2(
    BENCH / "MainKratos.py",
    CASE / "MainKratos.py",
)


# ---------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------

metadata = {
    "case": "baseline_dry_intact",
    "stage": "preflight",

    "material": {
        "description":
            "idealised cohesive-frictional dry baseline",
        "density_kg_m3": density,
        "young_modulus_pa": young_modulus,
        "poisson_ratio": poisson_ratio,
        "cohesion_pa": cohesion,
        "friction_angle_deg": friction_deg,
        "dilatancy_angle_deg": dilatancy_deg,
        "material_points_per_element": mp_per_element,
    },

    "boundary_conditions": {
        "bottom": "ux=uy=0",
        "left": "ux=0, uy free",
        "right": "free",
        "top": "free",
    },

    "preflight": {
        "end_time_s": 0.002,
        "time_step_s": 0.001,
        "purpose":
            "Input, material-point generation, boundary-condition "
            "and solver compatibility check only.",
    },
}

with (CASE / "case_metadata.json").open("w") as f:
    json.dump(metadata, f, indent=4)


# ---------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------

expected_mps = len(body_elements) * mp_per_element

print("=" * 76)
print("PHASE 2B-2 — KRATOS BASELINE CASE GENERATION")
print("=" * 76)

print(f"Body nodes             : {len(body_nodes):,}")
print(f"Body elements          : {len(body_elements):,}")

print(f"MPs per element        : {mp_per_element}")
print(f"Expected material pts  : {expected_mps:,}")

print(f"Grid nodes             : {len(grid_nodes):,}")
print(f"Grid elements          : {len(grid_elements):,}")

print(f"Bottom boundary nodes  : {len(bottom_nodes):,}")
print(f"Left boundary nodes    : {len(left_nodes):,}")

print()
print("Material:")
print(f"  density              : {density:.1f} kg/m3")
print(f"  E                    : {young_modulus/1e6:.1f} MPa")
print(f"  nu                   : {poisson_ratio:.2f}")
print(f"  cohesion             : {cohesion/1000:.1f} kPa")
print(f"  friction angle       : {friction_deg:.1f} deg")
print(f"  dilatancy angle      : {dilatancy_deg:.1f} deg")

print()
print("Files generated:")

for name in (
    "MainKratos.py",
    "ProjectParameters.json",
    "ParticleMaterials.json",
    "slope_Body.mdpa",
    "slope_Grid.mdpa",
    "case_metadata.json",
):
    path = CASE / name
    print(f"  {name:28s} {path.stat().st_size/1024:.1f} KB")

print()
print("PRE-FLIGHT ONLY:")
print("  end time = 0.002 s")
print("  dt       = 0.001 s")
print("  steps    = 2")

print("=" * 76)
print("CASE GENERATION COMPLETE")
print("=" * 76)
