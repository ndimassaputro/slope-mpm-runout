from pathlib import Path

import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


ROOT = Path(__file__).resolve().parents[1]

CHECKPOINT = (
    ROOT
    / "scenarios"
    / "dynamic_pipeline"
    / "wet_preconditioned_F1p58_checkpoint"
    / "checkpoint_Body"
)

DYNAMIC = (
    ROOT
    / "scenarios"
    / "dynamic_pipeline"
    / "wet_preconditioned_F1p58_dynamic"
    / "dynamic_Body"
)


def read_vtk(path):
    reader = vtk.vtkDataSetReader()
    reader.SetFileName(str(path))
    reader.ReadAllScalarsOn()
    reader.ReadAllVectorsOn()
    reader.ReadAllFieldsOn()
    reader.Update()
    return reader.GetOutput()


def get_array(data, name):
    arr = data.GetCellData().GetArray(name)

    if arr is None:
        return None

    return vtk_to_numpy(arr).astype(float)


checkpoint_files = sorted(
    CHECKPOINT.glob("MPM_Material_*.vtk")
)

dynamic_files = sorted(
    DYNAMIC.glob("MPM_Material_*.vtk")
)

if not checkpoint_files:
    raise SystemExit("Checkpoint VTK not found.")

if not dynamic_files:
    raise SystemExit("Dynamic VTK not found.")


checkpoint_path = checkpoint_files[-1]
final_path = dynamic_files[-1]

d0 = read_vtk(checkpoint_path)
d1 = read_vtk(final_path)


x0 = vtk_to_numpy(
    d0.GetPoints().GetData()
).astype(float)

x1 = vtk_to_numpy(
    d1.GetPoints().GetData()
).astype(float)


if x0.shape != x1.shape:
    raise RuntimeError(
        f"Different MP shapes: {x0.shape} vs {x1.shape}"
    )


disp = np.linalg.norm(
    x1[:, :2] - x0[:, :2],
    axis=1,
)


velocity = get_array(
    d1,
    "MP_VELOCITY",
)

plastic = get_array(
    d1,
    "MP_EQUIVALENT_PLASTIC_STRAIN",
)


front0 = np.percentile(
    x0[:, 0],
    99.9,
)

front1 = np.percentile(
    x1[:, 0],
    99.9,
)

front_advance = front1 - front0


print("=" * 72)
print("F=1.58 PRECONDITIONED DYNAMIC RESPONSE")
print("=" * 72)

print("Checkpoint :", checkpoint_path.name)
print("Final VTK  :", final_path.name)
print("MPs        :", len(disp))

print()
print("--- MOVEMENT ---")

print(
    "Mean displacement :",
    f"{np.mean(disp)*1000:.6f} mm",
)

print(
    "P95 displacement  :",
    f"{np.percentile(disp,95)*1000:.6f} mm",
)

print(
    "P99 displacement  :",
    f"{np.percentile(disp,99)*1000:.6f} mm",
)

print(
    "Max displacement  :",
    f"{np.max(disp)*1000:.6f} mm",
)


if velocity is not None:

    speed = np.linalg.norm(
        velocity[:, :2],
        axis=1,
    )

    print()
    print("--- SPEED ---")

    print(
        "Mean speed :",
        f"{np.mean(speed):.6e} m/s",
    )

    print(
        "P95 speed  :",
        f"{np.percentile(speed,95):.6e} m/s",
    )

    print(
        "Max speed  :",
        f"{np.max(speed):.6e} m/s",
    )


if plastic is not None:

    plastic = np.asarray(
        plastic
    ).reshape(-1)

    print()
    print("--- PLASTICITY ---")

    print(
        "Max plastic strain :",
        f"{np.max(plastic):.6e}",
    )

    print(
        "Plastic MPs >1e-4  :",
        f"{100*np.mean(plastic > 1e-4):.3f} %",
    )


print()
print("--- RUNOUT INDICATOR ---")

print(
    "Robust front advance :",
    f"{front_advance:.6f} m",
)

print("=" * 72)
