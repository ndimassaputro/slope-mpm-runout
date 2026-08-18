from pathlib import Path
import json, math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.tri as mtri

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "scenarios" / "baseline_dry_intact"
MESH = CASE / "mesh"
FIG = ROOT / "results" / "figures"
TAB = ROOT / "results" / "tables"
for p in (CASE, MESH, FIG, TAB):
    p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------
H = 10.0
CREST_X = 6.0
ANGLE_DEG = 30.0
DX = 0.50

# Background MPM domain
XMAX = 38.0
YMAX = 12.0

ang = math.radians(ANGLE_DEG)
RUN = H / math.tan(ang)
TOE_X = CREST_X + RUN
SLOPE_LEN = H / math.sin(ang)

# Exact cross-sectional area of the idealised soil body
AREA_EXACT = CREST_X * H + 0.5 * RUN * H


def surface(x):
    if x <= CREST_X:
        return H
    return H - (x - CREST_X) * math.tan(ang)


# ---------------------------------------------------------------------
# Initial material mesh
# ---------------------------------------------------------------------
pts = set()

for x in np.arange(0.0, TOE_X + 0.5 * DX, DX):

    if x > TOE_X + 1.0e-9:
        continue

    sy = surface(x)

    for y in np.arange(0.0, H + 0.5 * DX, DX):

        if y > sy + 1.0e-9:
            continue

        # Avoid very small triangles immediately below the exact
        # inclined boundary.
        if x > CREST_X and y < sy - 1.0e-9:

            perpendicular_gap = (
                (sy - y) * math.cos(ang)
            )

            if perpendicular_gap < 0.30 * DX:
                continue

        pts.add((
            round(float(x), 9),
            round(float(y), 9),
        ))


# Add exact inclined slope boundary.
nseg = math.ceil(SLOPE_LEN / DX)

for f in np.linspace(0.0, 1.0, nseg + 1):

    pts.add((
        round(CREST_X + f * RUN, 9),
        round(H * (1.0 - f), 9),
    ))


# Ensure exact polygon corners.
pts.update({
    (0.0, 0.0),
    (0.0, H),
    (CREST_X, H),
    (round(TOE_X, 9), 0.0),
})


P = np.asarray(
    sorted(pts),
    dtype=float,
)

T = mtri.Triangulation(
    P[:, 0],
    P[:, 1],
).triangles.copy()


def area2(tri):
    a, b, c = P[tri]

    return (
        (b[0] - a[0]) * (c[1] - a[1])
        - (b[1] - a[1]) * (c[0] - a[0])
    )


# Ensure counter-clockwise element ordering.
for i in range(len(T)):

    if area2(T[i]) < 0:

        T[i, 1], T[i, 2] = (
            T[i, 2],
            T[i, 1],
        )


# Remove zero-area triangles created from exactly collinear
# boundary points.
areas = np.abs(
    np.array([area2(t) for t in T])
) / 2.0

T = T[areas > 1.0e-8]

areas = np.abs(
    np.array([area2(t) for t in T])
) / 2.0


def min_angle(tri):

    q = P[tri]

    a = np.linalg.norm(q[1] - q[2])
    b = np.linalg.norm(q[0] - q[2])
    c = np.linalg.norm(q[0] - q[1])

    output = []

    for opposite, side1, side2 in (
        (a, b, c),
        (b, a, c),
        (c, a, b),
    ):

        cos_value = np.clip(
            (
                side1**2
                + side2**2
                - opposite**2
            )
            / (2.0 * side1 * side2),
            -1.0,
            1.0,
        )

        output.append(
            math.degrees(
                math.acos(cos_value)
            )
        )

    return min(output)


min_angles = np.array([
    min_angle(t)
    for t in T
])

AREA_MESH = areas.sum()

AREA_ERR = (
    100.0
    * (AREA_MESH - AREA_EXACT)
    / AREA_EXACT
)


# ---------------------------------------------------------------------
# Structured triangular MPM background grid
# ---------------------------------------------------------------------
gx = np.arange(
    0.0,
    XMAX + 0.5 * DX,
    DX,
)

gy = np.arange(
    0.0,
    YMAX + 0.5 * DX,
    DX,
)

nx = len(gx)
ny = len(gy)

G = np.array([
    (x, y)
    for y in gy
    for x in gx
], dtype=float)


def nid(i, j):
    return j * nx + i


GT = []

for j in range(ny - 1):

    for i in range(nx - 1):

        n00 = nid(i, j)
        n10 = nid(i + 1, j)
        n01 = nid(i, j + 1)
        n11 = nid(i + 1, j + 1)

        GT.append(
            (n00, n10, n11)
        )

        GT.append(
            (n00, n11, n01)
        )


GT = np.asarray(
    GT,
    dtype=int,
)


# ---------------------------------------------------------------------
# Export mesh tables
# ---------------------------------------------------------------------
pd.DataFrame({
    "node_id": np.arange(1, len(P) + 1),
    "x_m": P[:, 0],
    "y_m": P[:, 1],
    "z_m": 0.0,
}).to_csv(
    MESH / "body_nodes.csv",
    index=False,
)

pd.DataFrame({
    "element_id": np.arange(1, len(T) + 1),
    "node_1": T[:, 0] + 1,
    "node_2": T[:, 1] + 1,
    "node_3": T[:, 2] + 1,
}).to_csv(
    MESH / "body_elements.csv",
    index=False,
)

pd.DataFrame({
    "node_id": np.arange(1, len(G) + 1),
    "x_m": G[:, 0],
    "y_m": G[:, 1],
    "z_m": 0.0,
}).to_csv(
    MESH / "grid_nodes.csv",
    index=False,
)

pd.DataFrame({
    "element_id": np.arange(1, len(GT) + 1),
    "node_1": GT[:, 0] + 1,
    "node_2": GT[:, 1] + 1,
    "node_3": GT[:, 2] + 1,
}).to_csv(
    MESH / "grid_elements.csv",
    index=False,
)


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
config = {
    "case": "baseline_dry_intact",

    "geometry": {
        "slope_height_m": H,
        "crest_x_m": CREST_X,
        "slope_angle_deg": ANGLE_DEG,
        "slope_run_m": RUN,
        "toe_x_m": TOE_X,
        "domain_xmax_m": XMAX,
        "domain_ymax_m": YMAX,
    },

    "mesh": {
        "target_spacing_m": DX,
        "body_nodes": len(P),
        "body_triangles": len(T),
        "background_nodes": len(G),
        "background_triangles": len(GT),
    },

    "boundary_concept": {
        "bottom": "ux = uy = 0",
        "left": "ux = 0; uy free",
        "right": "free",
        "top": "free",
    },
}

(
    CASE / "geometry_config.json"
).write_text(
    json.dumps(
        config,
        indent=2,
    )
)


summary = pd.DataFrame({
    "metric": [
        "slope_height_m",
        "slope_angle_deg",
        "slope_run_m",
        "toe_x_m",
        "target_spacing_m",
        "body_nodes",
        "body_triangles",
        "background_nodes",
        "background_triangles",
        "exact_area_m2",
        "mesh_area_m2",
        "area_error_percent",
        "minimum_triangle_angle_deg",
        "p05_minimum_triangle_angle_deg",
    ],

    "value": [
        H,
        ANGLE_DEG,
        RUN,
        TOE_X,
        DX,
        len(P),
        len(T),
        len(G),
        len(GT),
        AREA_EXACT,
        AREA_MESH,
        AREA_ERR,
        min_angles.min(),
        np.percentile(
            min_angles,
            5,
        ),
    ],
})

summary.to_csv(
    TAB / "slope_geometry_summary.csv",
    index=False,
)


# ---------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "legend.fontsize": 8,
    "axes.linewidth": 0.8,
    "savefig.dpi": 400,
    "savefig.bbox": "tight",
})


polyx = [
    0,
    0,
    CREST_X,
    TOE_X,
]

polyy = [
    0,
    H,
    H,
    0,
]


fig, ax = plt.subplots(
    1,
    3,
    figsize=(12, 3.6),
)


# (a) slope geometry
ax[0].fill(
    polyx,
    polyy,
    facecolor="0.88",
    edgecolor="0.15",
)

ax[0].plot(
    [CREST_X, TOE_X],
    [H, 0],
    color="0.05",
    linewidth=1.2,
)

ax[0].scatter(
    [CREST_X, TOE_X],
    [H, 0],
    s=18,
    facecolors="white",
    edgecolors="0.10",
    zorder=3,
)

ax[0].text(
    CREST_X - 0.3,
    H + 0.35,
    "crest",
    ha="right",
)

ax[0].text(
    TOE_X + 0.3,
    0.25,
    "toe",
)

ax[0].text(
    13.1,
    4.2,
    r"$30^\circ$",
    rotation=-30,
)

ax[0].set_title(
    "(a) Idealised slope geometry",
    loc="left",
    fontweight="bold",
)


# (b) body mesh
ax[1].triplot(
    P[:, 0],
    P[:, 1],
    T,
    color="0.62",
    linewidth=0.28,
)

ax[1].plot(
    polyx + [0],
    polyy + [0],
    color="0.10",
    linewidth=0.9,
)

ax[1].text(
    0.97,
    0.95,
    (
        f"{len(T):,} triangles\n"
        f"h = {DX:.2f} m"
    ),
    transform=ax[1].transAxes,
    ha="right",
    va="top",
)

ax[1].set_title(
    "(b) Initial material mesh",
    loc="left",
    fontweight="bold",
)


# (c) background domain
ax[2].fill(
    polyx,
    polyy,
    facecolor="0.90",
    edgecolor="0.20",
)

for x in np.arange(
    0,
    XMAX + 0.1,
    2,
):
    ax[2].plot(
        [x, x],
        [0, YMAX],
        color="0.90",
        linewidth=0.4,
        zorder=0,
    )

for y in np.arange(
    0,
    YMAX + 0.1,
    2,
):
    ax[2].plot(
        [0, XMAX],
        [y, y],
        color="0.90",
        linewidth=0.4,
        zorder=0,
    )

# conceptual displacement constraints
ax[2].plot(
    [0, XMAX],
    [0, 0],
    color="0.05",
    linewidth=2.0,
)

ax[2].plot(
    [0, 0],
    [0, YMAX],
    color="0.20",
    linewidth=1.3,
    linestyle="--",
)

ax[2].text(
    19,
    0.45,
    r"base: $u_x=u_y=0$",
    ha="center",
)

ax[2].text(
    0.6,
    11.5,
    r"left: $u_x=0$",
    rotation=90,
    va="top",
)

ax[2].annotate(
    "runout space",
    xy=(32, 1),
    xytext=(28, 4),
    arrowprops=dict(
        arrowstyle="->",
        linewidth=0.8,
        color="0.20",
    ),
)

ax[2].set_title(
    "(c) MPM background domain",
    loc="left",
    fontweight="bold",
)


for a in ax:

    a.set_xlabel(
        "Horizontal coordinate, x (m)"
    )

    a.set_ylabel(
        "Vertical coordinate, y (m)"
    )

    a.set_aspect(
        "equal",
        adjustable="box",
    )

    for spine in a.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.8)
        spine.set_color("0.15")


ax[0].set_xlim(-1, 27)
ax[0].set_ylim(-0.7, 11.2)

ax[1].set_xlim(-0.5, 24.5)
ax[1].set_ylim(-0.5, 10.8)

ax[2].set_xlim(-1, 39)
ax[2].set_ylim(-0.7, 12.7)


fig.tight_layout()

fig.savefig(
    FIG / "slope_geometry_definition.png"
)

fig.savefig(
    FIG / "slope_geometry_definition.pdf"
)

plt.close(fig)


# ---------------------------------------------------------------------
# Terminal report
# ---------------------------------------------------------------------
print("=" * 72)
print("PHASE 2A — INDEPENDENT SLOPE GEOMETRY")
print("=" * 72)

print(
    f"Slope H / angle / run : "
    f"{H:.1f} m / "
    f"{ANGLE_DEG:.1f} deg / "
    f"{RUN:.3f} m"
)

print(
    f"Toe coordinate        : "
    f"{TOE_X:.3f} m"
)

print(
    f"Target spacing        : "
    f"{DX:.3f} m"
)

print(
    f"Body nodes/elements   : "
    f"{len(P):,} / {len(T):,}"
)

print(
    f"Grid nodes/elements   : "
    f"{len(G):,} / {len(GT):,}"
)

print(
    f"Exact area            : "
    f"{AREA_EXACT:.6f} m2"
)

print(
    f"Mesh area             : "
    f"{AREA_MESH:.6f} m2"
)

print(
    f"Area error            : "
    f"{AREA_ERR:.3e} %"
)

print(
    f"Minimum triangle angle: "
    f"{min_angles.min():.2f} deg"
)

print(
    f"5th pct min angle     : "
    f"{np.percentile(min_angles, 5):.2f} deg"
)

print(
    f"Figure                : "
    f"{FIG / 'slope_geometry_definition.png'}"
)

print("=" * 72)
print("PHASE 2A COMPLETE")
print("=" * 72)
