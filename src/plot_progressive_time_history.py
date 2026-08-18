from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]

CSV = (
    ROOT
    / "scenarios"
    / "toe_erosion"
    / "F1p58_progressive_extended"
    / "response_history.csv"
)

OUT = (
    ROOT
    / "results"
    / "figures"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


def apply_publication_style():

    plt.rcParams.update(
        {
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
        }
    )


def clean_axis(ax):

    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.8)
        spine.set_color("0.15")

    ax.grid(
        axis="y",
        color="0.90",
        linewidth=0.6,
    )

    ax.set_axisbelow(True)


def panel_title(ax, label, title):

    ax.set_title(
        f"({label}) {title}",
        loc="left",
        fontweight="bold",
    )


apply_publication_style()


if not CSV.exists():
    raise FileNotFoundError(CSV)


df = pd.read_csv(CSV)


# ============================================================
# Numerical elapsed time
#
# Original restart time is t = 1.0 s.
# This is numerical relaxation time, NOT physical coastal
# erosion duration/rate.
# ============================================================

df["tau_s"] = (
    df["time_s"] - 1.0
)


# ============================================================
# Detect erosion-stage changes automatically
# ============================================================

stage_mask = (
    df["Et"]
    .ne(
        df["Et"].shift(1)
    )
)

stages = (
    df.loc[
        stage_mask,
        ["tau_s", "Et"]
    ]
    .copy()
)

stages = stages[
    stages["Et"] > 0
]


# ============================================================
# Peak speed
# ============================================================

peak_idx = (
    df["p95_speed_mps"].idxmax()
)

peak = df.loc[
    peak_idx
]


# ============================================================
# Figure
# ============================================================

fig, axes = plt.subplots(
    2,
    2,
    figsize=(7.4, 6.2),
)

ax1, ax2, ax3, ax4 = axes.ravel()


# ------------------------------------------------------------
# (a) prescribed erosion sequence
# ------------------------------------------------------------

ax1.step(
    df["tau_s"],
    df["Et"],
    where="post",
    linewidth=1.4,
    color="0.15",
)

ax1.set_ylabel(
    r"Toe-recession ratio, $E_t=e/H$"
)

panel_title(
    ax1,
    "a",
    "Prescribed erosion sequence",
)

clean_axis(ax1)


# ------------------------------------------------------------
# (b) P95 displacement
# ------------------------------------------------------------

ax2.plot(
    df["tau_s"],
    df["p95_displacement_m"] * 1000.0,
    linewidth=1.3,
    color="0.15",
)

ax2.set_ylabel(
    "P95 displacement (mm)"
)

panel_title(
    ax2,
    "b",
    "Bulk movement",
)

clean_axis(ax2)


# ------------------------------------------------------------
# (c) P95 speed
# ------------------------------------------------------------

ax3.plot(
    df["tau_s"],
    df["p95_speed_mps"],
    linewidth=1.3,
    color="0.15",
)

ax3.scatter(
    [peak["tau_s"]],
    [peak["p95_speed_mps"]],
    s=28,
    color="0.15",
    zorder=5,
)

ax3.annotate(
    (
        f"peak = "
        f"{peak['p95_speed_mps']:.3f} m/s\n"
        f"$E_t$ = {peak['Et']:.2f}"
    ),
    xy=(
        peak["tau_s"],
        peak["p95_speed_mps"],
    ),
    xytext=(
        peak["tau_s"] + 0.10,
        peak["p95_speed_mps"] * 0.82,
    ),
    arrowprops={
        "arrowstyle": "->",
        "linewidth": 0.8,
        "color": "0.25",
    },
    fontsize=8,
)

ax3.set_ylabel(
    "P95 speed (m/s)"
)

ax3.set_xlabel(
    "Numerical elapsed time (s)"
)

panel_title(
    ax3,
    "c",
    "Dynamic response",
)

clean_axis(ax3)


# ------------------------------------------------------------
# (d) new plastic MPs
# ------------------------------------------------------------

ax4.plot(
    df["tau_s"],
    df[
        "new_plastic_fraction_gt_1e5_percent"
    ],
    linewidth=1.3,
    color="0.15",
)

ax4.set_ylabel(
    "New plastic MPs (%)"
)

ax4.set_xlabel(
    "Numerical elapsed time (s)"
)

panel_title(
    ax4,
    "d",
    "Cumulative plastic mobilization",
)

clean_axis(ax4)


# ============================================================
# Erosion-stage markers
# ============================================================

for ax in (
    ax2,
    ax3,
    ax4,
):

    for _, row in stages.iterrows():

        ax.axvline(
            row["tau_s"],
            linestyle="--",
            linewidth=0.7,
            color="0.75",
            zorder=0,
        )


# ============================================================
# Stage labels on panel (a)
# ============================================================

for _, row in stages.iterrows():

    ax1.axvline(
        row["tau_s"],
        linestyle="--",
        linewidth=0.7,
        color="0.75",
        zorder=0,
    )


# ============================================================
# Common limits
# ============================================================

xmin = max(
    0.0,
    df["tau_s"].min(),
)

xmax = df["tau_s"].max()

for ax in axes.ravel():

    ax.set_xlim(
        xmin,
        xmax,
    )


# ============================================================
# Title and caption
# ============================================================

fig.suptitle(
    (
        "Progressive toe-erosion response of the "
        r"preconditioned $F=1.58$ slope"
    ),
    fontsize=11,
    fontweight="bold",
    y=0.995,
)


fig.text(
    0.5,
    0.012,
    (
        "Dashed lines mark prescribed erosion increments. "
        "Elapsed time is a numerical relaxation coordinate, "
        "not a physical coastal-erosion rate. "
        "The response mobilizes progressively but does not "
        "develop self-sustaining runout."
    ),
    ha="center",
    va="bottom",
    fontsize=8,
)


fig.tight_layout(
    rect=[
        0.04,
        0.055,
        0.99,
        0.96,
    ]
)


png = (
    OUT
    / "progressive_time_history.png"
)

pdf = (
    OUT
    / "progressive_time_history.pdf"
)


fig.savefig(
    png,
    dpi=400,
)

fig.savefig(
    pdf,
)

plt.close(fig)


# ============================================================
# Console summary
# ============================================================

final = df.iloc[-1]

print("=" * 76)
print("PROGRESSIVE TIME-HISTORY FIGURE")
print("=" * 76)

print("PNG :", png)
print("PDF :", pdf)

print()
print("Detected erosion stages:")

for _, row in stages.iterrows():

    print(
        f"  tau={row['tau_s']:.3f} s"
        f" -> Et={row['Et']:.2f}"
    )

print()
print(
    "Peak P95 speed :",
    f"{peak['p95_speed_mps']:.6e} m/s",
)

print(
    "Peak Et        :",
    f"{peak['Et']:.2f}",
)

print(
    "Final P95 speed:",
    f"{final['p95_speed_mps']:.6e} m/s",
)

print(
    "Final new plastic:",
    f"{final['new_plastic_fraction_gt_1e5_percent']:.3f} %",
)

print("=" * 76)
