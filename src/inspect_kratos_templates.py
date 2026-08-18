from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmark" / "official_granular_flow_2D"

BODY = BENCH / "granular_flow_2D_Body.mdpa"
GRID = BENCH / "granular_flow_2D_Grid.mdpa"
PROJECT = BENCH / "ProjectParameters.json"
MATERIALS = BENCH / "ParticleMaterials.json"


def inspect_mdpa(path):
    text = path.read_text(errors="replace")
    lines = text.splitlines()

    element_types = []
    condition_types = []
    submodelparts = []
    properties = []

    for line in lines:
        s = line.strip()

        m = re.match(r"Begin\s+Elements\s+([^\s/]+)", s)
        if m:
            element_types.append(m.group(1))

        m = re.match(r"Begin\s+Conditions\s+([^\s/]+)", s)
        if m:
            condition_types.append(m.group(1))

        m = re.match(r"Begin\s+SubModelPart\s+([^\s/]+)", s)
        if m:
            submodelparts.append(m.group(1))

        m = re.match(r"Begin\s+Properties\s+(\d+)", s)
        if m:
            properties.append(int(m.group(1)))

    node_block = False
    node_count = 0
    coords = []

    element_block = False
    element_count = 0

    condition_block = False
    condition_count = 0

    for line in lines:
        s = line.strip()

        if s == "Begin Nodes":
            node_block = True
            continue

        if s == "End Nodes":
            node_block = False
            continue

        if s.startswith("Begin Elements"):
            element_block = True
            continue

        if s == "End Elements":
            element_block = False
            continue

        if s.startswith("Begin Conditions"):
            condition_block = True
            continue

        if s == "End Conditions":
            condition_block = False
            continue

        if node_block and s and not s.startswith("//"):
            parts = s.split()
            if len(parts) >= 4:
                try:
                    node_count += 1
                    coords.append(
                        (
                            float(parts[1]),
                            float(parts[2]),
                            float(parts[3]),
                        )
                    )
                except ValueError:
                    pass

        if element_block and s and not s.startswith("//"):
            if s[0].isdigit():
                element_count += 1

        if condition_block and s and not s.startswith("//"):
            if s[0].isdigit():
                condition_count += 1

    print()
    print("-" * 76)
    print(path.name)
    print("-" * 76)

    print("Properties IDs :", properties)
    print("Element types  :", element_types or ["NONE"])
    print("Condition types:", condition_types or ["NONE"])
    print("SubModelParts  :")

    for name in submodelparts:
        print(f"  - {name}")

    print(f"Nodes          : {node_count:,}")
    print(f"Elements       : {element_count:,}")
    print(f"Conditions     : {condition_count:,}")

    if coords:
        xs = [p[0] for p in coords]
        ys = [p[1] for p in coords]

        print(
            "Coordinate box : "
            f"x=[{min(xs):.6f}, {max(xs):.6f}], "
            f"y=[{min(ys):.6f}, {max(ys):.6f}]"
        )


print("=" * 76)
print("PHASE 2B-1 — KRATOS TEMPLATE INSPECTION")
print("=" * 76)

inspect_mdpa(BODY)
inspect_mdpa(GRID)


with open(PROJECT) as f:
    project = json.load(f)

solver = project["solver_settings"]

print()
print("-" * 76)
print("ProjectParameters.json")
print("-" * 76)

print("solver_type             :", solver["solver_type"])
print("model_part_name         :", solver["model_part_name"])
print("domain_size             :", solver["domain_size"])
print("analysis_type           :", solver["analysis_type"])
print("time integration        :", solver["time_integration_method"])
print("scheme_type             :", solver["scheme_type"])
print(
    "body input              :",
    solver["model_import_settings"]["input_filename"],
)
print(
    "grid input              :",
    solver["grid_model_import_settings"]["input_filename"],
)
print(
    "problem submodel parts  :",
    solver["problem_domain_sub_model_part_list"],
)
print(
    "process submodel parts  :",
    solver["processes_sub_model_part_list"],
)

constraints = project["processes"]["constraints_process_list"]

print("\nConstraints:")

for item in constraints:
    p = item["Parameters"]
    print(
        f"  {p['model_part_name']} -> "
        f"{p['variable_name']} "
        f"constrained={p['constrained']}"
    )

gravity = project["processes"]["gravity"]

print("\nGravity:")

for item in gravity:
    p = item["Parameters"]
    print(
        f"  {p['model_part_name']} -> "
        f"{p['variable_name']} "
        f"{p['modulus']} m/s2 "
        f"direction={p['direction']}"
    )


with open(MATERIALS) as f:
    materials = json.load(f)

print()
print("-" * 76)
print("ParticleMaterials.json")
print("-" * 76)

for prop in materials["properties"]:
    mat = prop["Material"]
    variables = mat["Variables"]

    print("Model part        :", prop["model_part_name"])
    print("Properties ID     :", prop["properties_id"])
    print(
        "Constitutive law :",
        mat["constitutive_law"]["name"],
    )

    for key, value in variables.items():
        print(f"  {key:30s}: {value}")

print()
print("=" * 76)
print("TEMPLATE INSPECTION COMPLETE")
print("=" * 76)
