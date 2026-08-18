from pathlib import Path
import csv
import os
import re
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]

BASE = (
    ROOT
    / "scenarios"
    / "strength_reduction_quasistatic"
)

TABLE = (
    ROOT
    / "results"
    / "tables"
    / "refined_quasistatic_sweep_status.csv"
)


def factor_from_name(name):

    return float(
        name
        .replace("F_", "")
        .replace("p", ".")
    )


cases = sorted(
    [
        p
        for p in BASE.glob("F_*")
        if p.is_dir()
    ],
    key=lambda p:
        factor_from_name(p.name),
)


rows = []


print("=" * 86)
print("PHASE 3B — REFINED QUASI-STATIC STRENGTH-REDUCTION SWEEP")
print("=" * 86)


for i, case in enumerate(
    cases,
    start=1,
):

    F = factor_from_name(
        case.name
    )

    print()
    print(
        f"[{i}/{len(cases)}] "
        f"{case.name}  "
        f"(F={F:.2f})"
    )

    # Remove old raw outputs if rerunning intentionally.
    for folder_name in (
        "qs_Body",
        "qs_Grid",
    ):
        folder = case / folder_name

        if folder.exists():
            import shutil
            shutil.rmtree(folder)

    env = os.environ.copy()

    env[
        "OMP_NUM_THREADS"
    ] = "1"

    env[
        "PYTHONUNBUFFERED"
    ] = "1"


    start = time.time()

    result = subprocess.run(
        [
            "python",
            "MainKratos.py",
        ],

        cwd=case,
        env=env,

        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    runtime = (
        time.time() - start
    )

    text = result.stdout

    (
        case / "run.log"
    ).write_text(text)


    analysis_end = (
        "Analysis -END-"
        in text
    )

    inverted = bool(
        re.search(
            r"INVERTED|detF\s*=",
            text,
            flags=re.IGNORECASE,
        )
    )

    exception = bool(
        re.search(
            r"Kratos::Exception|"
            r"terminate called|"
            r"Traceback",
            text,
            flags=re.IGNORECASE,
        )
    )


    converged_steps = len(
        re.findall(
            r"Convergence is achieved",
            text,
        )
    )


    lambda_matches = re.findall(
        r"GravityRamp:\s+lambda="
        r"([0-9.]+)",
        text,
    )

    last_lambda = (
        float(
            lambda_matches[-1]
        )
        if lambda_matches
        else 0.0
    )


    # Number of load levels that actually converged.
    full_gravity_reached = (
        analysis_end
        and converged_steps == 20
        and last_lambda >= 0.999
    )


    if full_gravity_reached:

        status = "FULL_EQ"

    elif inverted:

        status = "INVERTED"

    elif exception:

        status = "EXCEPTION"

    else:

        status = "CHECK"


    print(
        f"    status              : "
        f"{status}"
    )

    print(
        f"    converged steps     : "
        f"{converged_steps}/20"
    )

    print(
        f"    last gravity factor : "
        f"{last_lambda:.3f}"
    )

    print(
        f"    analysis end        : "
        f"{analysis_end}"
    )

    print(
        f"    inverted            : "
        f"{inverted}"
    )

    print(
        f"    return code         : "
        f"{result.returncode}"
    )

    print(
        f"    runtime             : "
        f"{runtime:.2f} s"
    )


    rows.append({
        "factor": F,
        "case": case.name,
        "status": status,

        "converged_steps":
            converged_steps,

        "last_gravity_fraction":
            last_lambda,

        "full_gravity_reached":
            full_gravity_reached,

        "analysis_end":
            analysis_end,

        "element_inverted":
            inverted,

        "exception":
            exception,

        "return_code":
            result.returncode,

        "runtime_s":
            runtime,
    })


TABLE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


with TABLE.open(
    "w",
    newline="",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=rows[0].keys(),
    )

    writer.writeheader()
    writer.writerows(rows)


print()
print("=" * 86)
print("REFINED QUASI-STATIC SUMMARY")
print("=" * 86)

for row in rows:

    print(
        f"F={row['factor']:.2f}  "
        f"{row['status']:10s}  "
        f"steps={row['converged_steps']:2d}/20  "
        f"last-g={row['last_gravity_fraction']:.2f}"
    )


stable = [
    r["factor"]
    for r in rows
    if r["status"] == "FULL_EQ"
]

failed = [
    r["factor"]
    for r in rows
    if r["status"] != "FULL_EQ"
]


print()

if stable and failed:

    highest_stable = max(
        stable
    )

    higher_failed = [
        x
        for x in failed
        if x > highest_stable
    ]

    if higher_failed:

        lowest_failed = min(
            higher_failed
        )

        print(
            "Current full-gravity "
            "transition bracket:"
        )

        print(
            f"    {highest_stable:.2f} "
            f"< F_transition < "
            f"{lowest_failed:.2f}"
        )

else:

    print(
        "No closed transition bracket "
        "identified yet."
    )


print()
print(f"Saved: {TABLE}")
print("=" * 86)
