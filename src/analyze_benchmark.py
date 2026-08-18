from pathlib import Path
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import vtk
from vtk.util.numpy_support import vtk_to_numpy


ROOT = Path(__file__).resolve().parents[1]

BODY = (
    ROOT
    / "benchmark"
    / "official_granular_flow_2D"
    / "granular_flow_2D_Body"
)

RESULTS_TABLE = ROOT / "results" / "tables"
RESULTS_FIGURE = ROOT / "results" / "figures"

RESULTS_TABLE.mkdir(parents=True, exist_ok=True)
RESULTS_FIGURE.mkdir(parents=True, exist_ok=True)


def apply_publication_style():
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 10,
        "legend.fontsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "axes.linewidth": 0.8,
        "figure.dpi": 120,
        "savefig.dpi": 400,
        "savefig.bbox": "tight",
    })


def clean_axis(ax, grid=True):
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.8)
        spine.set_color("0.15")

    if grid:
        ax.grid(axis="y", color="0.90", linewidth=0.6)

    ax.set_axisbelow(True)


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

    if data is None or data.GetNumberOfPoints() == 0:
        raise RuntimeError(f"Could not read material-point dataset: {path}")

    xyz = vtk_to_numpy(data.GetPoints().GetData()).astype(float)

    cell_data = data.GetCellData()

    velocity_array = cell_data.GetArray("MP_VELOCITY")
    displacement_array = cell_data.GetArray("MP_DISPLACEMENT")

    velocity = (
        vtk_to_numpy(velocity_array).astype(float)
        if velocity_array is not None
        else None
    )

    displacement = (
        vtk_to_numpy(displacement_array).astype(float)
        if displacement_array is not None
        else None
    )

    return xyz, velocity, displacement


def parse_time(path):
    match = re.search(r"_0_(\d+\.\d+)\.vtk$", path.name)

    if match is None:
        raise ValueError(f"Could not parse time from {path.name}")

    return float(match.group(1))


files = sorted(
    BODY.glob("MPM_Material_0_*.vtk"),
    key=parse_time,
)

if not files:
    raise FileNotFoundError(f"No material-point VTK files found in {BODY}")


print("=" * 76)
print("PHASE 1F — KRATOS GRANULAR-FLOW BENCHMARK ANALYSIS")
print("=" * 76)
print(f"VTK files detected : {len(files)}")


# ---------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------

xyz0, velocity0, displacement0 = read_vtk(files[0])

x0 = xyz0[:, 0]
y0 = xyz0[:, 1]

initial_x_min = np.min(x0)
initial_x_max = np.max(x0)
initial_y_min = np.min(y0)
initial_y_max = np.max(y0)

initial_width = initial_x_max - initial_x_min
initial_height = initial_y_max - initial_y_min

initial_front_p999 = np.percentile(x0, 99.9)


# ---------------------------------------------------------------------
# Time-series analysis
# ---------------------------------------------------------------------

records = []

for i, path in enumerate(files, start=1):

    time = parse_time(path)

    xyz, velocity, displacement = read_vtk(path)

    x = xyz[:, 0]
    y = xyz[:, 1]

    if velocity is not None:
        speed = np.linalg.norm(velocity[:, :2], axis=1)

        mean_speed = np.mean(speed)
        p95_speed = np.percentile(speed, 95)
        max_speed = np.max(speed)

    else:
        mean_speed = np.nan
        p95_speed = np.nan
        max_speed = np.nan

    if displacement is not None:
        disp_mag = np.linalg.norm(displacement[:, :2], axis=1)

        mean_disp = np.mean(disp_mag)
        p95_disp = np.percentile(disp_mag, 95)
        max_disp = np.max(disp_mag)

    else:
        mean_disp = np.nan
        p95_disp = np.nan
        max_disp = np.nan

    x_p999 = np.percentile(x, 99.9)
    x_p995 = np.percentile(x, 99.5)

    records.append({
        "time_s": time,
        "n_material_points": len(x),
        "x_min_m": np.min(x),
        "x_max_m": np.max(x),
        "x_p99_5_m": x_p995,
        "x_p99_9_m": x_p999,
        "y_min_m": np.min(y),
        "y_max_m": np.max(y),
        "y_p99_9_m": np.percentile(y, 99.9),
        "raw_front_advance_m": np.max(x) - initial_x_max,
        "robust_front_advance_m": x_p999 - initial_front_p999,
        "normalized_raw_runout": (
            (np.max(x) - initial_x_max) / initial_width
        ),
        "mean_speed_m_s": mean_speed,
        "p95_speed_m_s": p95_speed,
        "max_speed_m_s": max_speed,
        "mean_displacement_m": mean_disp,
        "p95_displacement_m": p95_disp,
        "max_displacement_m": max_disp,
    })

    if i == 1 or i % 25 == 0 or i == len(files):
        print(
            f"[{i:3d}/{len(files)}] "
            f"t={time:7.4f} s | "
            f"xmax={np.max(x):.4f} m"
        )


df = pd.DataFrame(records)

time_series_path = RESULTS_TABLE / "benchmark_time_series.csv"
df.to_csv(time_series_path, index=False)


# ---------------------------------------------------------------------
# Final metrics
# ---------------------------------------------------------------------

final = df.iloc[-1]

peak_speed_idx = df["max_speed_m_s"].idxmax()
peak_speed_row = df.loc[peak_speed_idx]

summary = pd.DataFrame({
    "metric": [
        "material_points_initial",
        "material_points_final",
        "initial_width_m",
        "initial_height_m",
        "initial_front_x_m",
        "final_front_x_m",
        "raw_front_advance_m",
        "robust_front_advance_p99_9_m",
        "normalized_raw_runout_L0",
        "final_max_height_m",
        "maximum_particle_displacement_m",
        "peak_particle_speed_m_s",
        "time_of_peak_speed_s",
    ],
    "value": [
        len(x0),
        int(final["n_material_points"]),
        initial_width,
        initial_height,
        initial_x_max,
        final["x_max_m"],
        final["raw_front_advance_m"],
        final["robust_front_advance_m"],
        final["normalized_raw_runout"],
        final["y_max_m"],
        final["max_displacement_m"],
        peak_speed_row["max_speed_m_s"],
        peak_speed_row["time_s"],
    ],
})

summary_path = RESULTS_TABLE / "benchmark_summary.csv"
summary.to_csv(summary_path, index=False)


# ---------------------------------------------------------------------
# Selected configurations
# ---------------------------------------------------------------------

target_times = [0.0, 0.5, 1.0, 2.0]
snapshots = {}

available_times = np.array([parse_time(p) for p in files])

for target in target_times:
    idx = np.argmin(np.abs(available_times - target))
    path = files[idx]
    time = available_times[idx]

    xyz, velocity, displacement = read_vtk(path)

    snapshots[target] = {
        "actual_time": time,
        "xyz": xyz,
    }


# ---------------------------------------------------------------------
# Publication-style figure
# ---------------------------------------------------------------------

apply_publication_style()

fig, axes = plt.subplots(2, 2, figsize=(10.2, 6.6))


# (a) Initial/final configuration
ax = axes[0, 0]

xyz_initial = snapshots[0.0]["xyz"]
xyz_final = snapshots[2.0]["xyz"]

ax.scatter(
    xyz_initial[:, 0],
    xyz_initial[:, 1],
    s=0.20,
    alpha=0.30,
    c="0.70",
    rasterized=True,
    label="Initial",
)

ax.scatter(
    xyz_final[:, 0],
    xyz_final[:, 1],
    s=0.20,
    alpha=0.50,
    c="0.15",
    rasterized=True,
    label="Final",
)

ax.axvline(
    initial_x_max,
    linestyle="--",
    linewidth=0.9,
    color="0.35",
)

ax.set_xlabel("Horizontal coordinate, x (m)")
ax.set_ylabel("Vertical coordinate, y (m)")
ax.set_title("(a) Initial and final material-point configuration",
             loc="left", fontweight="bold")
ax.legend(frameon=False, markerscale=8)
ax.set_aspect("equal", adjustable="box")
clean_axis(ax, grid=False)


# (b) Runout evolution
ax = axes[0, 1]

ax.plot(
    df["time_s"],
    df["raw_front_advance_m"],
    linewidth=1.3,
    color="0.10",
    label="Maximum-x front",
)

ax.plot(
    df["time_s"],
    df["robust_front_advance_m"],
    linewidth=1.1,
    linestyle="--",
    color="0.45",
    label="99.9th percentile front",
)

ax.set_xlabel("Time (s)")
ax.set_ylabel("Front advance (m)")
ax.set_title("(b) Runout evolution", loc="left", fontweight="bold")
ax.legend(frameon=False)
clean_axis(ax)


# (c) Selected deformation states
ax = axes[1, 0]

markers = ["o", "s", "^", "D"]
sizes = [0.16, 0.18, 0.20, 0.22]
alphas = [0.20, 0.30, 0.42, 0.60]
grays = ["0.80", "0.62", "0.40", "0.10"]

for target, marker, size, alpha, gray in zip(
    target_times, markers, sizes, alphas, grays
):
    snap = snapshots[target]
    xyz = snap["xyz"]

    ax.scatter(
        xyz[:, 0],
        xyz[:, 1],
        s=size,
        marker=marker,
        alpha=alpha,
        c=gray,
        rasterized=True,
        label=f"{snap['actual_time']:.2f} s",
    )

ax.set_xlabel("Horizontal coordinate, x (m)")
ax.set_ylabel("Vertical coordinate, y (m)")
ax.set_title("(c) Large-deformation evolution",
             loc="left", fontweight="bold")
ax.set_aspect("equal", adjustable="box")
ax.legend(frameon=False, markerscale=8)
clean_axis(ax, grid=False)


# (d) Velocity evolution
ax = axes[1, 1]

ax.plot(
    df["time_s"],
    df["mean_speed_m_s"],
    linewidth=1.2,
    color="0.45",
    label="Mean",
)

ax.plot(
    df["time_s"],
    df["p95_speed_m_s"],
    linewidth=1.2,
    color="0.10",
    label="95th percentile",
)

ax.set_xlabel("Time (s)")
ax.set_ylabel("Material-point speed (m/s)")
ax.set_title("(d) Material-point velocity response",
             loc="left", fontweight="bold")
ax.legend(frameon=False)
clean_axis(ax)


fig.tight_layout()

figure_png = RESULTS_FIGURE / "benchmark_validation.png"
figure_pdf = RESULTS_FIGURE / "benchmark_validation.pdf"

fig.savefig(figure_png)
fig.savefig(figure_pdf)

plt.close(fig)


# ---------------------------------------------------------------------
# Terminal summary
# ---------------------------------------------------------------------

print()
print("=" * 76)
print("BENCHMARK SUMMARY")
print("=" * 76)

print(f"Material points       : {len(x0):,}")
print(f"Initial width         : {initial_width:.6f} m")
print(f"Initial height        : {initial_height:.6f} m")
print(f"Initial front         : {initial_x_max:.6f} m")
print(f"Final front           : {final['x_max_m']:.6f} m")
print(
    f"Raw front advance     : "
    f"{final['raw_front_advance_m']:.6f} m"
)
print(
    f"Robust front advance  : "
    f"{final['robust_front_advance_m']:.6f} m"
)
print(
    f"Normalized runout     : "
    f"{final['normalized_raw_runout']:.3f} L0"
)
print(
    f"Max displacement      : "
    f"{final['max_displacement_m']:.6f} m"
)
print(
    f"Peak particle speed   : "
    f"{peak_speed_row['max_speed_m_s']:.6f} m/s "
    f"at t={peak_speed_row['time_s']:.4f} s"
)

print()
print(f"Saved: {time_series_path}")
print(f"Saved: {summary_path}")
print(f"Saved: {figure_png}")
print(f"Saved: {figure_pdf}")

print("=" * 76)
print("PHASE 1F COMPLETE")
print("=" * 76)
