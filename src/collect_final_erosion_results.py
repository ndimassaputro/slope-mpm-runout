from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

CASES = [
    ("Et=0.10", "F1p58_Et010"),
    ("Et=0.15", "F1p58_Et015"),
    ("Et=0.20", "F1p58_Et020"),
    ("Et=0.25", "F1p58_Et025"),
    ("Et=0.30", "F1p58_Et030"),
]

BASE = ROOT / "scenarios" / "toe_erosion"

rows = []


for label, folder in CASES:

    path = (
        BASE
        / folder
        / "response_history.csv"
    )

    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_csv(path)

    final = df.iloc[-1]

    peak_v = df.loc[
        df["p95_speed_mps"].idxmax()
    ]

    rows.append(
        {
            "case": label,
            "mode": "single-stage",
            "Et": float(
                label.split("=")[1]
            ),
            "final_p95_disp_mm":
                final[
                    "p95_displacement_m"
                ] * 1000.0,
            "peak_p95_speed_mps":
                peak_v[
                    "p95_speed_mps"
                ],
            "peak_speed_time_s":
                peak_v[
                    "time_s"
                ],
            "new_plastic_percent":
                final[
                    "fraction_delta_plastic_gt_1e5_percent"
                ],
            "max_delta_plastic_strain":
                df[
                    "max_delta_plastic_strain"
                ].max(),
            "max_robust_front_advance_mm":
                df[
                    "robust_front_advance_m"
                ].max() * 1000.0,
        }
    )


# ============================================================
# Progressive extended case
# ============================================================

path = (
    BASE
    / "F1p58_progressive_extended"
    / "response_history.csv"
)

if not path.exists():
    raise FileNotFoundError(path)

df = pd.read_csv(path)

final = df.iloc[-1]

peak_v = df.loc[
    df["p95_speed_mps"].idxmax()
]

rows.append(
    {
        "case": "Et=0.10→0.30",
        "mode": "progressive",
        "Et": 0.30,
        "final_p95_disp_mm":
            final[
                "p95_displacement_m"
            ] * 1000.0,
        "peak_p95_speed_mps":
            peak_v[
                "p95_speed_mps"
            ],
        "peak_speed_time_s":
            peak_v[
                "time_s"
            ],
        "new_plastic_percent":
            final[
                "new_plastic_fraction_gt_1e5_percent"
            ],
        "max_delta_plastic_strain":
            df[
                "max_delta_plastic_strain"
            ].max(),
        "max_robust_front_advance_mm":
            df[
                "q999_downslope_displacement_m"
            ].max() * 1000.0,
    }
)


out = pd.DataFrame(rows)

results_dir = ROOT / "results"
results_dir.mkdir(
    exist_ok=True
)

csv_path = (
    results_dir
    / "final_erosion_summary.csv"
)

out.to_csv(
    csv_path,
    index=False
)


print("=" * 90)
print("FINAL EROSION SUMMARY")
print("=" * 90)

print(
    out.to_string(
        index=False,
        float_format=lambda x: f"{x:.6g}",
    )
)

print()
print("Saved:")
print(csv_path)

print("=" * 90)
