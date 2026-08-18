from pathlib import Path
import numpy as np
import pandas as pd
import vtk
from vtk.util.numpy_support import vtk_to_numpy


ROOT = Path(__file__).resolve().parents[1]

STATIC_DIR = (
    ROOT
    / "scenarios"
    / "baseline_dry_intact"
    / "equilibrium"
    / "equilibrium_Body"
)

QS_DIR = (
    ROOT
    / "scenarios"
    / "quasistatic_ramp_smoke"
    / "F_1p00"
    / "qs_Body"
)

OUT = (
    ROOT
    / "results"
    / "tables"
    / "quasistatic_vs_static_baseline.csv"
)


def latest_mp_vtk(folder):

    files = sorted(
        folder.glob(
            "MPM_Material_*.vtk"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"No material-point VTK files in {folder}"
        )

    return files[-1]


def read_dataset(path):

    reader = vtk.vtkDataSetReader()
    reader.SetFileName(str(path))

    reader.ReadAllScalarsOn()
    reader.ReadAllVectorsOn()
    reader.ReadAllFieldsOn()

    reader.Update()

    return reader.GetOutput()


def get_cell_array(data, name):

    arr = data.GetCellData().GetArray(name)

    if arr is None:
        return None

    return vtk_to_numpy(arr).astype(float)


def analyse(path):

    data = read_dataset(path)

    xyz = vtk_to_numpy(
        data.GetPoints().GetData()
    ).astype(float)

    disp = get_cell_array(
        data,
        "MP_DISPLACEMENT",
    )

    stress = get_cell_array(
        data,
        "MP_CAUCHY_STRESS_VECTOR",
    )

    plastic = get_cell_array(
        data,
        "MP_EQUIVALENT_PLASTIC_STRAIN",
    )

    if disp is None:
        raise RuntimeError(
            f"MP_DISPLACEMENT missing in {path}"
        )

    u = np.linalg.norm(
        disp[:, :2],
        axis=1,
    )

    result = {
        "material_points": len(xyz),

        "mean_displacement_m":
            np.mean(u),

        "p95_displacement_m":
            np.percentile(u, 95),

        "max_displacement_m":
            np.max(u),
    }

    if stress is not None:

        if stress.ndim == 1:
            stress = stress[:, None]

        syy = stress[:, 1]

        result.update({
            "sigma_yy_min_kpa":
                np.min(syy) / 1000,

            "sigma_yy_max_kpa":
                np.max(syy) / 1000,
        })

    else:

        result.update({
            "sigma_yy_min_kpa": np.nan,
            "sigma_yy_max_kpa": np.nan,
        })

    if plastic is not None:

        ep = np.asarray(
            plastic
        ).reshape(-1)

        result.update({
            "max_eq_plastic_strain":
                np.max(ep),

            "plastic_fraction_gt_1e4_percent":
                100 * np.mean(ep > 1e-4),
        })

    else:

        result.update({
            "max_eq_plastic_strain": np.nan,
            "plastic_fraction_gt_1e4_percent":
                np.nan,
        })

    return xyz, result


static_file = latest_mp_vtk(
    STATIC_DIR
)

qs_file = latest_mp_vtk(
    QS_DIR
)


print("=" * 78)
print("STATIC vs QUASI-STATIC BASELINE VALIDATION")
print("=" * 78)

print(f"Static final VTK      : {static_file.name}")
print(f"Quasi-static final VTK: {qs_file.name}")
print()


xyz_static, static = analyse(
    static_file
)

xyz_qs, qs = analyse(
    qs_file
)


rows = []

metrics = [
    "material_points",
    "mean_displacement_m",
    "p95_displacement_m",
    "max_displacement_m",
    "sigma_yy_min_kpa",
    "sigma_yy_max_kpa",
    "max_eq_plastic_strain",
    "plastic_fraction_gt_1e4_percent",
]


for metric in metrics:

    a = static[metric]
    b = qs[metric]

    if (
        np.isfinite(a)
        and np.isfinite(b)
        and abs(a) > 1e-14
    ):
        rel = (
            100.0
            * abs(b - a)
            / abs(a)
        )
    elif abs(b - a) <= 1e-14:
        rel = 0.0
    else:
        rel = np.nan

    rows.append({
        "metric": metric,
        "static": a,
        "quasi_static": b,
        "relative_difference_percent": rel,
    })


df = pd.DataFrame(rows)

OUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

df.to_csv(
    OUT,
    index=False,
)


print(
    f"Material points       : "
    f"{static['material_points']:,} vs "
    f"{qs['material_points']:,}"
)

print()

print(
    f"Mean displacement     : "
    f"{static['mean_displacement_m']*1000:.3f} vs "
    f"{qs['mean_displacement_m']*1000:.3f} mm"
)

print(
    f"95th pct displacement : "
    f"{static['p95_displacement_m']*1000:.3f} vs "
    f"{qs['p95_displacement_m']*1000:.3f} mm"
)

print(
    f"Max displacement      : "
    f"{static['max_displacement_m']*1000:.3f} vs "
    f"{qs['max_displacement_m']*1000:.3f} mm"
)

print()

print(
    f"sigma_yy minimum      : "
    f"{static['sigma_yy_min_kpa']:.3f} vs "
    f"{qs['sigma_yy_min_kpa']:.3f} kPa"
)

print(
    f"sigma_yy maximum      : "
    f"{static['sigma_yy_max_kpa']:.3f} vs "
    f"{qs['sigma_yy_max_kpa']:.3f} kPa"
)

print()

print(
    f"Max plastic strain    : "
    f"{static['max_eq_plastic_strain']:.6e} vs "
    f"{qs['max_eq_plastic_strain']:.6e}"
)

print(
    f"Plastic MPs >1e-4     : "
    f"{static['plastic_fraction_gt_1e4_percent']:.3f}% vs "
    f"{qs['plastic_fraction_gt_1e4_percent']:.3f}%"
)

print()

# Same number/order of MPs is expected for this comparison.
if xyz_static.shape == xyz_qs.shape:

    coord_diff = np.linalg.norm(
        xyz_qs[:, :2]
        - xyz_static[:, :2],
        axis=1,
    )

    print(
        f"Final-coordinate RMSE : "
        f"{np.sqrt(np.mean(coord_diff**2))*1000:.4f} mm"
    )

    print(
        f"Final-coordinate max  : "
        f"{np.max(coord_diff)*1000:.4f} mm"
    )

else:

    print(
        "Coordinate comparison : skipped "
        "(different MP counts)"
    )


print()
print("Relative differences:")
print(
    df[
        [
            "metric",
            "relative_difference_percent",
        ]
    ].to_string(
        index=False,
    )
)

print()
print(f"Saved: {OUT}")
print("=" * 78)
print("BASELINE COMPARISON COMPLETE")
print("=" * 78)
