from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy

ROOT = Path(__file__).resolve().parents[1]
BODY = (
    ROOT
    / "benchmark"
    / "official_granular_flow_2D"
    / "granular_flow_2D_Body"
)

INITIAL = BODY / "MPM_Material_0_0.0000000.vtk"
FINAL = BODY / "MPM_Material_0_2.0000000.vtk"


def array_summary(dataset_attributes, label):
    n_arrays = dataset_attributes.GetNumberOfArrays()

    print(f"{label} arrays       : {n_arrays}")

    for i in range(n_arrays):
        arr = dataset_attributes.GetArray(i)

        if arr is None:
            continue

        name = arr.GetName() or f"unnamed_{i}"

        try:
            values = vtk_to_numpy(arr)
            print(
                f"  {name:24s} "
                f"shape={str(values.shape):16s} "
                f"dtype={values.dtype}"
            )
        except Exception as exc:
            print(f"  {name:24s} [could not convert: {exc}]")


def read_vtk(path):
    reader = vtk.vtkDataSetReader()
    reader.SetFileName(str(path))

    # Request all available legacy-VTK data arrays.
    for method_name in (
        "ReadAllScalarsOn",
        "ReadAllVectorsOn",
        "ReadAllTensorsOn",
        "ReadAllFieldsOn",
    ):
        method = getattr(reader, method_name, None)
        if method is not None:
            method()

    reader.Update()

    data = reader.GetOutput()

    if data is None:
        raise RuntimeError(f"VTK returned no dataset for {path}")

    return data


print("=" * 76)
print("KRATOS MPM BENCHMARK — NATIVE VTK INSPECTION")
print("=" * 76)
print(f"VTK version : {vtk.vtkVersion.GetVTKVersion()}")

for label, path in (("INITIAL", INITIAL), ("FINAL", FINAL)):
    print()
    print("-" * 76)
    print(label)
    print("-" * 76)

    if not path.exists():
        raise FileNotFoundError(path)

    print(f"File         : {path.name}")
    print(f"File size    : {path.stat().st_size / 1024**2:.2f} MB")

    data = read_vtk(path)

    print(f"Dataset type : {data.GetClassName()}")
    print(f"Points       : {data.GetNumberOfPoints():,}")
    print(f"Cells        : {data.GetNumberOfCells():,}")

    bounds = data.GetBounds()
    print(
        "Bounds       : "
        f"x=[{bounds[0]:.6f}, {bounds[1]:.6f}] m, "
        f"y=[{bounds[2]:.6f}, {bounds[3]:.6f}] m, "
        f"z=[{bounds[4]:.6f}, {bounds[5]:.6f}] m"
    )

    if data.GetPoints() is not None:
        xyz = vtk_to_numpy(data.GetPoints().GetData())

        print(f"Point shape  : {xyz.shape}")
        print(
            "Coordinate ranges:\n"
            f"  x : {xyz[:, 0].min():.6f} to {xyz[:, 0].max():.6f} m\n"
            f"  y : {xyz[:, 1].min():.6f} to {xyz[:, 1].max():.6f} m\n"
            f"  z : {xyz[:, 2].min():.6f} to {xyz[:, 2].max():.6f} m"
        )

    print()
    array_summary(data.GetPointData(), "Point-data")
    print()
    array_summary(data.GetCellData(), "Cell-data")
    print()
    array_summary(data.GetFieldData(), "Field-data")

print()
print("=" * 76)
print("NATIVE VTK INSPECTION COMPLETE")
print("=" * 76)
