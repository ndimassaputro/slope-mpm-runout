from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import vtk
from vtk.util.numpy_support import vtk_to_numpy


ROOT = Path(__file__).resolve().parents[1]

CASE = (
    ROOT
    / "scenarios"
    / "baseline_dry_intact"
    / "equilibrium"
)

MESH = (
    ROOT
    / "scenarios"
    / "baseline_dry_intact"
    / "mesh"
)

FIG = ROOT / "results" / "figures"
TAB = ROOT / "results" / "tables"

FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)


BODY_INITIAL = (
    CASE
    / "equilibrium_Body"
    / "MPM_Material_0_0.0000000.vtk"
)

BODY_FINAL = (
    CASE
    / "equilibrium_Body"
    / "MPM_Material_0_1.1000000.vtk"
)

GRID_FINAL = (
    CASE
    / "equilibrium_Grid"
    / "Background_Grid_0_1.1000000.vtk"
)


# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------

def read_vtk(path):

    reader = vtk.vtkDataSetReader()
    reader.SetFileName(str(path))

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
        raise RuntimeError(
            f"Could not read {path}"
        )

    return data


def get_array(attributes, name):

    arr = attributes.GetArray(name)

    if arr is None:
        return None

    return vtk_to_numpy(arr).astype(float)


def list_arrays(attributes):

    output = []

    for i in range(
        attributes.GetNumberOfArrays()
    ):
        arr = attributes.GetArray(i)

        if arr is not None:
            output.append(
                (
                    arr.GetName(),
                    vtk_to_numpy(arr).shape,
                )
            )

    return output


# ---------------------------------------------------------------------
# Read material-point outputs
# ---------------------------------------------------------------------

initial = read_vtk(BODY_INITIAL)
final = read_vtk(BODY_FINAL)

xyz0 = vtk_to_numpy(
    initial.GetPoints().GetData()
).astype(float)

xyz1 = vtk_to_numpy(
    final.GetPoints().GetData()
).astype(float)


cd = final.GetCellData()

disp = get_array(
    cd,
    "MP_DISPLACEMENT",
)

velocity = get_array(
    cd,
    "MP_VELOCITY",
)

stress = get_array(
    cd,
    "MP_CAUCHY_STRESS_VECTOR",
)

strain = get_array(
    cd,
    "MP_ALMANSI_STRAIN_VECTOR",
)

plastic = get_array(
    cd,
    "MP_EQUIVALENT_PLASTIC_STRAIN",
)


print("=" * 76)
print("PHASE 2D — STATIC EQUILIBRIUM DIAGNOSTICS")
print("=" * 76)

print()
print("Material-point VTK arrays:")

for name, shape in list_arrays(cd):
    print(
        f"  {name:35s}"
        f"{str(shape):>18s}"
    )


# ---------------------------------------------------------------------
# Basic MP checks
# ---------------------------------------------------------------------

n0 = len(xyz0)
n1 = len(xyz1)

if n0 != n1:
    raise RuntimeError(
        f"Material point count changed: {n0} -> {n1}"
    )

if disp is None:
    raise RuntimeError(
        "MP_DISPLACEMENT not found"
    )

disp_xy = disp[:, :2]

disp_mag = np.linalg.norm(
    disp_xy,
    axis=1,
)

max_disp = np.max(disp_mag)
p95_disp = np.percentile(
    disp_mag,
    95,
)

mean_disp = np.mean(disp_mag)


# Compare field displacement against actual point movement.
coord_delta = xyz1[:, :2] - xyz0[:, :2]

coord_consistency = np.linalg.norm(
    coord_delta - disp_xy,
    axis=1,
)

coord_rmse = np.sqrt(
    np.mean(coord_consistency**2)
)

coord_max_error = np.max(
    coord_consistency
)


# ---------------------------------------------------------------------
# Velocity
# ---------------------------------------------------------------------

if velocity is not None:

    speed = np.linalg.norm(
        velocity[:, :2],
        axis=1,
    )

    max_speed = np.max(speed)
    p95_speed = np.percentile(
        speed,
        95,
    )

else:

    max_speed = np.nan
    p95_speed = np.nan


# ---------------------------------------------------------------------
# Stress
# ---------------------------------------------------------------------

if stress is not None:

    if stress.ndim == 1:
        stress = stress[:, None]

    sigma_xx = stress[:, 0]

    sigma_yy = (
        stress[:, 1]
        if stress.shape[1] >= 2
        else np.full(n1, np.nan)
    )

    tau_xy = (
        stress[:, -1]
        if stress.shape[1] >= 3
        else np.full(n1, np.nan)
    )

else:

    sigma_xx = np.full(n1, np.nan)
    sigma_yy = np.full(n1, np.nan)
    tau_xy = np.full(n1, np.nan)


# ---------------------------------------------------------------------
# Plasticity
# ---------------------------------------------------------------------

if plastic is not None:

    plastic = np.asarray(
        plastic
    ).reshape(-1)

    max_plastic = np.max(plastic)

    plastic_fraction_1e8 = (
        100.0
        * np.mean(plastic > 1.0e-8)
    )

    plastic_fraction_1e4 = (
        100.0
        * np.mean(plastic > 1.0e-4)
    )

else:

    plastic = np.full(n1, np.nan)

    max_plastic = np.nan
    plastic_fraction_1e8 = np.nan
    plastic_fraction_1e4 = np.nan


# ---------------------------------------------------------------------
# Exact model weight from triangulated body mesh
# ---------------------------------------------------------------------

nodes = pd.read_csv(
    MESH / "body_nodes.csv"
)

elements = pd.read_csv(
    MESH / "body_elements.csv"
)

xy = nodes[
    ["x_m", "y_m"]
].to_numpy()

areas = []

for row in elements.itertuples(index=False):

    ids = np.array(
        [
            row.node_1,
            row.node_2,
            row.node_3,
        ],
        dtype=int,
    ) - 1

    p = xy[ids]

    area = 0.5 * abs(
        (p[1, 0] - p[0, 0])
        * (p[2, 1] - p[0, 1])
        -
        (p[2, 0] - p[0, 0])
        * (p[1, 1] - p[0, 1])
    )

    areas.append(area)


area = float(
    np.sum(areas)
)

density = 2000.0
thickness = 1.0
gravity = 9.81

mass = (
    area
    * thickness
    * density
)

weight = mass * gravity


# ---------------------------------------------------------------------
# Grid reactions
# ---------------------------------------------------------------------

grid = read_vtk(GRID_FINAL)

grid_xyz = vtk_to_numpy(
    grid.GetPoints().GetData()
).astype(float)

grid_pd = grid.GetPointData()

reaction = get_array(
    grid_pd,
    "REACTION",
)

if reaction is None:

    reaction_x = np.nan
    reaction_y = np.nan
    balance_error = np.nan

else:

    # Only bottom nodes have constrained vertical displacement.
    bottom = np.isclose(
        grid_xyz[:, 1],
        0.0,
        atol=1.0e-10,
    )

    reaction_x = np.sum(
        reaction[bottom, 0]
    )

    reaction_y = np.sum(
        reaction[bottom, 1]
    )

    balance_error = (
        100.0
        * abs(abs(reaction_y) - weight)
        / weight
    )


# ---------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------

summary = pd.DataFrame({
    "metric": [
        "material_points_initial",
        "material_points_final",
        "body_area_m2",
        "body_mass_kg_per_m",
        "body_weight_N_per_m",
        "bottom_reaction_x_N_per_m",
        "bottom_reaction_y_N_per_m",
        "vertical_force_balance_error_percent",
        "mean_displacement_m",
        "p95_displacement_m",
        "max_displacement_m",
        "p95_velocity_m_s",
        "max_velocity_m_s",
        "coordinate_displacement_rmse_m",
        "coordinate_displacement_max_error_m",
        "sigma_xx_min_kPa",
        "sigma_xx_max_kPa",
        "sigma_yy_min_kPa",
        "sigma_yy_max_kPa",
        "tau_xy_min_kPa",
        "tau_xy_max_kPa",
        "max_equivalent_plastic_strain",
        "plastic_mp_fraction_gt_1e8_percent",
        "plastic_mp_fraction_gt_1e4_percent",
    ],

    "value": [
        n0,
        n1,
        area,
        mass,
        weight,
        reaction_x,
        reaction_y,
        balance_error,
        mean_disp,
        p95_disp,
        max_disp,
        p95_speed,
        max_speed,
        coord_rmse,
        coord_max_error,
        np.nanmin(sigma_xx) / 1000,
        np.nanmax(sigma_xx) / 1000,
        np.nanmin(sigma_yy) / 1000,
        np.nanmax(sigma_yy) / 1000,
        np.nanmin(tau_xy) / 1000,
        np.nanmax(tau_xy) / 1000,
        max_plastic,
        plastic_fraction_1e8,
        plastic_fraction_1e4,
    ],
})

summary_path = (
    TAB
    / "static_equilibrium_summary.csv"
)

summary.to_csv(
    summary_path,
    index=False,
)


# ---------------------------------------------------------------------
# Publication-style figure
# ---------------------------------------------------------------------

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.linewidth": 0.8,
    "savefig.dpi": 400,
    "savefig.bbox": "tight",
})


def finish_axis(ax):

    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.8)
        spine.set_color("0.15")

    ax.set_xlabel(
        "Horizontal coordinate, x (m)"
    )

    ax.set_ylabel(
        "Vertical coordinate, y (m)"
    )

    ax.set_aspect(
        "equal",
        adjustable="box",
    )


fig, axes = plt.subplots(
    2,
    2,
    figsize=(10.0, 6.8),
)


# (a) initial / equilibrium geometry
ax = axes[0, 0]

sample = slice(None, None, 2)

ax.scatter(
    xyz0[sample, 0],
    xyz0[sample, 1],
    s=1.3,
    c="0.75",
    alpha=0.35,
    edgecolors="none",
    label="Initial",
)

ax.scatter(
    xyz1[sample, 0],
    xyz1[sample, 1],
    s=1.3,
    c="0.10",
    alpha=0.55,
    edgecolors="none",
    label="Self-weight equilibrium",
)

ax.legend(
    frameon=False,
    markerscale=4,
)

ax.set_title(
    "(a) Dry/intact equilibrium configuration",
    loc="left",
    fontweight="bold",
)

finish_axis(ax)


# (b) displacement magnitude
ax = axes[0, 1]

sc = ax.scatter(
    xyz1[:, 0],
    xyz1[:, 1],
    c=disp_mag * 1000,
    cmap="Greys",
    s=5,
    edgecolors="none",
)

cb = fig.colorbar(
    sc,
    ax=ax,
    shrink=0.88,
)

cb.set_label(
    "Displacement magnitude (mm)"
)

ax.set_title(
    "(b) Material-point displacement",
    loc="left",
    fontweight="bold",
)

finish_axis(ax)


# (c) vertical stress
ax = axes[1, 0]

sc = ax.scatter(
    xyz1[:, 0],
    xyz1[:, 1],
    c=sigma_yy / 1000,
    cmap="Greys",
    s=5,
    edgecolors="none",
)

cb = fig.colorbar(
    sc,
    ax=ax,
    shrink=0.88,
)

cb.set_label(
    r"$\sigma_{yy}$ (kPa)"
)

ax.set_title(
    "(c) Vertical Cauchy stress",
    loc="left",
    fontweight="bold",
)

finish_axis(ax)


# (d) plastic strain
ax = axes[1, 1]

sc = ax.scatter(
    xyz1[:, 0],
    xyz1[:, 1],
    c=plastic,
    cmap="Greys",
    s=5,
    edgecolors="none",
)

cb = fig.colorbar(
    sc,
    ax=ax,
    shrink=0.88,
)

cb.set_label(
    "Equivalent plastic strain"
)

ax.set_title(
    "(d) Plasticity distribution",
    loc="left",
    fontweight="bold",
)

finish_axis(ax)


fig.tight_layout()

png = (
    FIG
    / "static_equilibrium_diagnostics.png"
)

pdf = (
    FIG
    / "static_equilibrium_diagnostics.pdf"
)

fig.savefig(png)
fig.savefig(pdf)

plt.close(fig)


# ---------------------------------------------------------------------
# Terminal report
# ---------------------------------------------------------------------

print()
print("=" * 76)
print("EQUILIBRIUM SUMMARY")
print("=" * 76)

print(
    f"Material points       : "
    f"{n0:,} -> {n1:,}"
)

print(
    f"Body area             : "
    f"{area:.6f} m2"
)

print(
    f"Total weight          : "
    f"{weight / 1000:.3f} kN/m"
)

print(
    f"Bottom reaction Ry    : "
    f"{reaction_y / 1000:.3f} kN/m"
)

print(
    f"Force-balance error   : "
    f"{balance_error:.4f} %"
)

print()
print(
    f"Mean displacement     : "
    f"{mean_disp * 1000:.3f} mm"
)

print(
    f"95th pct displacement : "
    f"{p95_disp * 1000:.3f} mm"
)

print(
    f"Max displacement      : "
    f"{max_disp * 1000:.3f} mm"
)

print()
print(
    f"sigma_yy range        : "
    f"{np.nanmin(sigma_yy)/1000:.2f} to "
    f"{np.nanmax(sigma_yy)/1000:.2f} kPa"
)

print(
    f"Max eq. plastic strain: "
    f"{max_plastic:.6e}"
)

print(
    f"Plastic MPs > 1e-4    : "
    f"{plastic_fraction_1e4:.3f} %"
)

print()
print(
    f"Coord/disp RMSE       : "
    f"{coord_rmse:.3e} m"
)

print()
print(f"Saved: {summary_path}")
print(f"Saved: {png}")
print(f"Saved: {pdf}")

print("=" * 76)
print("PHASE 2D COMPLETE")
print("=" * 76)
