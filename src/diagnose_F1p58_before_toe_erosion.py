from pathlib import Path
import math

import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


ROOT = Path(__file__).resolve().parents[1]

CHECKPOINT_DIR = (
    ROOT
    / "scenarios"
    / "dynamic_pipeline"
    / "wet_preconditioned_F1p58_checkpoint"
    / "checkpoint_Body"
)

DYNAMIC_DIR = (
    ROOT
    / "scenarios"
    / "dynamic_pipeline"
    / "wet_preconditioned_F1p58_dynamic"
    / "dynamic_Body"
)


# ============================================================
# Slope geometry
# ============================================================

H = 10.0
CREST_X = 6.0
SLOPE_ANGLE_DEG = 30.0

TAN_BETA = math.tan(
    math.radians(SLOPE_ANGLE_DEG)
)

TOE_X = (
    CREST_X
    + H / TAN_BETA
)


def read(path):

    reader = vtk.vtkDataSetReader()

    reader.SetFileName(str(path))
    reader.ReadAllScalarsOn()
    reader.ReadAllVectorsOn()
    reader.ReadAllFieldsOn()
    reader.Update()

    return reader.GetOutput()


def cell_array(data, name):

    a = (
        data.GetCellData()
        .GetArray(name)
    )

    if a is None:
        return None

    return vtk_to_numpy(a).astype(float)


checkpoint_files = sorted(
    CHECKPOINT_DIR.glob(
        "MPM_Material_*.vtk"
    )
)

dynamic_files = sorted(
    DYNAMIC_DIR.glob(
        "MPM_Material_*.vtk"
    )
)


if not checkpoint_files:
    raise SystemExit(
        "Checkpoint VTK not found."
    )

if not dynamic_files:
    raise SystemExit(
        "Dynamic VTK not found."
    )


checkpoint_path = checkpoint_files[-1]
dynamic_path = dynamic_files[-1]

checkpoint = read(
    checkpoint_path
)

dynamic = read(
    dynamic_path
)


x0 = vtk_to_numpy(
    checkpoint
    .GetPoints()
    .GetData()
).astype(float)

x1 = vtk_to_numpy(
    dynamic
    .GetPoints()
    .GetData()
).astype(float)


ep0 = cell_array(
    checkpoint,
    "MP_EQUIVALENT_PLASTIC_STRAIN",
)

ep1 = cell_array(
    dynamic,
    "MP_EQUIVALENT_PLASTIC_STRAIN",
)


if ep0 is None or ep1 is None:
    raise SystemExit(
        "Plastic strain array missing."
    )


ep0 = np.asarray(
    ep0
).reshape(-1)

ep1 = np.asarray(
    ep1
).reshape(-1)


if len(ep0) != len(ep1):
    raise RuntimeError(
        "Plastic strain arrays differ in size."
    )


delta_ep = ep1 - ep0


print("=" * 76)
print("F=1.58 — PLASTICITY CHECK")
print("=" * 76)

print(
    "Material points :",
    len(ep0),
)

print()
print("--- AT EQUILIBRIUM CHECKPOINT ---")

print(
    "Max plastic strain :",
    f"{np.max(ep0):.6e}",
)

print(
    "Plastic MPs >1e-4  :",
    f"{100*np.mean(ep0 > 1e-4):.3f} %",
)


print()
print("--- AFTER 0.05 s DYNAMIC ---")

print(
    "Max plastic strain :",
    f"{np.max(ep1):.6e}",
)

print(
    "Plastic MPs >1e-4  :",
    f"{100*np.mean(ep1 > 1e-4):.3f} %",
)


print()
print("--- PLASTICITY ADDED DURING DYNAMIC ---")

print(
    "Mean delta eps_p :",
    f"{np.mean(delta_ep):.6e}",
)

print(
    "P95 delta eps_p  :",
    f"{np.percentile(delta_ep,95):.6e}",
)

print(
    "Max delta eps_p  :",
    f"{np.max(delta_ep):.6e}",
)

print(
    "MPs with delta >1e-5:",
    f"{100*np.mean(delta_ep > 1e-5):.3f} %",
)


# ============================================================
# Toe erosion candidates
#
# Remove triangular wedge at original toe:
#
#              slope
#                /
#               /
#        -------/
#        <---e-->
#
# e = horizontal toe recession.
# ============================================================

print()
print("=" * 76)
print("TOE-EROSION CANDIDATE COUNT")
print("=" * 76)

print(
    "Slope height H :",
    f"{H:.3f} m",
)

print(
    "Original toe x:",
    f"{TOE_X:.6f} m",
)


for Et in (
    0.05,
    0.10,
    0.15,
):

    e = Et * H

    new_toe_x = (
        TOE_X - e
    )

    x = x0[:, 0]
    y = x0[:, 1]

    # Original 30-degree slope surface.
    surface_y = (
        (TOE_X - x)
        * TAN_BETA
    )

    # MPs in triangular toe wedge.
    mask = (
        (x >= new_toe_x)
        & (x <= TOE_X)
        & (y >= -1e-8)
        & (y <= surface_y + 1e-8)
    )

    n_remove = int(
        np.sum(mask)
    )

    fraction = (
        100
        * n_remove
        / len(x0)
    )

    print()
    print(
        f"E_t = {Et:.2f}"
    )

    print(
        f"  toe recession e : "
        f"{e:.3f} m"
    )

    print(
        f"  new toe x       : "
        f"{new_toe_x:.3f} m"
    )

    print(
        f"  MPs removed     : "
        f"{n_remove}"
    )

    print(
        f"  fraction        : "
        f"{fraction:.3f} %"
    )


print()
print("=" * 76)
print("DIAGNOSTIC COMPLETE")
print("=" * 76)
