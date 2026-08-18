from pathlib import Path
import csv
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
SWEEP = ROOT / "scenarios" / "strength_reduction"

cases = sorted(
    p
    for p in SWEEP.glob("F_*")
    if p.is_dir()
)


def factor_from_name(name):
    return float(
        name.replace("F_", "").replace("p", ".")
    )


rows = []

print("=" * 78)
print("PHASE 3A — STATIC STRENGTH-REDUCTION SWEEP")
print("=" * 78)

for i, case in enumerate(cases, start=1):

    F = factor_from_name(case.name)

    print()
    print(
        f"[{i}/{len(cases)}] "
        f"Running {case.name}  (F={F:.2f})"
    )

    log_path = case / "run.log"

    t0 = time.time()

    result = subprocess.run(
        ["python", "MainKratos.py"],
        cwd=case,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    elapsed = time.time() - t0

    text = result.stdout
    log_path.write_text(text)

    analysis_end = (
        "Analysis -END-" in text
    )

    converged = (
        "Convergence is achieved" in text
    )

    error_detected = bool(
        re.search(
            r"Traceback|KRATOS_ERROR|Segmentation fault",
            text,
            flags=re.IGNORECASE,
        )
    )

    iterations = len(
        re.findall(
            r"RESIDUAL CRITERION:",
            text,
        )
    )

    status = (
        "COMPLETE"
        if (
            result.returncode == 0
            and analysis_end
            and converged
            and not error_detected
        )
        else "CHECK"
    )

    print(
        f"    status     : {status}"
    )

    print(
        f"    return code: {result.returncode}"
    )

    print(
        f"    converged  : {converged}"
    )

    print(
        f"    NR checks  : {iterations}"
    )

    print(
        f"    runtime    : {elapsed:.2f} s"
    )

    rows.append({
        "factor": F,
        "case": case.name,
        "status": status,
        "return_code": result.returncode,
        "analysis_end": analysis_end,
        "converged": converged,
        "error_detected": error_detected,
        "residual_checks": iterations,
        "runtime_s": elapsed,
    })


status_file = (
    ROOT
    / "results"
    / "tables"
    / "strength_reduction_run_status.csv"
)

status_file.parent.mkdir(
    parents=True,
    exist_ok=True,
)

with status_file.open(
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
print("=" * 78)
print("SWEEP EXECUTION COMPLETE")
print("=" * 78)

for row in rows:
    print(
        f"F={row['factor']:.2f}  "
        f"{row['status']:8s}  "
        f"NR={row['residual_checks']:2d}  "
        f"{row['runtime_s']:.2f} s"
    )

print()
print(f"Saved: {status_file}")
print("=" * 78)
