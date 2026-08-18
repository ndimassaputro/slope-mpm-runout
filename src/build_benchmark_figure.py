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

TABLE = ROOT / "results" / "tables" / "benchmark_time_series.csv"
OUT = ROOT / "results" / "figures"

OUT.mkdir(parents=True, exist_ok=True)


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

    for name in (
        "ReadAllScalarsOn",
        "ReadAllVectorsOn",
        "ReadAllTensorsOn",
        "ReadAllFieldsOn",
    ):
        method = getattr(reader, name, None)
        if method is not None:
            method()

    reader.Update()
    data = reader.GetOutput()

    xyz = vtk_to_numpy(data.GetPoints().GetData()).astype(float)

    cd = data.GetCellData()

    velocity = vtk_to_numpy(
        cd.GetArray("MP_VELOCITY")
    ).astype(float)

    displacement = vtk_to_numpy(
        cd.GetArray("MP_DISPLACEMENT")
    ).astype(float)

    return xyz, velocity, displacement


def get_time(path):
    m = re.search(r"_0_(\d+\.\d+)\.vtk$", path.name)
    return float(m.group(1))


def nearest_file(files, target):
    times = np.array([get_time(p) for p in files])
    return files[np.argmin(np.abs(times - target))]


def upper_surface(x, y, bins=180, percentile=98.5):
    edges = np.linspace(np.min(x), np.max(x), bins + 1)

    xc = []
    ys = []

    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (x >= lo) & (x < hi)

        if np.sum(mask) >= 5:
            xc.append(0.5 * (lo + hi))
            ys.append(np.percentile(y[mask], percentile))

    return np.asarray(xc), np.asarray(ys)


files = sorted(
    BODY.glob("MPM_Material_0_*.vtk"),
    key=get_time,
)

if not files:
    raise FileNotFoundError(BODY)

df = pd.read_csv(TABLE)

initial_file = nearest_file(files, 0.0)
final_file = nearest_file(files, 2.0)

xyz0, _, _ = read_vtk(initial_file)
xyzf, _, _ = read_vtk(final_file)

x_min0 = xyz0[:, 0].min()
x_max0 = xyz0[:, 0].max()
y_min0 = xyz0[:, 1].min()
y_max0 = xyz0[:, 1].max()

L0 = x_max0 - x_min0
H0 = y_max0 - y_min0


def normalize(xyz):
    x = (xyz[:, 0] - x_min0) / L0
    y = (xyz[:, 1] - y_min0) / H0
    return x, y


x0, y0 = normalize(xyz0)
xf, yf = normalize(xyzf)

apply_publication_style()

fig, axes = plt.subplots(2, 2, figsize=(10.0, 6.7))


# ------------------------------------------------------------------
# (a) Initial and final normalized configuration
# ------------------------------------------------------------------

ax = axes[0, 0]

sample = slice(None, None, 8)

ax.scatter(
    x0[sample],
    y0[sample],
    s=1.2,
    alpha=0.28,
    c="0.72",
    edgecolors="none",
    rasterized=True,
    label="Initial",
)

ax.scatter(
    xf[sample],
    yf[sample],
    s=1.2,
    alpha=0.50,
    c="0.15",
    edgecolors="none",
    rasterized=True,
    label="Final",
)

ax.axvline(
    1.0,
    linestyle="--",
    linewidth=0.9,
    color="0.35",
)

ax.set_xlabel(r"Normalized horizontal coordinate, $x/L_0$")
ax.set_ylabel(r"Normalized vertical coordinate, $y/H_0$")
ax.set_title(
    "(a) Initial and final configuration",
    loc="left",
    fontweight="bold",
)
ax.legend(frameon=False, markerscale=4)

ax.set_xlim(-0.03, 2.65)
ax.set_ylim(-0.04, 1.08)

clean_axis(ax, grid=False)


# ------------------------------------------------------------------
# (b) Normalized runout evolution
# ------------------------------------------------------------------

ax = axes[0, 1]

ax.plot(
    df["time_s"],
    df["raw_front_advance_m"] / L0,
    linewidth=1.35,
    color="0.10",
    label="Maximum-x front",
)

ax.plot(
    df["time_s"],
    df["robust_front_advance_m"] / L0,
    linewidth=1.20,
    linestyle="--",
    color="0.45",
    label="99.9th percentile front",
)

ax.set_xlabel("Time (s)")
ax.set_ylabel(r"Normalized front advance, $\Delta x/L_0$")
ax.set_title(
    "(b) Runout evolution",
    loc="left",
    fontweight="bold",
)
ax.legend(frameon=False)

clean_axis(ax)


# ------------------------------------------------------------------
# (c) Upper-surface evolution
# ------------------------------------------------------------------

ax = axes[1, 0]

snapshot_times = [0.00, 0.25, 0.50, 1.00, 2.00]
styles = [
    ("0.72", ":"),
    ("0.58", "-."),
    ("0.42", "--"),
    ("0.28", "-"),
    ("0.08", "-"),
]

for target, (gray, ls) in zip(snapshot_times, styles):

    path = nearest_file(files, target)
    actual = get_time(path)

    xyz, _, _ = read_vtk(path)

    x, y = normalize(xyz)

    xs, ys = upper_surface(
        x,
        y,
        bins=180,
        percentile=98.5,
    )

    ax.plot(
        xs,
        ys,
        linewidth=1.15,
        linestyle=ls,
        color=gray,
        label=f"{actual:.2f} s",
    )

ax.set_xlabel(r"Normalized horizontal coordinate, $x/L_0$")
ax.set_ylabel(r"Normalized surface elevation, $y/H_0$")
ax.set_title(
    "(c) Upper-surface evolution",
    loc="left",
    fontweight="bold",
)

ax.set_xlim(-0.03, 2.65)
ax.set_ylim(-0.04, 1.08)

ax.legend(frameon=False, ncol=2)

clean_axis(ax)


# ------------------------------------------------------------------
# (d) Velocity response
# ------------------------------------------------------------------

ax = axes[1, 1]

ax.plot(
    df["time_s"],
    df["mean_speed_m_s"],
    linewidth=1.2,
    color="0.48",
    label="Mean",
)

ax.plot(
    df["time_s"],
    df["p95_speed_m_s"],
    linewidth=1.3,
    color="0.10",
    label="95th percentile",
)

ax.set_xlabel("Time (s)")
ax.set_ylabel("Material-point speed (m/s)")
ax.set_title(
    "(d) Material-point velocity response",
    loc="left",
    fontweight="bold",
)

ax.legend(frameon=False)

clean_axis(ax)


fig.tight_layout()

png = OUT / "benchmark_reproduction.png"
pdf = OUT / "benchmark_reproduction.pdf"

fig.savefig(png)
fig.savefig(pdf)
plt.close(fig)

print("=" * 72)
print("BENCHMARK REPRODUCTION FIGURE")
print("=" * 72)
print(f"Initial width  L0 : {L0:.6f} m")
print(f"Initial height H0 : {H0:.6f} m")
print(
    "Final raw runout  : "
    f"{df.iloc[-1]['raw_front_advance_m'] / L0:.3f} L0"
)
print(
    "Final robust runout: "
    f"{df.iloc[-1]['robust_front_advance_m'] / L0:.3f} L0"
)
print(f"Saved: {png}")
print(f"Saved: {pdf}")
print("=" * 72)
