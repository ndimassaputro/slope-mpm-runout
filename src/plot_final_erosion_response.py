from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]

CSV = (
    ROOT
    / "results"
    / "final_erosion_summary.csv"
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


df = pd.read_csv(CSV)

single = (
    df[
        df["mode"] == "single-stage"
    ]
    .sort_values("Et")
    .copy()
)

progressive = (
    df[
        df["mode"] == "progressive"
    ]
    .iloc[0]
)


# ============================================================
# Values
# ============================================================

Et = single["Et"].to_numpy()

disp = single[
    "final_p95_disp_mm"
].to_numpy()

speed = single[
    "peak_p95_speed_mps"
].to_numpy()

plastic = single[
    "new_plastic_percent"
].to_numpy()


# ============================================================
# Figure
# ============================================================

fig, axes = plt.subplots(
    3,
    1,
    figsize=(6.8, 8.0),
    sharex=True,
)

ax1, ax2, ax3 = axes


# ------------------------------------------------------------
# (a) displacement
# ------------------------------------------------------------

ax1.plot(
    Et,
    disp,
    marker="o",
    markersize=5,
    linewidth=1.3,
    color="0.15",
    label="Single-stage erosion",
)

ax1.scatter(
    progressive["Et"],
    progressive["final_p95_disp_mm"],
    marker="D",
    s=42,
    facecolors="white",
    edgecolors="0.15",
    linewidths=1.2,
    zorder=5,
    label="Progressive erosion",
)

ax1.set_ylabel(
    "Final P95 displacement (mm)"
)

panel_title(
    ax1,
    "a",
    "Bulk movement response",
)

clean_axis(ax1)

ax1.legend(
    frameon=False,
    loc="upper left",
)


# ------------------------------------------------------------
# (b) peak speed
# ------------------------------------------------------------

ax2.plot(
    Et,
    speed,
    marker="o",
    markersize=5,
    linewidth=1.3,
    color="0.15",
)

ax2.scatter(
    progressive["Et"],
    progressive["peak_p95_speed_mps"],
    marker="D",
    s=42,
    facecolors="white",
    edgecolors="0.15",
    linewidths=1.2,
    zorder=5,
)

ax2.set_ylabel(
    "Peak P95 speed (m/s)"
)

panel_title(
    ax2,
    "b",
    "Dynamic response",
)

clean_axis(ax2)


# ------------------------------------------------------------
# (c) plastic mobilization
# ------------------------------------------------------------

ax3.plot(
    Et,
    plastic,
    marker="o",
    markersize=5,
    linewidth=1.3,
    color="0.15",
)

ax3.scatter(
    progressive["Et"],
    progressive["new_plastic_percent"],
    marker="D",
    s=42,
    facecolors="white",
    edgecolors="0.15",
    linewidths=1.2,
    zorder=5,
)

ax3.set_ylabel(
    "New plastic MPs (%)"
)

ax3.set_xlabel(
    r"Toe-recession ratio, $E_t=e/H$"
)

panel_title(
    ax3,
    "c",
    "Plastic mobilization",
)

clean_axis(ax3)


# ============================================================
# Common x-axis
# ============================================================

ax3.set_xticks(
    np.arange(
        0.10,
        0.301,
        0.05,
    )
)

ax3.set_xlim(
    0.085,
    0.315,
)


# ============================================================
# Annotation: same final geometry, different erosion history
# ============================================================

ax2.annotate(
    "same final $E_t=0.30$,\n"
    "different erosion history",
    xy=(
        progressive["Et"],
        progressive["peak_p95_speed_mps"],
    ),
    xytext=(
        0.205,
        0.023,
    ),
    arrowprops={
        "arrowstyle": "->",
        "linewidth": 0.8,
        "color": "0.25",
    },
    fontsize=8,
    ha="right",
)


fig.suptitle(
    "Toe-erosion response of the preconditioned "
    r"$F=1.58$ slope",
    fontsize=11,
    fontweight="bold",
    y=0.995,
)


fig.text(
    0.5,
    0.012,
    (
        "Filled circles: independent single-stage erosion.  "
        "Open diamond: progressive erosion sequence.  "
        "No self-sustaining runout was observed."
    ),
    ha="center",
    va="bottom",
    fontsize=8,
)


fig.tight_layout(
    rect=[
        0.04,
        0.045,
        0.99,
        0.97,
    ]
)


png = (
    OUT
    / "final_erosion_response.png"
)

pdf = (
    OUT
    / "final_erosion_response.pdf"
)


fig.savefig(
    png,
    dpi=400,
)

fig.savefig(
    pdf,
)

plt.close(fig)


print("=" * 76)
print("FINAL EROSION RESPONSE FIGURE")
print("=" * 76)

print("PNG :", png)
print("PDF :", pdf)

print()
print(
    "Single-stage Et=0.30:"
)

print(
    f"  displacement = "
    f"{single.iloc[-1]['final_p95_disp_mm']:.3f} mm"
)

print(
    f"  peak speed    = "
    f"{single.iloc[-1]['peak_p95_speed_mps']:.5f} m/s"
)

print(
    f"  new plastic   = "
    f"{single.iloc[-1]['new_plastic_percent']:.1f} %"
)

print()
print(
    "Progressive final Et=0.30:"
)

print(
    f"  displacement = "
    f"{progressive['final_p95_disp_mm']:.3f} mm"
)

print(
    f"  peak speed    = "
    f"{progressive['peak_p95_speed_mps']:.5f} m/s"
)

print(
    f"  new plastic   = "
    f"{progressive['new_plastic_percent']:.1f} %"
)

print("=" * 76)
